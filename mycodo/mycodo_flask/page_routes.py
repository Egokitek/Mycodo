# coding=utf-8
""" collection of Page endpoints """
import datetime
import flask_login
import glob
import logging
import os
import resource
import subprocess
import sys
import time
from collections import OrderedDict
from flask_babel import gettext
from w1thermsensor import W1ThermSensor

from flask import flash
from flask import redirect
from flask import render_template
from flask import request
from flask import url_for

from flask.blueprints import Blueprint

from mycodo.mycodo_flask.extensions import db
from mycodo.mycodo_flask.static_routes import inject_mycodo_version
from mycodo import flaskforms
from mycodo import flaskutils
from mycodo_client import DaemonControl
from mycodo_client import daemon_active

from mycodo.databases.models import AlembicVersion
from mycodo.databases.models import Camera
from mycodo.databases.models import Conditional
from mycodo.databases.models import ConditionalActions
from mycodo.databases.models import DisplayOrder
from mycodo.databases.models import Graph
from mycodo.databases.models import LCD
from mycodo.databases.models import Method
from mycodo.databases.models import Misc
from mycodo.databases.models import PID
from mycodo.databases.models import Relay
from mycodo.databases.models import Sensor
from mycodo.databases.models import Timer
from mycodo.databases.models import User

from mycodo.devices.camera import CameraStream
from mycodo.devices.camera import camera_record
from mycodo.utils.system_pi import csv_to_list_of_int
from mycodo.utils.tools import return_relay_usage

from config import BACKUP_LOG_FILE
from config import DAEMON_LOG_FILE
from config import HTTP_LOG_FILE
from config import KEEPUP_LOG_FILE
from config import LOGIN_LOG_FILE
from config import RESTORE_LOG_FILE
from config import UPGRADE_LOG_FILE

from config import CONDITIONAL_ACTIONS
from config import DAEMON_PID_FILE
from config import INSTALL_DIRECTORY
from config import MEASUREMENTS
from config import MEASUREMENT_UNITS
from config import PATH_CAMERAS

from config import USAGE_REPORTS_PATH

logger = logging.getLogger('mycodo.mycodo_flask.pages')

blueprint = Blueprint('page_routes',
                      __name__,
                      static_folder='../static',
                      template_folder='../templates')


@blueprint.context_processor
def inject_dictionary():
    return inject_mycodo_version()


@blueprint.context_processor
def epoch_to_time_string():
    def format_timestamp(epoch):
        return datetime.datetime.fromtimestamp(epoch).strftime("%Y-%m-%d %H:%M:%S")
    return dict(format_timestamp=format_timestamp)


@blueprint.route('/camera', methods=('GET', 'POST'))
@flask_login.login_required
def page_camera():
    """
    Page to start/stop video stream or time-lapse, or capture a still image.
    Displays most recent still image and time-lapse image.
    """
    if not flaskutils.user_has_permission('view_camera'):
        return redirect(url_for('general_routes.home'))

    form_camera = flaskforms.Camera()
    camera = Camera.query.all()

    # Check if a video stream is active
    for each_camera in camera:
        if each_camera.stream_started and not CameraStream().is_running():
            each_camera.stream_started = False
            db.session.commit()

    if request.method == 'POST':
        if not flaskutils.user_has_permission('edit_settings'):
            return redirect(url_for('page_routes.page_camera'))

        control = DaemonControl()
        mod_camera = Camera.query.filter(
            Camera.id == form_camera.camera_id.data).first()
        if form_camera.capture_still.data:
            if mod_camera.stream_started:
                flash(gettext(
                    u"Cannot capture still image if stream is active."))
                return redirect('/camera')
            if CameraStream().is_running():
                CameraStream().terminate_controller()  # Stop camera stream
                time.sleep(2)
            camera_record('photo', mod_camera)
        elif form_camera.start_timelapse.data:
            if mod_camera.stream_started:
                flash(gettext(u"Cannot start time-lapse if stream is active."))
                return redirect('/camera')
            now = time.time()
            mod_camera.timelapse_started = True
            mod_camera.timelapse_start_time = now
            mod_camera.timelapse_end_time = now + float(form_camera.timelapse_runtime_sec.data)
            mod_camera.timelapse_interval = form_camera.timelapse_interval.data
            mod_camera.timelapse_next_capture = now
            mod_camera.timelapse_capture_number = 0
            db.session.commit()
            control.refresh_daemon_camera_settings()
        elif form_camera.pause_timelapse.data:
            mod_camera.timelapse_paused = True
            db.session.commit()
            control.refresh_daemon_camera_settings()
        elif form_camera.resume_timelapse.data:
            mod_camera.timelapse_paused = False
            db.session.commit()
            control.refresh_daemon_camera_settings()
        elif form_camera.stop_timelapse.data:
            mod_camera.timelapse_started = False
            mod_camera.timelapse_start_time = None
            mod_camera.timelapse_end_time = None
            mod_camera.timelapse_interval = None
            mod_camera.timelapse_next_capture = None
            mod_camera.timelapse_capture_number = None
            db.session.commit()
            control.refresh_daemon_camera_settings()
        elif form_camera.start_stream.data:
            if mod_camera.timelapse_started:
                flash(gettext(
                    u"Cannot start stream if time-lapse is active."))
                return redirect('/camera')
            elif CameraStream().is_running():
                flash(gettext(
                    u"Cannot start stream. The stream is already running."))
                return redirect('/camera')
            elif (not (mod_camera.camera_type == 'Raspberry Pi' and
                       mod_camera.library == 'picamera')):
                flash(gettext(u"Streaming is only supported with the Raspberry"
                              u" Pi camera using the picamera library."))
                return redirect('/camera')
            elif Camera.query.filter_by(stream_started=True).count():
                flash(gettext(u"Cannot start stream if another stream is "
                              u"already in progress."))
                return redirect('/camera')
            else:
                mod_camera.stream_started = True
                db.session.commit()
        elif form_camera.stop_stream.data:
            if CameraStream().is_running():
                CameraStream().terminate_controller()
            mod_camera.stream_started = False
            db.session.commit()
        return redirect('/camera')

    # Get the full path and timestamps of latest still and time-lapse images
    latest_img_still_ts = {}
    latest_img_still = {}
    latest_img_tl_ts = {}
    latest_img_tl = {}
    for each_camera in camera:
        camera_path = os.path.join(PATH_CAMERAS, '{id}-{uid}'.format(
            id=each_camera.id, uid=each_camera.unique_id))
        try:
            latest_still_img_full_path = max(glob.iglob(
                '{path}/still/Still-{cam_id}-*.jpg'.format(
                    path=camera_path,
                    cam_id=each_camera.id)),
                key=os.path.getmtime)
        except ValueError:
            latest_still_img_full_path = None
        if latest_still_img_full_path:
            ts = os.path.getmtime(latest_still_img_full_path)
            latest_img_still_ts[each_camera.id] = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
            latest_img_still[each_camera.id] = os.path.basename(latest_still_img_full_path)
        else:
            latest_img_still[each_camera.id] = None

        try:
            latest_time_lapse_img_full_path = max(glob.iglob(
                '{path}/timelapse/Timelapse-{cam_id}-*.jpg'.format(
                    path=camera_path,
                    cam_id=each_camera.id)),
                key=os.path.getmtime)
        except ValueError:
            latest_time_lapse_img_full_path = None
        if latest_time_lapse_img_full_path:
            ts = os.path.getmtime(latest_time_lapse_img_full_path)
            latest_img_tl_ts[each_camera.id] = datetime.datetime.fromtimestamp(
                ts).strftime("%Y-%m-%d %H:%M:%S")
            latest_img_tl[each_camera.id] = os.path.basename(
                latest_time_lapse_img_full_path)
        else:
            latest_img_tl[each_camera.id] = None

    time_now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    return render_template('pages/camera.html',
                           camera=camera,
                           form_camera=form_camera,
                           latest_img_still=latest_img_still,
                           latest_img_still_ts=latest_img_still_ts,
                           latest_img_tl=latest_img_tl,
                           latest_img_tl_ts=latest_img_tl_ts,
                           time_now=time_now)


@blueprint.route('/export', methods=('GET', 'POST'))
@flask_login.login_required
def page_export():
    """
    Export measurement data in CSV format
    """
    export_options = flaskforms.ExportOptions()
    relay = Relay.query.all()
    sensor = Sensor.query.all()
    relay_choices = flaskutils.choices_id_name(relay)
    sensor_choices = flaskutils.choices_sensors(sensor)

    if request.method == 'POST':
        start_time = export_options.date_range.data.split(' - ')[0]
        start_seconds = int(time.mktime(
            time.strptime(start_time, '%m/%d/%Y %H:%M')))
        end_time = export_options.date_range.data.split(' - ')[1]
        end_seconds = int(time.mktime(
            time.strptime(end_time, '%m/%d/%Y %H:%M')))

        unique_id = export_options.measurement.data.split(',')[0]
        measurement = export_options.measurement.data.split(',')[1]

        url = '/export_data/{meas}/{id}/{start}/{end}'.format(
            meas=measurement,
            id=unique_id,
            start=start_seconds, end=end_seconds)
        return redirect(url)

    # Generate start end end times for date/time picker
    end_picker = datetime.datetime.now().strftime('%m/%d/%Y %H:%M')
    start_picker = datetime.datetime.now() - datetime.timedelta(hours=6)
    start_picker = start_picker.strftime('%m/%d/%Y %H:%M')

    return render_template('tools/export.html',
                           start_picker=start_picker,
                           end_picker=end_picker,
                           exportOptions=export_options,
                           relay_choices=relay_choices,
                           sensor_choices=sensor_choices)


@blueprint.route('/graph', methods=('GET', 'POST'))
@flask_login.login_required
def page_graph():
    """
    Generate custom graphs to display sensor data retrieved from influxdb.
    """
    # Create form objects
    form_mod_graph = flaskforms.GraphMod()
    form_del_graph = flaskforms.GraphDel()
    form_order_graph = flaskforms.GraphOrder()
    form_add_graph = flaskforms.GraphAdd()

    # Retrieve the order to display graphs
    display_order = csv_to_list_of_int(DisplayOrder.query.first().graph)

    # Retrieve tables from SQL database
    graph = Graph.query.all()
    pid = PID.query.all()
    relay = Relay.query.all()
    sensor = Sensor.query.all()

    # Retrieve all choices to populate form drop-down menu
    pid_choices = flaskutils.choices_pids(pid)
    relay_choices = flaskutils.choices_id_name(relay)
    sensor_choices = flaskutils.choices_sensors(sensor)

    # Add multi-select values as form choices, for validation
    form_mod_graph.pid_ids.choices = []
    form_mod_graph.relay_ids.choices = []
    form_mod_graph.sensor_ids.choices = []
    for key, value in pid_choices.items():
        form_mod_graph.pid_ids.choices.append((key, value))
    for key, value in relay_choices.items():
        form_mod_graph.relay_ids.choices.append((key, value))
    for key, value in sensor_choices.items():
        form_mod_graph.sensor_ids.choices.append((key, value))

    # Generate dictionary of custom colors for each graph
    dict_colors = dict_custom_colors()

    # Detect which form on the page was submitted
    if request.method == 'POST':
        if not flaskutils.user_has_permission('edit_controllers'):
            return redirect(url_for('general_routes.home'))

        form_name = request.form['form-name']
        if form_name == 'modGraph':
            flaskutils.graph_mod(form_mod_graph, request.form)
        elif form_name == 'delGraph':
            flaskutils.graph_del(form_del_graph)
        elif form_order_graph.orderGraphUp.data:
            flaskutils.graph_reorder(form_order_graph.orderGraph_id.data,
                                     display_order, 'up')
        elif form_order_graph.orderGraphDown.data:
            flaskutils.graph_reorder(form_order_graph.orderGraph_id.data,
                                     display_order, 'down')
        elif form_name == 'addGraph':
            flaskutils.graph_add(form_add_graph, display_order)
        return redirect('/graph')

    return render_template('pages/graph.html',
                           graph=graph,
                           pid=pid,
                           relay=relay,
                           sensor=sensor,
                           pid_choices=pid_choices,
                           relay_choices=relay_choices,
                           sensor_choices=sensor_choices,
                           dict_colors=dict_colors,
                           measurement_units=MEASUREMENT_UNITS,
                           displayOrder=display_order,
                           form_mod_graph=form_mod_graph,
                           form_del_graph=form_del_graph,
                           form_order_graph=form_order_graph,
                           form_add_graph=form_add_graph)


@blueprint.route('/graph-async', methods=('GET', 'POST'))
@flask_login.login_required
def page_graph_async():
    """ Generate graphs using asynchronous data retrieval """
    sensor = Sensor.query.all()
    sensor_choices = flaskutils.choices_sensors(sensor)
    sensor_choices_split = OrderedDict()
    for key in sensor_choices:
        order = key.split(",")
        # Separate sensor IDs and measurement types
        sensor_choices_split.update({order[0]: order[1]})

    selected_id = None
    selected_measure = None
    selected_unique_id = None

    if request.method == 'POST':
        selected_id = request.form['selected_measure'].split(",")[0]
        selected_measure = request.form['selected_measure'].split(",")[1]
        selected_unique_id = Sensor.query.filter(Sensor.unique_id == selected_id).first().unique_id

    return render_template('pages/graph-async.html',
                           sensor=sensor,
                           sensor_choices=sensor_choices,
                           sensor_choices_split=sensor_choices_split,
                           selected_id=selected_id,
                           selected_measure=selected_measure,
                           selected_unique_id=selected_unique_id)


@blueprint.route('/help', methods=('GET', 'POST'))
@flask_login.login_required
def page_help():
    """ Display Mycodo manual/help """
    return render_template('manual.html')


@blueprint.route('/info', methods=('GET', 'POST'))
@flask_login.login_required
def page_info():
    """ Display page with system information from command line tools """
    if not flaskutils.user_has_permission('view_stats'):
        return redirect(url_for('general_routes.home'))

    uptime = subprocess.Popen(
        "uptime", stdout=subprocess.PIPE, shell=True)
    (uptime_output, _) = uptime.communicate()
    uptime.wait()

    uname = subprocess.Popen(
        "uname -a", stdout=subprocess.PIPE, shell=True)
    (uname_output, _) = uname.communicate()
    uname.wait()

    gpio = subprocess.Popen(
        "gpio readall", stdout=subprocess.PIPE, shell=True)
    (gpio_output, _) = gpio.communicate()
    gpio.wait()

    df = subprocess.Popen(
        "df -h", stdout=subprocess.PIPE, shell=True)
    (df_output, _) = df.communicate()
    df.wait()

    free = subprocess.Popen(
        "free -h", stdout=subprocess.PIPE, shell=True)
    (free_output, _) = free.communicate()
    free.wait()

    ifconfig = subprocess.Popen(
        "ifconfig -a", stdout=subprocess.PIPE, shell=True)
    (ifconfig_output, _) = ifconfig.communicate()
    ifconfig.wait()

    daemon_pid = None
    if os.path.exists(DAEMON_PID_FILE):
        with open(DAEMON_PID_FILE, 'r') as pid_file:
            daemon_pid = int(pid_file.read())

    database_version = []
    for each_ver in AlembicVersion.query.all():
        database_version.append(each_ver.version_num)

    virtualenv_flask = False
    if hasattr(sys, 'real_prefix'):
        virtualenv_flask = True

    virtualenv_daemon = False
    pstree_output = None
    top_output = None
    daemon_up = daemon_active()
    if daemon_up:
        control = DaemonControl()
        ram_use_daemon = control.ram_use()
        virtualenv_daemon = control.is_in_virtualenv()

        pstree = subprocess.Popen(
            "pstree -p {pid}".format(pid=daemon_pid), stdout=subprocess.PIPE, shell=True)
        (pstree_output, _) = pstree.communicate()
        pstree.wait()

        top = subprocess.Popen(
            "top -bH -n 1 -p {pid}".format(pid=daemon_pid), stdout=subprocess.PIPE, shell=True)
        (top_output, _) = top.communicate()
        top.wait()
    else:
        ram_use_daemon = 0

    ram_use_flask = resource.getrusage(
        resource.RUSAGE_SELF).ru_maxrss / float(1000)

    return render_template('pages/info.html',
                           daemon_pid=daemon_pid,
                           daemon_up=daemon_up,
                           gpio_readall=gpio_output,
                           database_version=database_version,
                           df=df_output,
                           free=free_output,
                           ifconfig=ifconfig_output,
                           pstree=pstree_output,
                           ram_use_daemon=ram_use_daemon,
                           ram_use_flask=ram_use_flask,
                           top=top_output,
                           uname=uname_output,
                           uptime=uptime_output,
                           virtualenv_daemon=virtualenv_daemon,
                           virtualenv_flask=virtualenv_flask)


@blueprint.route('/lcd', methods=('GET', 'POST'))
@flask_login.login_required
def page_lcd():
    """ Display LCD output settings """
    lcd = LCD.query.all()
    pid = PID.query.all()
    relay = Relay.query.all()
    sensor = Sensor.query.all()

    display_order = csv_to_list_of_int(DisplayOrder.query.first().lcd)

    form_add_lcd = flaskforms.LCDAdd()
    form_mod_lcd = flaskforms.LCDMod()

    if request.method == 'POST':
        if not flaskutils.user_has_permission('edit_controllers'):
            return redirect(url_for('general_routes.home'))

        if form_add_lcd.add.data:
            flaskutils.lcd_add(form_add_lcd.quantity.data)
        elif form_mod_lcd.save.data:
            flaskutils.lcd_mod(form_mod_lcd)
        elif form_mod_lcd.delete.data:
            flaskutils.lcd_del(form_mod_lcd.lcd_id.data)
        elif form_mod_lcd.reorder_up.data:
            flaskutils.lcd_reorder(form_mod_lcd.lcd_id.data,
                                   display_order, 'up')
        elif form_mod_lcd.reorder_down.data:
            flaskutils.lcd_reorder(form_mod_lcd.lcd_id.data,
                                   display_order, 'down')
        elif form_mod_lcd.activate.data:
            flaskutils.lcd_activate(form_mod_lcd.lcd_id.data)
        elif form_mod_lcd.deactivate.data:
            flaskutils.lcd_deactivate(form_mod_lcd.lcd_id.data)
        elif form_mod_lcd.reset_flashing.data:
            flaskutils.lcd_reset_flashing(form_mod_lcd.lcd_id.data)
        return redirect('/lcd')

    return render_template('pages/lcd.html',
                           lcd=lcd,
                           measurements=MEASUREMENTS,
                           pid=pid,
                           relay=relay,
                           sensor=sensor,
                           displayOrder=display_order,
                           form_add_lcd=form_add_lcd,
                           form_mod_lcd=form_mod_lcd)


@blueprint.route('/live', methods=('GET', 'POST'))
@flask_login.login_required
def page_live():
    """ Page of recent and updating sensor data """
    # Retrieve tables for the data displayed on the live page
    pid = PID.query.all()
    relay = Relay.query.all()
    sensor = Sensor.query.all()
    timer = Timer.query.all()

    # Display orders
    pid_display_order = csv_to_list_of_int(
        DisplayOrder.query.first().pid)
    sensor_display_order = csv_to_list_of_int(
        DisplayOrder.query.first().sensor)

    # Filter only activated sensors
    sensor_order_sorted = []
    if sensor_display_order:
        for each_sensor_order in sensor_display_order:
            for each_sensor in sensor:
                if (each_sensor_order == each_sensor.id and
                        each_sensor.is_activated):
                    sensor_order_sorted.append(each_sensor.id)

    # Retrieve only parent method columns
    method = Method.query.all()

    return render_template('pages/live.html',
                           measurement_units=MEASUREMENT_UNITS,
                           method=method,
                           pid=pid,
                           relay=relay,
                           sensor=sensor,
                           timer=timer,
                           pidDisplayOrder=pid_display_order,
                           sensorDisplayOrderSorted=sensor_order_sorted)


@blueprint.route('/logview', methods=('GET', 'POST'))
@flask_login.login_required
def page_logview():
    """ Display the last (n) lines from a log file """
    if not flaskutils.user_has_permission('view_logs'):
        return redirect(url_for('general_routes.home'))

    form_log_view = flaskforms.LogView()
    log_output = None
    lines = 30
    logfile = ''
    if request.method == 'POST':
        if form_log_view.lines.data:
            lines = form_log_view.lines.data

        if form_log_view.loglogin.data:
            logfile = LOGIN_LOG_FILE
        elif form_log_view.loghttp.data:
            logfile = HTTP_LOG_FILE
        elif form_log_view.logdaemon.data:
            logfile = DAEMON_LOG_FILE
        elif form_log_view.logkeepup.data:
            logfile = KEEPUP_LOG_FILE
        elif form_log_view.logbackup.data:
            logfile = BACKUP_LOG_FILE
        elif form_log_view.logrestore.data:
            logfile = RESTORE_LOG_FILE
        elif form_log_view.logupgrade.data:
            logfile = UPGRADE_LOG_FILE

        # Get contents from file
        if os.path.isfile(logfile):
            command = 'tail -n {lines} {log}'.format(lines=lines,
                                                     log=logfile)
            log = subprocess.Popen(
                command, stdout=subprocess.PIPE, shell=True)
            (log_output, _) = log.communicate()
            log.wait()
            log_output = unicode(log_output, 'utf-8')
        else:
            log_output = 404

    return render_template('tools/logview.html',
                           form_log_view=form_log_view,
                           lines=lines,
                           logfile=logfile,
                           log_output=log_output)


@blueprint.route('/pid', methods=('GET', 'POST'))
@flask_login.login_required
def page_pid():
    """ Display PID settings """
    pids = PID.query.all()
    relay = Relay.query.all()
    sensor = Sensor.query.all()

    display_order = csv_to_list_of_int(DisplayOrder.query.first().pid)

    form_add_pid = flaskforms.PIDAdd()
    form_mod_pid = flaskforms.PIDMod()

    method = Method.query.all()

    if request.method == 'POST':
        if not flaskutils.user_has_permission('edit_controllers'):
            return redirect(url_for('general_routes.home'))

        form_name = request.form['form-name']
        if form_name == 'addPID':
            flaskutils.pid_add(form_add_pid)
        elif form_name == 'modPID':
            if form_mod_pid.delete.data:
                flaskutils.pid_del(
                    form_mod_pid.pid_id.data)
            elif form_mod_pid.reorder_up.data:
                flaskutils.pid_reorder(
                    form_mod_pid.pid_id.data, display_order, 'up')
            elif form_mod_pid.reorder_down.data:
                flaskutils.pid_reorder(
                    form_mod_pid.pid_id.data, display_order, 'down')
            elif form_mod_pid.activate.data:
                flaskutils.pid_activate(
                    form_mod_pid.pid_id.data)
            elif form_mod_pid.deactivate.data:
                flaskutils.pid_deactivate(
                    form_mod_pid.pid_id.data)
            elif form_mod_pid.hold.data:
                flaskutils.pid_manipulate(
                    form_mod_pid.pid_id.data, 'Hold')
            elif form_mod_pid.pause.data:
                flaskutils.pid_manipulate(
                    form_mod_pid.pid_id.data, 'Pause')
            elif form_mod_pid.resume.data:
                flaskutils.pid_manipulate(
                    form_mod_pid.pid_id.data, 'Resume')
            else:
                flaskutils.pid_mod(form_mod_pid)

        return redirect('/pid')

    return render_template('pages/pid.html',
                           method=method,
                           pids=pids,
                           relay=relay,
                           sensor=sensor,
                           displayOrder=display_order,
                           form_add_pid=form_add_pid,
                           form_mod_pid=form_mod_pid)


@blueprint.route('/relay', methods=('GET', 'POST'))
@flask_login.login_required
def page_relay():
    """ Display relay status and config """
    camera = Camera.query.all()
    lcd = LCD.query.all()
    relay = Relay.query.all()
    user = User.query.all()

    conditional = Conditional.query.filter(
        Conditional.conditional_type == 'relay').all()
    conditional_actions = ConditionalActions.query.all()

    display_order = csv_to_list_of_int(DisplayOrder.query.first().relay)

    form_add_relay = flaskforms.RelayAdd()
    form_mod_relay = flaskforms.RelayMod()

    form_conditional = flaskforms.Conditional()
    form_conditional_actions = flaskforms.ConditionalActions()

    # Create list of file names from the sensor_options directory
    # Used in generating the correct options for each sensor/device
    relay_templates = []
    relay_path = os.path.join(
        INSTALL_DIRECTORY,
        'mycodo/mycodo_flask/templates/pages/relay_options')
    for (_, _, file_names) in os.walk(relay_path):
        relay_templates.extend(file_names)
        break

    if request.method == 'POST':
        if not flaskutils.user_has_permission('edit_controllers'):
            return redirect(url_for('page_routes.page_relay'))

        if form_add_relay.relay_add.data:
            flaskutils.relay_add(form_add_relay)
        elif form_mod_relay.save.data:
            flaskutils.relay_mod(form_mod_relay)
        elif (form_mod_relay.turn_on.data or
                form_mod_relay.turn_off.data or
                form_mod_relay.on_submit.data):
            flaskutils.relay_on_off(form_mod_relay)
        elif form_mod_relay.delete.data:
            flaskutils.relay_del(form_mod_relay)
        elif form_mod_relay.order_up.data:
            flaskutils.relay_reorder(form_mod_relay.relay_id.data,
                                     display_order, 'up')
        elif form_mod_relay.order_down.data:
            flaskutils.relay_reorder(form_mod_relay.relay_id.data,
                                     display_order, 'down')
        elif form_conditional.add_cond.data:
            flaskutils.conditional_add(form_conditional.conditional_type.data,
                                       form_conditional.quantity.data)
        elif form_conditional.delete_cond.data:
            flaskutils.conditional_mod(form_conditional, 'delete')
        elif form_conditional.save_cond.data:
            flaskutils.conditional_mod(form_conditional, 'modify')
        elif form_conditional.activate_cond.data:
            flaskutils.conditional_activate(form_conditional)
        elif form_conditional.deactivate_cond.data:
            flaskutils.conditional_deactivate(form_conditional)
        elif form_conditional_actions.add_action.data:
            flaskutils.conditional_action_add(form_conditional_actions)
        elif form_conditional_actions.save_action.data:
            flaskutils.conditional_action_mod(form_conditional_actions,
                                              'modify')
        elif form_conditional_actions.delete_action.data:
            flaskutils.conditional_action_mod(form_conditional_actions,
                                              'delete')
        return redirect('/relay')

    return render_template('pages/relay.html',
                           camera=camera,
                           conditional=conditional,
                           conditional_actions=conditional_actions,
                           conditional_actions_list=CONDITIONAL_ACTIONS,
                           displayOrder=display_order,
                           form_conditional=form_conditional,
                           form_conditional_actions=form_conditional_actions,
                           form_add_relay=form_add_relay,
                           form_mod_relay=form_mod_relay,
                           lcd=lcd,
                           relay=relay,
                           relay_templates=relay_templates,
                           user=user)


@blueprint.route('/sensor', methods=('GET', 'POST'))
@flask_login.login_required
def page_sensor():
    """ Display sensor settings """
    # TCA9548A I2C multiplexer
    multiplexer_addresses = [
        '0x70',
        '0x71',
        '0x72',
        '0x73',
        '0x74',
        '0x75',
        '0x76',
        '0x77'
    ]
    multiplexer_channels = list(range(0, 9))

    camera = Camera.query.all()
    lcd = LCD.query.all()
    pid = PID.query.all()
    relay = Relay.query.all()
    sensor = Sensor.query.all()
    user = User.query.all()

    conditional = Conditional.query.filter(
        Conditional.conditional_type == 'sensor').all()
    conditional_actions = ConditionalActions.query.all()

    display_order = csv_to_list_of_int(DisplayOrder.query.first().sensor)

    form_add_sensor = flaskforms.SensorAdd()
    form_mod_sensor = flaskforms.SensorMod()

    form_conditional = flaskforms.Conditional()
    form_conditional_actions = flaskforms.ConditionalActions()

    # If DS18B20 sensors added, compile a list of detected sensors
    ds18b20_sensors = []
    if Sensor.query.filter(Sensor.device == 'DS18B20').count():
        try:
            for each_sensor in W1ThermSensor.get_available_sensors():
                ds18b20_sensors.append(each_sensor.id)
        except OSError:
            flash("Unable to detect sensors in '/sys/bus/w1/devices'",
                  "error")

    # Create list of file names from the sensor_options directory
    # Used in generating the correct options for each sensor/device
    sensor_templates = []
    sensor_path = os.path.join(
        INSTALL_DIRECTORY,
        'mycodo/mycodo_flask/templates/pages/sensor_options')
    for (_, _, file_names) in os.walk(sensor_path):
        sensor_templates.extend(file_names)
        break

    if request.method == 'POST':
        if not flaskutils.user_has_permission('edit_controllers'):
            return redirect(url_for('page_routes.page_sensor'))

        if form_add_sensor.sensorAddSubmit.data:
            flaskutils.sensor_add(form_add_sensor)
        elif form_mod_sensor.modSensorSubmit.data:
            flaskutils.sensor_mod(form_mod_sensor)
        elif form_mod_sensor.delSensorSubmit.data:
            flaskutils.sensor_del(form_mod_sensor)
        elif form_mod_sensor.orderSensorUp.data:
            flaskutils.sensor_reorder(form_mod_sensor.modSensor_id.data,
                                      display_order, 'up')
        elif form_mod_sensor.orderSensorDown.data:
            flaskutils.sensor_reorder(form_mod_sensor.modSensor_id.data,
                                      display_order, 'down')
        elif form_mod_sensor.activateSensorSubmit.data:
            flaskutils.sensor_activate(form_mod_sensor)
        elif form_mod_sensor.deactivateSensorSubmit.data:
            flaskutils.sensor_deactivate(form_mod_sensor)

        elif form_conditional.deactivate_cond.data:
            flaskutils.conditional_deactivate(form_conditional)
        elif form_conditional.activate_cond.data:
            flaskutils.conditional_activate(form_conditional)
        elif form_mod_sensor.sensorCondAddSubmit.data:
            flaskutils.conditional_add(
                'sensor', 1, sensor_id=form_mod_sensor.modSensor_id.data)
        elif form_conditional.delete_cond.data:
            flaskutils.conditional_mod(form_conditional, 'delete')
        elif form_conditional.save_cond.data:
            flaskutils.conditional_mod(form_conditional, 'modify')
        elif form_conditional_actions.add_action.data:
            flaskutils.conditional_action_add(form_conditional_actions)
        elif form_conditional_actions.save_action.data:
            flaskutils.conditional_action_mod(form_conditional_actions,
                                              'modify')
        elif form_conditional_actions.delete_action.data:
            flaskutils.conditional_action_mod(form_conditional_actions,
                                              'delete')
        return redirect('/sensor')

    return render_template('pages/sensor.html',
                           camera=camera,
                           conditional=conditional,
                           conditional_actions=conditional_actions,
                           conditional_actions_list=CONDITIONAL_ACTIONS,
                           displayOrder=display_order,
                           ds18b20_sensors=ds18b20_sensors,
                           form_add_sensor=form_add_sensor,
                           form_conditional=form_conditional,
                           form_conditional_actions=form_conditional_actions,
                           form_mod_sensor=form_mod_sensor,
                           lcd=lcd,
                           measurements=MEASUREMENTS,
                           multiplexer_addresses=multiplexer_addresses,
                           multiplexer_channels=multiplexer_channels,
                           pid=pid,
                           relay=relay,
                           sensor=sensor,
                           sensor_templates=sensor_templates,
                           units=MEASUREMENT_UNITS,
                           user=user)


@blueprint.route('/timer', methods=('GET', 'POST'))
@flask_login.login_required
def page_timer():
    """ Display Timer settings """
    timer = Timer.query.all()
    relay = Relay.query.all()
    relay_choices = flaskutils.choices_id_name(relay)

    display_order = csv_to_list_of_int(DisplayOrder.query.first().timer)

    form_timer = flaskforms.Timer()

    if request.method == 'POST':
        if not flaskutils.user_has_permission('edit_controllers'):
            return redirect(url_for('general_routes.home'))

        form_name = request.form['form-name']
        if form_name == 'addTimer':
            flaskutils.timer_add(form_timer,
                                 request.form['timer_type'],
                                 display_order)
        elif form_name == 'modTimer':
            if form_timer.delete.data:
                flaskutils.timer_del(form_timer)
            elif form_timer.order_up.data:
                flaskutils.timer_reorder(form_timer.timer_id.data,
                                         display_order, 'up')
            elif form_timer.order_down.data:
                flaskutils.timer_reorder(form_timer.timer_id.data,
                                         display_order, 'down')
            elif form_timer.activate.data:
                flaskutils.timer_activate(form_timer)
            elif form_timer.deactivate.data:
                flaskutils.timer_deactivate(form_timer)
            elif form_timer.modify.data:
                flaskutils.timer_mod(form_timer)
        return redirect('/timer')

    return render_template('pages/timer.html',
                           timer=timer,
                           displayOrder=display_order,
                           relay_choices=relay_choices,
                           form_timer=form_timer)


@blueprint.route('/usage', methods=('GET', 'POST'))
@flask_login.login_required
def page_usage():
    """ Display relay usage (duration and energy usage/cost) """
    if not flaskutils.user_has_permission('view_stats'):
        return redirect(url_for('general_routes.home'))

    misc = Misc.query.first()
    relay = Relay.query.all()

    relay_stats = return_relay_usage(misc, relay)

    day = misc.relay_usage_dayofmonth
    if 4 <= day <= 20 or 24 <= day <= 30:
        date_suffix = 'th'
    else:
        date_suffix = ['st', 'nd', 'rd'][day % 10 - 1]

    display_order = csv_to_list_of_int(DisplayOrder.query.first().relay)

    return render_template('pages/usage.html',
                           date_suffix=date_suffix,
                           display_order=display_order,
                           misc=misc,
                           relay=relay,
                           relay_stats=relay_stats,
                           timestamp=time.strftime("%c"))


@blueprint.route('/usage_reports', methods=('GET', 'POST'))
@flask_login.login_required
def page_usage_reports():
    """ Display relay usage (duration and energy usage/cost) """
    if not flaskutils.user_has_permission('view_stats'):
        return redirect(url_for('general_routes.home'))

    report_location = os.path.normpath(USAGE_REPORTS_PATH)
    reports = [0, 0]

    return render_template('pages/usage_reports.html',
                           report_location=report_location,
                           reports=reports)


def dict_custom_colors():
    """
    Generate lists of custom colors from CSV strings saved in the database.
    If custom colors aren't already saved, fill in with a default palette.

    :return: dictionary of graph_ids and lists of custom colors
    """
    dark_themes = ['cyborg', 'darkly', 'slate', 'sun', 'superhero']
    if flask_login.current_user.theme in dark_themes:
        default_palette = [
            '#2b908f', '#90ee7e', '#f45b5b', '#7798BF', '#aaeeee', '#ff0066',
            '#eeaaee', '#55BF3B', '#DF5353', '#7798BF', '#aaeeee'
        ]
    else:
        default_palette = [
            '#7cb5ec', '#434348', '#90ed7d', '#f7a35c', '#8085e9', '#f15c80',
            '#e4d354', '#2b908f', '#f45b5b', '#91e8e1'
        ]

    color_count = OrderedDict()

    try:
        graph = Graph.query.all()
        for each_graph in graph:
            # Get current saved colors
            if each_graph.custom_colors:  # Split into list
                colors = each_graph.custom_colors.split(',')
            else:  # Create empty list
                colors = []
            # Fill end of list with empty strings
            while len(colors) < len(default_palette):
                colors.append('')

            # Populate empty strings with default colors
            for x, _ in enumerate(default_palette):
                if colors[x] == '':
                    colors[x] = default_palette[x]

            index = 0
            index_sum = 0
            total = []
            if each_graph.sensor_ids_measurements:
                for each_set in each_graph.sensor_ids_measurements.split(';'):
                    sensor_unique_id = each_set.split(',')[0]
                    sensor_measure = each_set.split(',')[1]
                    sensor = Sensor.query.filter_by(
                        unique_id=sensor_unique_id).first()
                    if (index < len(each_graph.sensor_ids_measurements.split(';')) and
                            len(colors) > index):
                        color = colors[index]
                    else:
                        color = '#FF00AA'
                    if sensor is not None:
                        total.append({
                            'unique_id': sensor_unique_id,
                            'name': sensor.name,
                            'measure': sensor_measure,
                            'color': color})
                        index += 1
                index_sum += index

            if each_graph.relay_ids:
                index = 0
                for each_set in each_graph.relay_ids.split(','):
                    relay_unique_id = each_set.split(',')[0]
                    relay = Relay.query.filter_by(
                        unique_id=relay_unique_id).first()
                    if (index < len(each_graph.relay_ids.split(',')) and
                            len(colors) > index_sum + index):
                        color = colors[index_sum+index]
                    else:
                        color = '#FF00AA'
                    if relay is not None:
                        total.append({
                            'unique_id': relay_unique_id,
                            'name': relay.name,
                            'measure': 'relay duration',
                            'color': color})
                        index += 1
                index_sum += index

            if each_graph.pid_ids:
                index = 0
                for each_set in each_graph.pid_ids.split(';'):
                    pid_unique_id = each_set.split(',')[0]
                    pid_measure = each_set.split(',')[1]
                    pid = PID.query.filter_by(
                        unique_id=pid_unique_id).first()
                    if (index < len(each_graph.pid_ids.split(';')) and
                            len(colors) > index_sum + index):
                        color = colors[index_sum+index]
                    else:
                        color = '#FF00AA'
                    if pid is not None:
                        total.append({
                            'unique_id': pid_unique_id,
                            'name': pid.name,
                            'measure': pid_measure,
                            'color': color})
                        index += 1

            color_count.update({each_graph.id: total})
    except IndexError:
        # Expected exception from previous version database
        # TODO: Remove this exception in next major version release
        pass

    return color_count


def gen(camera):
    """ Video streaming generator function """
    while True:
        frame = camera.get_frame()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
