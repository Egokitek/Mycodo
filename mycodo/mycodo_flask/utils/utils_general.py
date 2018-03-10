# -*- coding: utf-8 -*-
import glob
import importlib
import logging
from collections import OrderedDict
from datetime import datetime

import flask_login
import os
import sqlalchemy
from flask import flash
from flask import redirect
from flask import url_for
from flask_babel import gettext

from mycodo.config import DEVICE_INFO
from mycodo.config import LIST_DEVICES_ADC
from mycodo.config import MATH_INFO
from mycodo.config import MEASUREMENT_UNITS
from mycodo.config import METHOD_INFO
from mycodo.config import PATH_CAMERAS
from mycodo.databases.models import Camera
from mycodo.databases.models import Conditional
from mycodo.databases.models import Input
from mycodo.databases.models import LCD
from mycodo.databases.models import Math
from mycodo.databases.models import PID
from mycodo.databases.models import Role
from mycodo.databases.models import Timer
from mycodo.databases.models import User
from mycodo.mycodo_client import DaemonControl
from mycodo.mycodo_flask.extensions import db

logger = logging.getLogger(__name__)


#
# Activate/deactivate controller
#

def controller_activate_deactivate(controller_action,
                                   controller_type,
                                   controller_id):
    """
    Activate or deactivate controller

    :param controller_action: Activate or deactivate
    :type controller_action: str
    :param controller_type: The controller type (LCD, Math, PID, Input, Timer)
    :type controller_type: str
    :param controller_id: Controller with ID to activate or deactivate
    :type controller_id: str
    """
    if not user_has_permission('edit_controllers'):
        return redirect(url_for('routes_general.home'))

    activated = bool(controller_action == 'activate')

    translated_names = {
        "Conditional": gettext("Conditional"),
        "Input": gettext("Input"),
        "LCD": gettext("LCD"),
        "Math": gettext("Math"),
        "PID": gettext("PID"),
        "Timer": gettext("Timer")
    }

    mod_controller = None
    if controller_type == 'Conditional':
        mod_controller = Conditional.query.filter(
            Conditional.id == int(controller_id)).first()
    elif controller_type == 'Input':
        mod_controller = Input.query.filter(
            Input.id == int(controller_id)).first()
    elif controller_type == 'LCD':
        mod_controller = LCD.query.filter(
            LCD.id == int(controller_id)).first()
    elif controller_type == 'Math':
        mod_controller = Math.query.filter(
            Math.id == int(controller_id)).first()
    elif controller_type == 'PID':
        mod_controller = PID.query.filter(
            PID.id == int(controller_id)).first()
    elif controller_type == 'Timer':
        mod_controller = Timer.query.filter(
            Timer.id == int(controller_id)).first()

    if mod_controller is None:
        flash("{type} Controller {id} doesn't exist".format(
            type=controller_type, id=controller_id), "error")
        return redirect(url_for('routes_general.home'))

    try:
        mod_controller.is_activated = activated
        db.session.commit()

        if activated:
            flash(gettext("%(cont)s controller activated in SQL database",
                          cont=translated_names[controller_type]),
                  "success")
        else:
            flash(gettext("%(cont)s controller deactivated in SQL database",
                          cont=translated_names[controller_type]),
                  "success")
    except Exception as except_msg:
        flash(gettext("Error: %(err)s",
                      err='SQL: {msg}'.format(msg=except_msg)),
              "error")

    try:
        control = DaemonControl()
        if controller_action == 'activate':
            return_values = control.controller_activate(controller_type,
                                                        int(controller_id))
        else:
            return_values = control.controller_deactivate(controller_type,
                                                          int(controller_id))
        if return_values[0]:
            flash("{err}".format(err=return_values[1]), "error")
        else:
            flash("{err}".format(err=return_values[1]), "success")
    except Exception as except_msg:
        flash(gettext("Error: %(err)s",
                      err='Daemon: {msg}'.format(msg=except_msg)),
              "error")


#
# Choices
#

def choices_inputs(inputs):
    """ populate form multi-select choices from Input entries """
    choices = OrderedDict()
    for each_input in inputs:
        if each_input.device == 'LinuxCommand':
            value = '{id},{meas}'.format(
                id=each_input.unique_id,
                meas=each_input.cmd_measurement)
            display = '[Input {id:02d}] {name} ({meas})'.format(
                id=each_input.id,
                name=each_input.name,
                meas=each_input.cmd_measurement)
            choices.update({value: display})
        else:
            for each_name, each_dict in DEVICE_INFO[each_input.device].items():
                if each_name == 'measure':
                    for each_measure in each_dict:
                        value = '{id},{meas}'.format(
                            id=each_input.unique_id,
                            meas=each_measure)
                        display = '[Input {id:02d}] {name} ({meas})'.format(
                            id=each_input.id,
                            name=each_input.name,
                            meas=MEASUREMENT_UNITS[each_measure]['name'])
                        choices.update({value: display})
            # Display custom converted units for ADCs
            if each_input.device in LIST_DEVICES_ADC:
                value = '{id},{meas}'.format(
                    id=each_input.unique_id,
                    meas=each_input.adc_measure)
                display = '[Input {id:02d}] {name} ({meas})'.format(
                    id=each_input.id,
                    name=each_input.name,
                    meas=each_input.adc_measure)
                choices.update({value: display})
    return choices


def choices_maths(maths):
    """ populate form multi-select choices from Math entries """
    choices = OrderedDict()
    for each_math in maths:
        for each_measurement in each_math.measure.split(','):
            value = '{id},{measure}'.format(
                id=each_math.unique_id,
                measure=each_measurement)

            if each_measurement in MEASUREMENT_UNITS:
                measurement_display = MEASUREMENT_UNITS[each_measurement]['name']
            else:
                measurement_display = each_measurement
            display = '[Math {id:02d}] {name} ({meas})'.format(
                id=each_math.id,
                name=each_math.name,
                meas=measurement_display)
            choices.update({value: display})
    return choices


def choices_outputs(output):
    """ populate form multi-select choices from Output entries """
    choices = OrderedDict()
    for each_output in output:
        if each_output.relay_type in ['pwm', 'command_pwm']:
            value = '{id},duty_cycle'.format(id=each_output.unique_id)
            display = '[Output {id:02d}] {name} (Duty Cycle)'.format(
                id=each_output.id, name=each_output.name)
            choices.update({value: display})
        else:
            value = '{id},duration_sec'.format(id=each_output.unique_id)
            display = '[Output {id:02d}] {name} (Duration)'.format(
                id=each_output.id, name=each_output.name)
            choices.update({value: display})
    return choices


def choices_pids(pid):
    """ populate form multi-select choices from PID entries """
    choices = OrderedDict()
    for each_pid in pid:
        value = '{id},setpoint'.format(id=each_pid.unique_id)
        display = '[PID {id:02d}] {name} (Setpoint)'.format(
            id=each_pid.id, name=each_pid.name)
        choices.update({value: display})
        value = '{id},setpoint_band_min'.format(id=each_pid.unique_id)
        display = '[PID {id:02d}] {name} (Band Min)'.format(
            id=each_pid.id, name=each_pid.name)
        choices.update({value: display})
        value = '{id},setpoint_band_max'.format(id=each_pid.unique_id)
        display = '[PID {id:02d}] {name} (Band Max)'.format(
            id=each_pid.id, name=each_pid.name)
        choices.update({value: display})
        value = '{id},pid_p_value'.format(id=each_pid.unique_id)
        display = '[PID {id:02d}] {name} (P-Value)'.format(
            id=each_pid.id, name=each_pid.name)
        choices.update({value: display})
        value = '{id},pid_i_value'.format(id=each_pid.unique_id)
        display = '[PID {id:02d}] {name} (I-Value)'.format(
            id=each_pid.id, name=each_pid.name)
        choices.update({value: display})
        value = '{id},pid_d_value'.format(id=each_pid.unique_id)
        display = '[PID {id:02d}] {name} (D-Value)'.format(
            id=each_pid.id, name=each_pid.name)
        choices.update({value: display})
        value = '{id},pid_output'.format(id=each_pid.unique_id)
        display = '[PID {id:02d}] {name} (Output Duration)'.format(
            id=each_pid.id, name=each_pid.name)
        choices.update({value: display})
        value = '{id},duty_cycle'.format(id=each_pid.unique_id)
        display = '[PID {id:02d}] {name} (Output Duty Cycle)'.format(
            id=each_pid.id, name=each_pid.name)
        choices.update({value: display})
    return choices


def choices_id_name(table):
    """ Return a dictionary of all available ids and names of a table """
    choices = OrderedDict()
    for each_entry in table:
        value = each_entry.unique_id
        display = '[{id:02d}] {name}'.format(id=each_entry.id,
                                          name=each_entry.name)
        choices.update({value: display})
    return choices


def user_has_permission(permission):
    user = User.query.filter(User.name == flask_login.current_user.name).first()
    role = Role.query.filter(Role.id == user.role).first()
    if ((permission == 'edit_settings' and role.edit_settings) or
        (permission == 'edit_controllers' and role.edit_controllers) or
        (permission == 'edit_users' and role.edit_users) or
        (permission == 'view_settings' and role.view_settings) or
        (permission == 'view_camera' and role.view_camera) or
        (permission == 'view_stats' and role.view_stats) or
        (permission == 'view_logs' and role.view_logs)):
        return True
    flash("You don't have permission to do that", "error")
    return False


def delete_entry_with_id(table, entry_id):
    """ Delete SQL database entry with specific id """
    try:
        entries = table.query.filter(
            table.id == entry_id).first()
        db.session.delete(entries)
        db.session.commit()
        flash(gettext("%(msg)s",
                      msg='{action} {table} with ID: {id}'.format(
                          action=gettext("Delete"),
                          table=table.__tablename__,
                          id=entry_id)),
              "success")
        return 1
    except sqlalchemy.orm.exc.NoResultFound:
        flash(gettext("%(err)s",
                      err=gettext("Entry with ID %(id)s not found",
                                  id=entry_id)),
              "error")
        flash(gettext("%(msg)s",
                      msg='{action} {id}: {err}'.format(
                          action=gettext("Delete"),
                          id=entry_id,
                          err=gettext("Entry with ID %(id)s not found",
                                      id=entry_id))),
              "success")
        return 0


def flash_form_errors(form):
    """ Flashes form errors for easier display """
    for field, errors in form.errors.items():
        for error in errors:
            flash(gettext("Error in the %(field)s field - %(err)s",
                          field=getattr(form, field).label.text,
                          err=error),
                  "error")


def flash_success_errors(error, action, redirect_url):
    if error:
        for each_error in error:
            flash(gettext("%(msg)s",
                          msg='{action}: {err}'.format(
                              action=action,
                              err=each_error)),
                  "error")
        return redirect(redirect_url)
    else:
        flash(gettext("%(msg)s",
                      msg=action),
              "success")


def add_display_order(display_order, device_id):
    """ Add integer ID to list of string IDs """
    if display_order:
        display_order.append(device_id)
        display_order = [str(i) for i in display_order]
        return ','.join(display_order)
    return str(device_id)


def reorder(display_order, device_id, direction):
    if direction == 'up':
        status, reord_list = reorder_list(
            display_order,
            device_id,
            'up')
    elif direction == 'down':
        status, reord_list = reorder_list(
            display_order,
            device_id,
            'down')
    else:
        status = "Fail"
        reord_list = "unrecognized command"
    return status, reord_list


def reorder_list(modified_list, item, direction):
    """ Reorder entry in a comma-separated list either up or down """
    from_position = modified_list.index(item)
    if direction == "up":
        if from_position == 0:
            return 'error', gettext('Cannot move above the first item in the list')
        to_position = from_position - 1
    elif direction == 'down':
        if from_position == len(modified_list) - 1:
            return 'error', gettext('Cannot move below the last item in the list')
        to_position = from_position + 1
    else:
        return 'error', []
    modified_list.insert(to_position, modified_list.pop(from_position))
    return 'success', modified_list


def test_sql():
    try:
        num_entries = 1000000
        factor_info = 25000
        PID.query.delete()
        db.session.commit()
        logger.error("Starting SQL uuid generation test: "
                     "{n} entries...".format(n=num_entries))
        before_count = PID.query.count()
        run_times = []
        a = datetime.now()
        for x in range(1, num_entries + 1):
            db.session.add(PID())
            if x % factor_info == 0:
                db.session.commit()
                after_count = PID.query.count()
                b = datetime.now()
                run_times.append(float((b - a).total_seconds()))
                logger.error("Run Time: {time:.2f} sec, "
                             "New entries: {new}, "
                             "Total entries: {tot}".format(
                                time=run_times[-1],
                                new=after_count - before_count,
                                tot=PID.query.count()))
                before_count = PID.query.count()
                a = datetime.now()
        avg_run_time = sum(run_times) / float(len(run_times))
        logger.error("Finished. Total: {tot} entries. "
                     "Averages: {avg:.2f} sec, "
                     "{epm:.2f} entries/min".format(
                        tot=PID.query.count(),
                        avg=avg_run_time,
                        epm=(factor_info / avg_run_time) * 60.0))
    except Exception as msg:
        logger.error("Error creating entries: {err}".format(err=msg))


def get_camera_image_info():
    """ Retrieve information about the latest camera images """
    latest_img_still_ts = {}
    latest_img_still = {}
    latest_img_tl_ts = {}
    latest_img_tl = {}

    camera = Camera.query.all()

    for each_camera in camera:
        camera_path = os.path.join(PATH_CAMERAS, '{uid}'.format(
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
            latest_img_still_ts[each_camera.unique_id] = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
            latest_img_still[each_camera.unique_id] = os.path.basename(latest_still_img_full_path)
        else:
            latest_img_still[each_camera.unique_id] = None

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
            latest_img_tl_ts[each_camera.unique_id] = datetime.fromtimestamp(
                ts).strftime("%Y-%m-%d %H:%M:%S")
            latest_img_tl[each_camera.unique_id] = os.path.basename(
                latest_time_lapse_img_full_path)
        else:
            latest_img_tl[each_camera.unique_id] = None

    return (latest_img_still_ts, latest_img_still,
            latest_img_tl_ts, latest_img_tl)


def return_dependencies(device_type, dep_type='unmet'):
    unmet_deps = []
    met_deps = False

    list_dependencies = [
        DEVICE_INFO,
        MATH_INFO,
        METHOD_INFO
    ]
    for each_section in list_dependencies:
        if device_type in each_section:
            for each_device, each_dict in each_section[device_type].items():
                if each_device == 'py-dependencies':
                    for each_dep in each_dict:
                        try:
                            module = importlib.util.find_spec(each_dep)
                            if module is None:
                                if each_dep not in unmet_deps:
                                    unmet_deps.append(each_dep)
                            else:
                                met_deps = True
                        except ImportError:
                            if each_dep not in unmet_deps:
                                unmet_deps.append(each_dep)

                    if each_dict == []:
                        met_deps = True

    if dep_type == 'unmet':
        return unmet_deps
    else:
        return met_deps
