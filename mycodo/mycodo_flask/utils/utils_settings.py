# -*- coding: utf-8 -*-
import logging

import bcrypt
import flask_login
import os
import sqlalchemy
from flask import flash
from flask import redirect
from flask import url_for
from flask_babel import gettext

from mycodo.config import INSTALL_DIRECTORY
from mycodo.databases.models import Camera
from mycodo.databases.models import Misc
from mycodo.databases.models import Role
from mycodo.databases.models import SMTP
from mycodo.databases.models import User
from mycodo.mycodo_client import DaemonControl
from mycodo.mycodo_flask.extensions import db
from mycodo.mycodo_flask.utils.utils_general import delete_entry_with_id
from mycodo.mycodo_flask.utils.utils_general import flash_form_errors
from mycodo.mycodo_flask.utils.utils_general import flash_success_errors
from mycodo.utils.database import db_retrieve_table
from mycodo.utils.send_data import send_email
from mycodo.utils.utils import test_password
from mycodo.utils.utils import test_username

logger = logging.getLogger(__name__)


#
# User manipulation
#

def user_roles(form):
    action = None
    if form.add_role.data:
        action = gettext("Add")
    elif form.save_role.data:
        action = gettext("Modify")
    elif form.delete_role.data:
        action = gettext("Delete")

    action = '{action} {controller}'.format(
        action=action,
        controller=gettext("User Role"))
    error = []

    if not error:
        if form.add_role.data:
            new_role = Role()
            new_role.name = form.name.data
            new_role.view_logs = form.view_logs.data
            new_role.view_camera = form.view_camera.data
            new_role.view_stats = form.view_stats.data
            new_role.view_settings = form.view_settings.data
            new_role.edit_users = form.edit_users.data
            new_role.edit_settings = form.edit_settings.data
            new_role.edit_controllers = form.edit_controllers.data
            try:
                new_role.save()
            except sqlalchemy.exc.OperationalError as except_msg:
                error.append(except_msg)
            except sqlalchemy.exc.IntegrityError as except_msg:
                error.append(except_msg)
        elif form.save_role.data:
            mod_role = Role.query.filter(Role.id == form.role_id.data).first()
            mod_role.view_logs = form.view_logs.data
            mod_role.view_camera = form.view_camera.data
            mod_role.view_stats = form.view_stats.data
            mod_role.view_settings = form.view_settings.data
            mod_role.edit_users = form.edit_users.data
            mod_role.edit_settings = form.edit_settings.data
            mod_role.edit_controllers = form.edit_controllers.data
            db.session.commit()
        elif form.delete_role.data:
            if User().query.filter(User.role == form.role_id.data).count():
                error.append(
                    "Cannot delete role if it is assigned to a user. "
                    "Change the user to another role and try again.")
            else:
                delete_entry_with_id(Role,
                                     form.role_id.data)
    flash_success_errors(error, action, url_for('routes_settings.settings_users'))


def user_add(form):
    action = '{action} {controller} {user}'.format(
        action=gettext("Add"),
        controller=gettext("User"),
        user=form.user_name.data.lower())
    error = []

    if form.validate():
        new_user = User()
        new_user.name = form.user_name.data.lower()
        if not test_username(new_user.name):
            error.append(gettext(
                "Invalid user name. Must be between 2 and 64 characters "
                "and only contain letters and numbers."))

        new_user.email = form.email.data
        if User.query.filter_by(email=new_user.email).count():
            error.append(gettext(
                "Another user already has that email address."))

        if not test_password(form.password_new.data):
            error.append(gettext(
                "Invalid password. Must be between 6 and 64 characters "
                "and only contain letters, numbers, and symbols."))

        if form.password_new.data != form.password_repeat.data:
            error.append(gettext("Passwords do not match. Please try again."))

        if not error:
            new_user.set_password(form.password_new.data)
            role = Role.query.filter(
                Role.name == form.addRole.data).first().id
            new_user.role = role
            new_user.theme = form.theme.data
            try:
                new_user.save()
            except sqlalchemy.exc.OperationalError as except_msg:
                error.append(except_msg)
            except sqlalchemy.exc.IntegrityError as except_msg:
                error.append(except_msg)

        flash_success_errors(error, action, url_for('routes_settings.settings_users'))
    else:
        flash_form_errors(form)


def user_mod(form):
    mod_user = User.query.filter(
        User.id == form.user_id.data).first()
    action = '{action} {controller} {user}'.format(
        action=gettext("Modify"),
        controller=gettext("User"),
        user=mod_user.name)
    error = []

    try:
        mod_user = User.query.filter(
            User.id == form.user_id.data).first()
        mod_user.email = form.email.data
        # Only change the password if it's entered in the form
        logout_user = False
        if form.password_new.data != '':
            if not test_password(form.password_new.data):
                error.append(gettext("Invalid password"))
            if form.password_new.data != form.password_repeat.data:
                error.append(gettext("Passwords do not match. Please try again."))
            mod_user.password_hash = bcrypt.hashpw(
                form.password_new.data.encode('utf-8'),
                bcrypt.gensalt())
            if flask_login.current_user.id == form.user_id.data:
                logout_user = True

        current_role = Role.query.filter(
            Role.name == form.role.data).first()
        if mod_user.role == 1 and mod_user.role != current_role.id:
            error.append("Cannot change currently-logged in user's role from Admin")

        if not error:
            role = Role.query.filter(
                Role.name == form.role.data).first().id
            mod_user.role = role
            mod_user.theme = form.theme.data
            db.session.commit()
            if logout_user:
                return 'logout'
    except Exception as except_msg:
        error.append(except_msg)

    flash_success_errors(error, action, url_for('routes_settings.settings_users'))


def user_del(form):
    """ Delete user from SQL database """
    user_name = User.query.filter(User.id == form.user_id.data).first().name
    action = '{action} {controller} {user}'.format(
        action=gettext("Delete"),
        controller=gettext("User"),
        user=user_name)
    error = []

    if form.user_id.data == flask_login.current_user.id:
        error.append("Cannot delete the currently-logged in user")

    if not error:
        try:
            user = User.query.filter(
                User.id == form.user_id.data).first()
            user.delete()
        except Exception as except_msg:
            error.append(except_msg)

    flash_success_errors(error, action, url_for('routes_settings.settings_users'))


#
# Settings modifications
#

def settings_general_mod(form):
    """ Modify General settings """
    action = '{action} {controller}'.format(
        action=gettext("Modify"),
        controller=gettext("General Settings"))
    error = []

    if form.validate():
        if (form.relay_usage_report_span.data == 'monthly' and
                not 0 < form.relay_usage_report_day.data < 29):
            error.append("Day Options: Daily: 1-7 (1=Monday), Monthly: 1-28")
        elif (form.relay_usage_report_span.data == 'weekly' and
                not 0 < form.relay_usage_report_day.data < 8):
            error.append("Day Options: Daily: 1-7 (1=Monday), Monthly: 1-28")

        if not error:
            try:
                mod_misc = Misc.query.first()
                force_https = mod_misc.force_https
                mod_misc.force_https = form.force_https.data
                mod_misc.hide_alert_success = form.hide_success.data
                mod_misc.hide_alert_info = form.hide_info.data
                mod_misc.hide_alert_warning = form.hide_warning.data
                mod_misc.hide_tooltips = form.hide_tooltips.data
                mod_misc.max_amps = form.max_amps.data
                mod_misc.relay_usage_volts = form.relay_stats_volts.data
                mod_misc.relay_usage_cost = form.relay_stats_cost.data
                mod_misc.relay_usage_currency = form.relay_stats_currency.data
                mod_misc.relay_usage_dayofmonth = form.relay_stats_day_month.data
                mod_misc.relay_usage_report_gen = form.relay_usage_report_gen.data
                mod_misc.relay_usage_report_span = form.relay_usage_report_span.data
                mod_misc.relay_usage_report_day = form.relay_usage_report_day.data
                mod_misc.relay_usage_report_hour = form.relay_usage_report_hour.data
                mod_misc.stats_opt_out = form.stats_opt_out.data
                mod_misc.enable_upgrade_check = form.enable_upgrade_check.data

                mod_user = User.query.filter(User.id == flask_login.current_user.id).first()
                mod_user.language = form.language.data

                db.session.commit()
                control = DaemonControl()
                control.refresh_daemon_misc_settings()

                if force_https != form.force_https.data:
                    # Force HTTPS option changed.
                    # Reload web server with new settings.
                    wsgi_file = '{inst_dir}/mycodo_flask.wsgi'.format(
                        inst_dir=INSTALL_DIRECTORY)
                    with open(wsgi_file, 'a'):
                        os.utime(wsgi_file, None)

            except Exception as except_msg:
                error.append(except_msg)

        flash_success_errors(error, action, url_for('routes_settings.settings_general'))
    else:
        flash_form_errors(form)


def settings_alert_mod(form_mod_alert):
    """ Modify Alert settings """
    action = '{action} {controller}'.format(
        action=gettext("Modify"),
        controller=gettext("Alert Settings"))
    error = []

    try:
        if form_mod_alert.validate():
            mod_smtp = SMTP.query.one()
            if form_mod_alert.send_test.data:
                send_email(
                    mod_smtp.host, mod_smtp.ssl, mod_smtp.port,
                    mod_smtp.user, mod_smtp.passw, mod_smtp.email_from,
                    form_mod_alert.send_test_to_email.data,
                    "This is a test email from Mycodo")
                flash(gettext("Test email sent to %(recip)s. Check your "
                              "inbox to see if it was successful.",
                              recip=form_mod_alert.send_test_to_email.data),
                      "success")
                return redirect(url_for('routes_settings.settings_alerts'))
            else:
                mod_smtp.host = form_mod_alert.smtp_host.data
                mod_smtp.port = form_mod_alert.smtp_port.data
                mod_smtp.ssl = form_mod_alert.smtp_ssl.data
                mod_smtp.user = form_mod_alert.smtp_user.data
                if form_mod_alert.smtp_password.data:
                    mod_smtp.passw = form_mod_alert.smtp_password.data
                mod_smtp.email_from = form_mod_alert.smtp_from_email.data
                mod_smtp.hourly_max = form_mod_alert.smtp_hourly_max.data
                db.session.commit()
        else:
            flash_form_errors(form_mod_alert)
    except Exception as except_msg:
        error.append(except_msg)

    flash_success_errors(error, action, url_for('routes_settings.settings_alerts'))


def camera_add(form_camera):
    action = '{action} {controller}'.format(
        action=gettext("Add"),
        controller=gettext("Camera"))
    error = []

    if form_camera.validate():
        new_camera = Camera()
        if Camera.query.filter(Camera.name == form_camera.name.data).count():
            flash("You must choose a unique name", "error")
            return redirect(url_for('routes_settings.settings_camera'))
        new_camera.name = form_camera.name.data
        new_camera.library = form_camera.library.data
        if form_camera.library.data == 'fswebcam':
            new_camera.device = '/dev/video0'
            new_camera.brightness = 50
        elif form_camera.library.data == 'picamera':
            new_camera.brightness = 50
            new_camera.contrast = 0.0
            new_camera.exposure = 0.0
            new_camera.saturation = 0.0
        if not error:
            try:
                new_camera.save()
            except sqlalchemy.exc.OperationalError as except_msg:
                error.append(except_msg)
            except sqlalchemy.exc.IntegrityError  as except_msg:
                error.append(except_msg)

        flash_success_errors(error, action, url_for('routes_settings.settings_camera'))
    else:
        flash_form_errors(form_camera)


def camera_mod(form_camera):
    action = '{action} {controller}'.format(
        action=gettext("Modify"),
        controller=gettext("Camera"))
    error = []

    try:
        if (Camera.query
                .filter(Camera.id != form_camera.camera_id.data)
                .filter(Camera.name == form_camera.name.data).count()):
            flash("You must choose a unique name", "error")
            return redirect(url_for('routes_settings.settings_camera'))
        if 0 > form_camera.rotation.data > 360:
            flash("Rotation must be between 0 and 360 degrees", "error")
            return redirect(url_for('routes_settings.settings_camera'))

        mod_camera = Camera.query.filter(
            Camera.id == form_camera.camera_id.data).first()
        mod_camera.name = form_camera.name.data

        if mod_camera.library == 'fswebcam':
            mod_camera.hflip = form_camera.hflip.data
            mod_camera.vflip = form_camera.vflip.data
            mod_camera.rotation = form_camera.rotation.data
            mod_camera.height = form_camera.height.data
            mod_camera.width = form_camera.width.data
            mod_camera.brightness = form_camera.brightness.data
        elif mod_camera.library == 'picamera':
            mod_camera.hflip = form_camera.hflip.data
            mod_camera.vflip = form_camera.vflip.data
            mod_camera.rotation = form_camera.rotation.data
            mod_camera.height = form_camera.height.data
            mod_camera.width = form_camera.width.data
            mod_camera.brightness = form_camera.brightness.data
            mod_camera.contrast = form_camera.contrast.data
            mod_camera.exposure = form_camera.exposure.data
            mod_camera.saturation = form_camera.saturation.data
        else:
            error.append("Unknown camera library")

        if form_camera.relay_id.data:
            mod_camera.relay_id = form_camera.relay_id.data
        else:
            mod_camera.relay_id = None
        mod_camera.cmd_pre_camera = form_camera.cmd_pre_camera.data
        mod_camera.cmd_post_camera = form_camera.cmd_post_camera.data

        if not error:
            db.session.commit()
            control = DaemonControl()
            control.refresh_daemon_camera_settings()
    except Exception as except_msg:
        logger.exception(1)
        error.append(except_msg)

    flash_success_errors(error, action, url_for('routes_settings.settings_camera'))


def camera_del(form_camera):
    action = '{action} {controller}'.format(
        action=gettext("Delete"),
        controller=gettext("Camera"))
    error = []

    camera = db_retrieve_table(
        Camera, device_id=form_camera.camera_id.data)
    if camera.timelapse_started:
        error.append("Cannot delete camera if a time-lapse is currently "
                     "using it. Stop the time-lapse and try again.")

    if not error:
        try:
            delete_entry_with_id(
                Camera, int(form_camera.camera_id.data))
        except Exception as except_msg:
            error.append(except_msg)

    flash_success_errors(error, action, url_for('routes_settings.settings_camera'))
