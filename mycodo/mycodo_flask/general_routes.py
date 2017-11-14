# coding=utf-8
from __future__ import print_function

import StringIO  # not python 3 compatible
import calendar
import csv
import datetime
import logging
import os
import subprocess
import time
import flask_login
from importlib import import_module
from RPi import GPIO
from dateutil.parser import parse as date_parse
from flask import Response
from flask import current_app
from flask import flash
from flask import jsonify
from flask import make_response
from flask import redirect
from flask import render_template
from flask import request
from flask import send_from_directory
from flask import url_for
from flask.blueprints import Blueprint
from flask_babel import gettext
from flask_influxdb import InfluxDB

from mycodo.mycodo_flask.forms import forms_authentication
from mycodo.mycodo_flask.utils import utils_general
from mycodo.mycodo_flask.utils import utils_remote_host
from mycodo.mycodo_flask.utils.utils_general import gzipped

from mycodo.databases.models import Camera
from mycodo.databases.models import DisplayOrder
from mycodo.databases.models import Relay
from mycodo.databases.models import Remote
from mycodo.databases.models import Input
from mycodo.databases.models import User
from mycodo.mycodo_client import DaemonControl
from mycodo.mycodo_flask.authentication_routes import clear_cookie_auth
from mycodo.utils.influx import query_string
from mycodo.utils.system_pi import str_is_float

from mycodo.config import INFLUXDB_USER
from mycodo.config import INFLUXDB_PASSWORD
from mycodo.config import INFLUXDB_DATABASE
from mycodo.config import INSTALL_DIRECTORY
from mycodo.config import LOG_PATH
from mycodo.config import PATH_CAMERAS

blueprint = Blueprint('general_routes',
                      __name__,
                      static_folder='../static',
                      template_folder='../templates')

logger = logging.getLogger(__name__)
influx_db = InfluxDB()


@blueprint.route('/')
def home():
    """Load the default landing page"""
    if flask_login.current_user.is_authenticated:
        return redirect(url_for('page_routes.page_live'))
    return clear_cookie_auth()


@blueprint.route('/settings', methods=('GET', 'POST'))
@flask_login.login_required
def page_settings():
    return redirect('settings/general')


@blueprint.route('/remote/<page>', methods=('GET', 'POST'))
@flask_login.login_required
def remote_admin(page):
    """Return pages for remote administration"""
    if not utils_general.user_has_permission('edit_settings'):
        return redirect(url_for('general_routes.home'))

    remote_hosts = Remote.query.all()
    display_order_unsplit = DisplayOrder.query.first().remote_host
    if display_order_unsplit:
        display_order = display_order_unsplit.split(",")
    else:
        display_order = []

    if page == 'setup':
        form_setup = forms_authentication.RemoteSetup()
        host_auth = {}
        for each_host in remote_hosts:
            host_auth[each_host.host] = utils_remote_host.auth_credentials(
                each_host.host, each_host.username, each_host.password_hash)

        if request.method == 'POST':
            form_name = request.form['form-name']
            if form_name == 'setup':
                if form_setup.add.data:
                    utils_remote_host.remote_host_add(
                        form_setup=form_setup, display_order=display_order)
            if form_name == 'mod_remote':
                if form_setup.delete.data:
                    utils_remote_host.remote_host_del(form_setup=form_setup)
            return redirect('/remote/setup')

        return render_template('remote/setup.html',
                               form_setup=form_setup,
                               display_order=display_order,
                               remote_hosts=remote_hosts,
                               host_auth=host_auth)
    else:
        return render_template('404.html'), 404


@blueprint.route('/camera/<camera_id>/<img_type>/<filename>')
@flask_login.login_required
def camera_img(camera_id, img_type, filename):
    """Return an image from stills or timelapses"""
    camera = Camera.query.filter(Camera.id == int(camera_id)).first()
    camera_path = os.path.join(PATH_CAMERAS, '{id}-{uid}'.format(
            id=camera.id, uid=camera.unique_id))

    if img_type in ['still', 'timelapse']:
        path = os.path.join(camera_path, img_type)
        if os.path.isdir(path):
            files = (files for files in os.listdir(path)
                if os.path.isfile(os.path.join(path, files)))
        else:
            files = []
        if filename in files:
            path_file = os.path.join(path, filename)
            resp = make_response(open(path_file).read())
            resp.content_type = "image/jpeg"
            return resp

    return "Image not found"


def gen(camera):
    """Video streaming generator function."""
    while True:
        frame = camera.get_frame()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


@blueprint.route('/video_feed/<unique_id>')
@flask_login.login_required
def video_feed(unique_id):
    """Video streaming route. Put this in the src attribute of an img tag."""
    camera_options = Camera.query.filter(Camera.unique_id == unique_id).first()
    camera_stream = import_module('mycodo.mycodo_flask.camera.camera_' + camera_options.library).Camera
    camera_stream.set_camera_options(camera_options)
    return Response(gen(camera_stream(unique_id=unique_id)),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@blueprint.route('/gpiostate')
@flask_login.login_required
def gpio_state():
    """Return the GPIO state, for relay page status"""
    relay = Relay.query.all()
    daemon_control = DaemonControl()
    state = {}
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    for each_relay in relay:
        if each_relay.relay_type == 'wired' and -1 < each_relay.pin < 40:
            GPIO.setup(each_relay.pin, GPIO.OUT)
            if GPIO.input(each_relay.pin) == each_relay.trigger:
                state[each_relay.id] = 'on'
            else:
                state[each_relay.id] = 'off'
        elif (each_relay.relay_type == 'command' or
                (each_relay.relay_type in ['pwm', 'wireless_433MHz_pi_switch'] and
                 -1 < each_relay.pin < 40)):
            state[each_relay.id] = daemon_control.relay_state(each_relay.id)

    return jsonify(state)


@blueprint.route('/dl/<dl_type>/<path:filename>')
@flask_login.login_required
def download_file(dl_type, filename):
    """Serve log file to download"""
    if dl_type == 'log':
        return send_from_directory(LOG_PATH, filename, as_attachment=True)

    return '', 204


@blueprint.route('/last/<input_measure>/<input_id>/<input_period>')
@flask_login.login_required
def last_data(input_measure, input_id, input_period):
    """Return the most recent time and value from influxdb"""
    current_app.config['INFLUXDB_USER'] = INFLUXDB_USER
    current_app.config['INFLUXDB_PASSWORD'] = INFLUXDB_PASSWORD
    current_app.config['INFLUXDB_DATABASE'] = INFLUXDB_DATABASE
    dbcon = influx_db.connection
    try:
        query_str = query_string(
            input_measure, input_id, value='LAST',
            past_sec=input_period)
        if query_str == 1:
            return '', 204
        raw_data = dbcon.query(query_str).raw
        number = len(raw_data['series'][0]['values'])
        time_raw = raw_data['series'][0]['values'][number - 1][0]
        value = raw_data['series'][0]['values'][number - 1][1]
        value = '{:.3f}'.format(float(value))
        # Convert date-time to epoch (potential bottleneck for data)
        dt = date_parse(time_raw)
        timestamp = calendar.timegm(dt.timetuple()) * 1000
        live_data = '[{},{}]'.format(timestamp, value)
        return Response(live_data, mimetype='text/json')
    except KeyError:
        logger.debug("No Data returned form influxdb")
        return '', 204
    except Exception as e:
        logger.exception("URL for 'last_data' raised and error: "
                         "{err}".format(err=e))
        return '', 204


@blueprint.route('/past/<input_measure>/<input_id>/<past_seconds>')
@flask_login.login_required
@gzipped
def past_data(input_measure, input_id, past_seconds):
    """Return data from past_seconds until present from influxdb"""
    current_app.config['INFLUXDB_USER'] = INFLUXDB_USER
    current_app.config['INFLUXDB_PASSWORD'] = INFLUXDB_PASSWORD
    current_app.config['INFLUXDB_DATABASE'] = INFLUXDB_DATABASE
    dbcon = influx_db.connection
    try:
        query_str = query_string(
            input_measure, input_id, past_sec=past_seconds)
        if query_str == 1:
            return '', 204
        raw_data = dbcon.query(query_str).raw
        if raw_data:
            return jsonify(raw_data['series'][0]['values'])
        else:
            return '', 204
    except Exception as e:
        logger.debug("URL for 'past_data' raised and error: "
                     "{err}".format(err=e))
        return '', 204


@blueprint.route('/export_data/<measurement>/<unique_id>/<start_seconds>/<end_seconds>')
@flask_login.login_required
@gzipped
def export_data(measurement, unique_id, start_seconds, end_seconds):
    """
    Return data from start_seconds to end_seconds from influxdb.
    Used for exporting data.
    """
    current_app.config['INFLUXDB_USER'] = INFLUXDB_USER
    current_app.config['INFLUXDB_PASSWORD'] = INFLUXDB_PASSWORD
    current_app.config['INFLUXDB_DATABASE'] = INFLUXDB_DATABASE
    dbcon = influx_db.connection

    if measurement == 'duration_sec':
        name = Relay.query.filter(Relay.unique_id == unique_id).first().name
    else:
        name = Input.query.filter(Input.unique_id == unique_id).first().name

    utc_offset_timedelta = datetime.datetime.utcnow() - datetime.datetime.now()
    start = datetime.datetime.fromtimestamp(float(start_seconds))
    start += utc_offset_timedelta
    start_str = start.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    end = datetime.datetime.fromtimestamp(float(end_seconds))
    end += utc_offset_timedelta
    end_str = end.strftime('%Y-%m-%dT%H:%M:%S.%fZ')

    query_str = query_string(
        measurement, unique_id,
        start_str=start_str, end_str=end_str)
    if query_str == 1:
        return '', 204
    raw_data = dbcon.query(query_str).raw

    if not raw_data:
        return '', 204

    def iter_csv(data_in):
        line = StringIO.StringIO()
        writer = csv.writer(line)
        write_header = ('timestamp (UTC)', '{name} {meas} ({id})'.format(
            name=name.encode('utf8'), meas=measurement, id=unique_id))
        writer.writerow(write_header)
        for csv_line in data_in:
            writer.writerow((csv_line[0][:-4], csv_line[1]))
            line.seek(0)
            yield line.read()
            line.truncate(0)

    response = Response(iter_csv(raw_data['series'][0]['values']),
                        mimetype='text/csv')
    response.headers['Content-Disposition'] = 'attachment; filename={id}_{meas}.csv'.format(
        id=unique_id, meas=measurement)
    return response


@blueprint.route('/async/<measurement>/<unique_id>/<start_seconds>/<end_seconds>')
@flask_login.login_required
@gzipped
def async_data(measurement, unique_id, start_seconds, end_seconds):
    """
    Return data from start_seconds to end_seconds from influxdb.
    Used for asynchronous graph display of many points (up to millions).
    """
    current_app.config['INFLUXDB_USER'] = INFLUXDB_USER
    current_app.config['INFLUXDB_PASSWORD'] = INFLUXDB_PASSWORD
    current_app.config['INFLUXDB_DATABASE'] = INFLUXDB_DATABASE
    dbcon = influx_db.connection

    # Set the time frame to the past year if start/end not specified
    if start_seconds == '0' and end_seconds == '0':
        # Get how many points there are in the past year
        query_str = query_string(
            measurement, unique_id, value='COUNT')
        if query_str == 1:
            return '', 204
        raw_data = dbcon.query(query_str).raw

        count_points = raw_data['series'][0]['values'][0][1]
        # Get the timestamp of the first point in the past year
        query_str = query_string(
            measurement, unique_id, limit=1)
        if query_str == 1:
            return '', 204
        raw_data = dbcon.query(query_str).raw

        first_point = raw_data['series'][0]['values'][0][0]
        end = datetime.datetime.utcnow()
        end_str = end.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    else:
        start = datetime.datetime.utcfromtimestamp(float(start_seconds))
        start_str = start.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        end = datetime.datetime.utcfromtimestamp(float(end_seconds))
        end_str = end.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        query_str = query_string(
            measurement, unique_id,
            value='COUNT', start_str=start_str, end_str=end_str)
        if query_str == 1:
            return '', 204
        raw_data = dbcon.query(query_str).raw

        count_points = raw_data['series'][0]['values'][0][1]
        # Get the timestamp of the first point in the past year
        query_str = query_string(
            measurement, unique_id,
            start_str=start_str, end_str=end_str, limit=1)
        if query_str == 1:
            return '', 204
        raw_data = dbcon.query(query_str).raw

        first_point = raw_data['series'][0]['values'][0][0]

    start = datetime.datetime.strptime(first_point[:26],
                                       '%Y-%m-%dT%H:%M:%S.%f')
    start_str = start.strftime('%Y-%m-%dT%H:%M:%S.%fZ')

    logger.debug('Count = {}'.format(count_points))
    logger.debug('Start = {}'.format(start))
    logger.debug('End   = {}'.format(end))

    # How many seconds between the start and end period
    time_difference_seconds = (end - start).total_seconds()
    logger.debug('Difference seconds = {}'.format(time_difference_seconds))

    # If there are more than 700 points in the time frame, we need to group
    # data points into 700 groups with points averaged in each group.
    if count_points > 700:
        # Average period between input reads
        seconds_per_point = time_difference_seconds / count_points
        logger.debug('Seconds per point = {}'.format(seconds_per_point))

        # How many seconds to group data points in
        group_seconds = int(time_difference_seconds / 700)
        logger.debug('Group seconds = {}'.format(group_seconds))

        try:
            query_str = query_string(
                measurement, unique_id, value='MEAN',
                start_str=start_str, end_str=end_str,
                group_sec=group_seconds)
            if query_str == 1:
                return '', 204
            raw_data = dbcon.query(query_str).raw

            return jsonify(raw_data['series'][0]['values'])
        except Exception as e:
            logger.error("URL for 'async_data' raised and error: "
                         "{err}".format(err=e))
            return '', 204
    else:
        try:
            query_str = query_string(
                measurement, unique_id,
                start_str=start_str, end_str=end_str)
            if query_str == 1:
                return '', 204
            raw_data = dbcon.query(query_str).raw

            return jsonify(raw_data['series'][0]['values'])
        except Exception as e:
            logger.error("URL for 'async_data' raised and error: "
                         "{err}".format(err=e))
            return '', 204


@blueprint.route('/output_mod/<relay_id>/<state>/<out_type>/<amount>')
@flask_login.login_required
def output_mod(relay_id, state, out_type, amount):
    """Manipulate relay"""
    if not utils_general.user_has_permission('edit_controllers'):
        return 'Insufficient user permissions to manipulate relays'

    daemon = DaemonControl()
    if (state in ['on', 'off'] and out_type == 'sec' and
            (str_is_float(amount) and float(amount) >= 0)):
        return daemon.relay_on_off(int(relay_id), state, float(amount))
    elif (state == 'on' and out_type == 'pwm' and
              (str_is_float(amount) and float(amount) >= 0)):
        return daemon.relay_on(int(relay_id), state, duty_cycle=float(amount))


@blueprint.route('/daemonactive')
@flask_login.login_required
def daemon_active():
    """Return 'alive' if the daemon is running"""
    try:
        control = DaemonControl()
        return control.daemon_status()
    except Exception as e:
        logger.error("URL for 'daemon_active' raised and error: "
                     "{err}".format(err=e))
        return '0'


@blueprint.route('/systemctl/<action>')
@flask_login.login_required
def computer_command(action):
    """Execute one of several commands as root"""
    if not utils_general.user_has_permission('edit_settings'):
        return redirect(url_for('general_routes.home'))

    try:
        if action not in ['restart', 'shutdown']:
            flash("Unrecognized command: {action}".format(
                action=action), "success")
            return redirect('/settings')
        cmd = '{path}/mycodo/scripts/mycodo_wrapper {action} 2>&1'.format(
                path=INSTALL_DIRECTORY, action=action)
        subprocess.Popen(cmd, shell=True)
        if action == 'restart':
            flash(gettext(u"System rebooting in 10 seconds"), "success")
        elif action == 'shutdown':
            flash(gettext(u"System shutting down in 10 seconds"), "success")
        return redirect('/settings')
    except Exception as e:
        logger.error("System command '{cmd}' raised and error: "
                     "{err}".format(cmd=action, err=e))
        flash("System command '{cmd}' raised and error: "
              "{err}".format(cmd=action, err=e), "error")
        return redirect(url_for('general_routes.home'))


@blueprint.route('/newremote/')
def newremote():
    """Verify authentication as a client computer to the remote admin"""
    username = request.args.get('user')
    pass_word = request.args.get('passw')

    user = User.query.filter(
        User.name == username).first()

    # TODO: Change sleep() to max requests per duration of time
    time.sleep(1)  # Slow down requests (hackish, prevent brute force attack)
    if user:
        if User().check_password(pass_word, user.password_hash) == user.password_hash:
            return jsonify(status=0,
                           message="{hash}".format(
                               hash=user.password_hash))
    return jsonify(status=1,
                   message="Unable to authenticate with user and password.")


@blueprint.route('/auth/')
def data():
    """Checks authentication for remote admin"""
    username = request.args.get('user')
    password_hash = request.args.get('pw_hash')

    user = User.query.filter(
        User.name == username).first()

    # TODO: Change sleep() to max requests per duration of time
    time.sleep(1)  # Slow down requests (hackish, prevents brute force attack)
    if (user and
            user.roles.name == 'admin' and
            password_hash == user.password_hash):
        return "0"
    return "1"
