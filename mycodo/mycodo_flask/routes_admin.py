# coding=utf-8
""" collection of Admin endpoints """
import logging
import subprocess
from collections import OrderedDict

import flask_login
import os
from flask import Blueprint
from flask import flash
from flask import make_response
from flask import redirect
from flask import render_template
from flask import request
from flask import url_for
from flask_babel import gettext
from pkg_resources import parse_version

from mycodo.config import BACKUP_LOG_FILE
from mycodo.config import BACKUP_PATH
from mycodo.config import FORCE_UPGRADE_MASTER
from mycodo.config import INSTALL_DIRECTORY
from mycodo.config import MEASUREMENTS
from mycodo.config import MYCODO_VERSION
from mycodo.config import RESTORE_LOG_FILE
from mycodo.config import STATS_CSV
from mycodo.config import UPGRADE_INIT_FILE
from mycodo.config import UPGRADE_LOG_FILE
from mycodo.databases.models import Misc
from mycodo.mycodo_flask.extensions import db
from mycodo.mycodo_flask.forms import forms_dependencies
from mycodo.mycodo_flask.forms import forms_misc
from mycodo.mycodo_flask.routes_static import inject_variables
from mycodo.mycodo_flask.utils import utils_general
from mycodo.utils.github_release_info import github_releases
from mycodo.utils.statistics import return_stat_file_dict
from mycodo.utils.system_pi import can_perform_backup
from mycodo.utils.system_pi import get_directory_size
from mycodo.utils.system_pi import internet

logger = logging.getLogger('mycodo.mycodo_flask.admin')

blueprint = Blueprint(
    'routes_admin',
    __name__,
    static_folder='../static',
    template_folder='../templates'
)


@blueprint.context_processor
@flask_login.login_required
def inject_dictionary():
    return inject_variables()


@blueprint.route('/admin/backup', methods=('GET', 'POST'))
@flask_login.login_required
def admin_backup():
    """ Load the backup management page """
    if not utils_general.user_has_permission('edit_settings'):
        return redirect(url_for('routes_general.home'))

    form_backup = forms_misc.Backup()

    backup_dirs_tmp = []
    if not os.path.isdir('/var/Mycodo-backups'):
        flash("Error: Backup directory doesn't exist.", "error")
    else:
        backup_dirs_tmp = sorted(next(os.walk(BACKUP_PATH))[1])
        backup_dirs_tmp.reverse()

    backup_dirs = []
    full_paths = []
    for each_dir in backup_dirs_tmp:
        if each_dir.startswith("Mycodo-backup-"):
            full_path = os.path.join(BACKUP_PATH, each_dir)
            backup_dirs.append((each_dir, get_directory_size(full_path) / 1000000.0))
            full_paths.append(full_path)

    if request.method == 'POST':
        if form_backup.backup.data:
            backup_size, free_before, free_after = can_perform_backup()
            if free_after / 1000000 > 50:
                cmd = "{pth}/mycodo/scripts/mycodo_wrapper backup-create" \
                      " | ts '[%Y-%m-%d %H:%M:%S]'" \
                      " >> {log} 2>&1".format(pth=INSTALL_DIRECTORY,
                                              log=BACKUP_LOG_FILE)
                subprocess.Popen(cmd, shell=True)
                flash(gettext("Backup in progress"), "success")
            else:
                flash(
                    "Not enough free space to perform a backup. A backup "
                    "requires {size_bu:.1f} MB but there is only "
                    "{size_free:.1f} MB available, which would leave "
                    "{size_after:.1f} MB after the backup. If the free space "
                    "after a backup is less than 50 MB, the backup cannot "
                    "proceed. Free up space by deleting current "
                    "backups.".format(size_bu=backup_size / 1000000,
                                      size_free=free_before / 1000000,
                                      size_after=free_after / 1000000),
                    'error')

        elif form_backup.delete.data:
            cmd = "{pth}/mycodo/scripts/mycodo_wrapper backup-delete {dir}" \
                  " 2>&1".format(pth=INSTALL_DIRECTORY,
                                 dir=form_backup.selected_dir.data)
            subprocess.Popen(cmd, shell=True)
            flash(gettext("Deletion of backup in progress"),
                  "success")

        elif form_backup.restore.data:
            cmd = "{pth}/mycodo/scripts/mycodo_wrapper backup-restore {backup}" \
                  " | ts '[%Y-%m-%d %H:%M:%S]'" \
                  " >> {log} 2>&1".format(pth=INSTALL_DIRECTORY,
                                          backup=form_backup.full_path.data,
                                          log=RESTORE_LOG_FILE)
            subprocess.Popen(cmd, shell=True)
            flash(gettext("Restore in progress"),
                  "success")

    return render_template('admin/backup.html',
                           form_backup=form_backup,
                           backup_dirs=backup_dirs,
                           full_paths=full_paths)


@blueprint.route('/admin/dependencies', methods=('GET', 'POST'))
@flask_login.login_required
def admin_dependencies_main():
    return redirect(url_for('routes_admin.admin_dependencies', device='0'))


@blueprint.route('/admin/dependencies/<device>', methods=('GET', 'POST'))
@flask_login.login_required
def admin_dependencies(device):
    """ Display Dependency page """
    form_dependencies = forms_dependencies.Dependencies()

    if device != '0':
        device_unmet_dependencies = utils_general.return_dependencies(device)
    elif form_dependencies.device.data:
        device_unmet_dependencies = utils_general.return_dependencies(form_dependencies.device.data)
    else:
        device_unmet_dependencies = []

    unmet_dependencies = OrderedDict()
    unmet_exist = False
    met_dependencies = OrderedDict()
    met_exist = False
    unmet_list = {}
    for each_device, each_dict in MEASUREMENTS.items():
        # Determine if there are any unmet dependencies
        unmet_dependencies.update({
            each_device: utils_general.return_dependencies(
                each_device)
        })
        if utils_general.return_dependencies(each_device) != []:
            unmet_exist = True

        # Determine if there are any met dependencies
        met_dependencies.update({
            each_device: utils_general.return_dependencies(
                each_device, dep_type='met')
        })
        if utils_general.return_dependencies(
                each_device, dep_type='met'):
            met_exist = True

        # Find all the devices that use each unmet dependency
        if unmet_dependencies[each_device]:
            for each_dep in unmet_dependencies[each_device]:
                if each_dep not in unmet_list:
                    unmet_list[each_dep] = []
                if each_device not in unmet_list[each_dep]:
                    unmet_list[each_dep].append(each_device)

    if request.method == 'POST':
        if not utils_general.user_has_permission('edit_controllers'):
            return redirect(url_for('routes_admin.admin_dependencies', device=device))

        if form_dependencies.install.data:
            for each_dep in device_unmet_dependencies:
                if each_dep == 'Adafruit_BME280':
                    cmd = "{pth}/env/bin/pip3 install -e git://github.com/adafruit/Adafruit_Python_BME280.git#egg=adafruit-bme280" \
                          " | ts '[%Y-%m-%d %H:%M:%S]' 2>&1".format(
                        pth=INSTALL_DIRECTORY)
                    flash("Successfully installed {dep}".format(dep=each_dep), "success")
                    dep = subprocess.Popen(cmd, shell=True)
                    dep.wait()
                elif each_dep == 'tsl2591':
                    cmd = "{pth}/env/bin/pip3 install -e git://github.com/maxlklaxl/python-tsl2591.git#egg=tsl2591" \
                          " | ts '[%Y-%m-%d %H:%M:%S]' 2>&1".format(
                        pth=INSTALL_DIRECTORY)
                    flash("Successfully installed {dep}".format(dep=each_dep), "success")
                    dep = subprocess.Popen(cmd, shell=True)
                    dep.wait()
                else:
                    cmd = "/bin/bash {pth}/mycodo/scripts/user_commands.sh install-pip-dependency {dep}" \
                          " | ts '[%Y-%m-%d %H:%M:%S]' 2>&1".format(
                        pth=INSTALL_DIRECTORY,
                        dep=each_dep)
                    flash("Successfully installed {dep}".format(dep=each_dep), "success")
                    dep = subprocess.Popen(cmd, shell=True)
                    dep.wait()

            cmd = "{pth}/mycodo/scripts/mycodo_wrapper initialize" \
                  " | ts '[%Y-%m-%d %H:%M:%S]' 2>&1".format(
                pth=INSTALL_DIRECTORY)
            init = subprocess.Popen(cmd, shell=True)
            init.wait()

        return redirect(url_for('routes_admin.admin_dependencies', device='0'))

    return render_template('admin/dependencies.html',
                           measurements=MEASUREMENTS,
                           unmet_list=unmet_list,
                           device=device,
                           unmet_dependencies=unmet_dependencies,
                           unmet_exist=unmet_exist,
                           met_dependencies=met_dependencies,
                           met_exist=met_exist,
                           form_dependencies=form_dependencies,
                           device_unmet_dependencies=device_unmet_dependencies)


@blueprint.route('/admin/statistics', methods=('GET', 'POST'))
@flask_login.login_required
def admin_statistics():
    """ Display collected statistics """
    if not utils_general.user_has_permission('view_stats'):
        return redirect(url_for('routes_general.home'))

    try:
        statistics = return_stat_file_dict(STATS_CSV)
    except IOError:
        statistics = {}
    return render_template('admin/statistics.html',
                           statistics=statistics)


@blueprint.route('/admin/upgrade_status', methods=('GET', 'POST'))
@flask_login.login_required
def admin_upgrade_status():
    """ Return the last 30 lines of the upgrade log """
    if os.path.isfile(UPGRADE_LOG_FILE):
        command = 'tail -n 40 {log}'.format(log=UPGRADE_LOG_FILE)
        log = subprocess.Popen(
            command, stdout=subprocess.PIPE, shell=True)
        (log_output, _) = log.communicate()
        log.wait()
        log_output = log_output.decode("utf-8")
    else:
        log_output = 'Upgrade log not found. If an upgrade was just ' \
                     'initialized, please wait...'
    response = make_response(log_output)
    response.headers["content-type"] = "text/plain"
    return response


@blueprint.route('/admin/upgrade', methods=('GET', 'POST'))
@flask_login.login_required
def admin_upgrade():
    """ Display any available upgrades and option to upgrade """
    if not utils_general.user_has_permission('edit_settings'):
        return redirect(url_for('routes_general.home'))

    if not internet():
        flash(gettext("Upgrade functionality is disabled because an internet "
                      "connection was unable to be detected"),
              "error")
        return render_template('admin/upgrade.html',
                               is_internet=False)

    # Read from the upgrade status file created by the upgrade script
    # to indicate if the upgrade is running.
    try:
        with open(UPGRADE_INIT_FILE) as f:
            upgrade = int(f.read(1))
    except IOError:
        try:
            with open(UPGRADE_INIT_FILE, 'w') as f:
                f.write('0')
        finally:
            upgrade = 0

    if upgrade:
        if upgrade == 2:
            flash(gettext("There was an error encountered during the upgrade"
                          " process. Check the upgrade log for details."),
                  "error")
        return render_template('admin/upgrade.html',
                               upgrade=upgrade)

    form_backup = forms_misc.Backup()
    form_upgrade = forms_misc.Upgrade()

    is_internet = True
    upgrade_available = False

    # Check for any new Mycodo releases on github
    releases = []
    try:
        maj_version = int(MYCODO_VERSION.split('.')[0])
        releases = github_releases(maj_version)
    except Exception as err:
        flash(gettext("Could not determine local mycodo version or "
                      "online release versions: {err}".format(err=err)),
              "error")
    if len(releases):
        latest_release = releases[0]
        current_releases = []
        releases_behind = None
        for index, each_release in enumerate(releases):
            if parse_version(each_release) >= parse_version(MYCODO_VERSION):
                current_releases.append(each_release)
            if parse_version(each_release) == parse_version(MYCODO_VERSION):
                releases_behind = index
        if parse_version(releases[0]) > parse_version(MYCODO_VERSION):
            upgrade_available = True
    else:
        current_releases = []
        latest_release = '0.0.0'
        releases_behind = 0

    # Update database to reflect the current upgrade status
    mod_misc = Misc.query.first()
    if mod_misc.mycodo_upgrade_available != upgrade_available:
        mod_misc.mycodo_upgrade_available = upgrade_available
        db.session.commit()

    if request.method == 'POST':
        if (form_upgrade.upgrade.data and
                (upgrade_available or FORCE_UPGRADE_MASTER)):
            backup_size, free_before, free_after = can_perform_backup()
            if free_after / 1000000 < 50:
                flash(
                    "A backup must be performed during an upgrade and there "
                    "is not enough free space to perform a backup. A backup "
                    "requires {size_bu:.1f} MB but there is only "
                    "{size_free:.1f} MB available, which would leave "
                    "{size_after:.1f} MB after the backup. If the free space "
                    "after a backup is less than 50 MB, the backup cannot "
                    "proceed. Free up space by deleting current "
                    "backups.".format(size_bu=backup_size / 1000000,
                                      size_free=free_before / 1000000,
                                      size_after=free_after / 1000000),
                    'error')
            elif FORCE_UPGRADE_MASTER:
                cmd = "{pth}/mycodo/scripts/mycodo_wrapper upgrade-master" \
                      " | ts '[%Y-%m-%d %H:%M:%S]'" \
                      " >> {log} 2>&1".format(pth=INSTALL_DIRECTORY,
                                              log=UPGRADE_LOG_FILE)
                subprocess.Popen(cmd, shell=True)

                upgrade = 1
                flash(gettext("The upgrade (from master branch) has started"), "success")
            else:
                cmd = "{pth}/mycodo/scripts/mycodo_wrapper upgrade" \
                      " | ts '[%Y-%m-%d %H:%M:%S]'" \
                      " >> {log} 2>&1".format(pth=INSTALL_DIRECTORY,
                                              log=UPGRADE_LOG_FILE)
                subprocess.Popen(cmd, shell=True)

                upgrade = 1
                mod_misc = Misc.query.first()
                mod_misc.mycodo_upgrade_available = False
                db.session.commit()
                flash(gettext("The upgrade has started"), "success")
        else:
            flash(gettext("You cannot upgrade if an upgrade is not available"),
                  "error")

    return render_template('admin/upgrade.html',
                           force_upgrade_master=FORCE_UPGRADE_MASTER,
                           form_backup=form_backup,
                           form_upgrade=form_upgrade,
                           current_release=MYCODO_VERSION,
                           current_releases=current_releases,
                           latest_release=latest_release,
                           releases_behind=releases_behind,
                           upgrade_available=upgrade_available,
                           upgrade=upgrade,
                           is_internet=is_internet)
