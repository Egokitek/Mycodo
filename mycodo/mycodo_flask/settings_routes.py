# coding=utf-8
""" collection of Page endpoints """
import logging
import operator

from flask import (
    redirect,
    render_template,
    request,
    session,
    url_for
)
from flask.blueprints import Blueprint

# Classes
from mycodo.databases.mycodo_db.models import (
    Camera,
    Misc,
    Role,
    SMTP,
    User
)

# Functions
from mycodo import flaskforms
from mycodo import flaskutils

# Config
from config import LANGUAGES

from mycodo.mycodo_flask.general_routes import (
    inject_mycodo_version,
    logged_in
)

logger = logging.getLogger('mycodo.mycodo_flask.settings')

blueprint = Blueprint('settings_routes',
                      __name__,
                      static_folder='../static',
                      template_folder='../templates')


@blueprint.context_processor
def inject_dictionary():
    return inject_mycodo_version()


@blueprint.route('/settings/alerts', methods=('GET', 'POST'))
def settings_alerts():
    """ Display alert settings """
    if not logged_in():
        return redirect(url_for('general_routes.home'))

    if not flaskutils.authorized(session, 'Guest'):
        flaskutils.deny_guest_user()
        return redirect(url_for('settings_routes.settings_general'))

    smtp = SMTP.query.first()
    form_email_alert = flaskforms.EmailAlert()

    if request.method == 'POST':
        form_name = request.form['form-name']
        # Update smtp settings table in mycodo SQL database
        if form_name == 'EmailAlert':
            flaskutils.settings_alert_mod(form_email_alert)
        return redirect(url_for('settings_routes.settings_alerts'))

    return render_template('settings/alerts.html',
                           smtp=smtp,
                           form_email_alert=form_email_alert)


@blueprint.route('/settings/camera', methods=('GET', 'POST'))
def settings_camera():
    """ Display camera settings """
    if not logged_in():
        return redirect(url_for('general_routes.home'))

    camera = Camera.query.all()
    form_settings_camera = flaskforms.SettingsCamera()

    if request.method == 'POST':
        form_name = request.form['form-name']
        if form_name == 'Camera':
            flaskutils.settings_camera_mod(form_settings_camera)
        return redirect(url_for('settings_routes.settings_camera'))

    return render_template('settings/camera.html',
                           camera=camera,
                           form_settings_camera=form_settings_camera)


@blueprint.route('/settings/general', methods=('GET', 'POST'))
def settings_general():
    """ Display general settings """
    if not logged_in():
        return redirect(url_for('general_routes.home'))

    misc = Misc.query.first()
    form_settings_general = flaskforms.SettingsGeneral()

    languages_sorted = sorted(LANGUAGES.items(), key=operator.itemgetter(1))

    if request.method == 'POST':
        form_name = request.form['form-name']
        if form_name == 'General':
            flaskutils.settings_general_mod(form_settings_general)
        return redirect(url_for('settings_routes.settings_general'))

    return render_template('settings/general.html',
                           misc=misc,
                           languages=languages_sorted,
                           form_settings_general=form_settings_general)


@blueprint.route('/settings/users', methods=('GET', 'POST'))
def settings_users():
    """ Display user settings """
    if not logged_in():
        return redirect(url_for('general_routes.home'))

    if not flaskutils.authorized(session, 'Admin'):
        flaskutils.deny_guest_user()
        return redirect(url_for('settings_routes.settings_general'))

    users = User.query.all()
    user_roles = Role.query.all()
    form_add_user = flaskforms.AddUser()
    form_mod_user = flaskforms.ModUser()
    form_del_user = flaskforms.DelUser()

    if request.method == 'POST':
        form_name = request.form['form-name']
        if form_name == 'addUser':
            flaskutils.user_add(form_add_user)
        elif form_name == 'delUser':
            if flaskutils.user_del(form_del_user) == 'logout':
                return redirect('/logout')
        elif form_name == 'modUser':
            if flaskutils.user_mod(form_mod_user) == 'logout':
                return redirect('/logout')
        return redirect(url_for('settings_routes.settings_users'))

    return render_template('settings/users.html',
                           users=users,
                           user_roles=user_roles,
                           form_add_user=form_add_user,
                           form_mod_user=form_mod_user,
                           form_del_user=form_del_user)
