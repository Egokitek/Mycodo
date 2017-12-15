# -*- coding: utf-8 -*-
import logging
import sqlalchemy

from flask import flash
from flask import url_for

from mycodo.mycodo_flask.extensions import db
from flask_babel import gettext

from mycodo.databases.models import Conditional
from mycodo.databases.models import ConditionalActions
from mycodo.databases.models import DisplayOrder
from mycodo.databases.models import Input
from mycodo.databases.models import Math
from mycodo.utils.system_pi import csv_to_list_of_int
from mycodo.utils.system_pi import list_to_csv

from mycodo.mycodo_flask.utils.utils_general import add_display_order
from mycodo.mycodo_flask.utils.utils_general import controller_activate_deactivate
from mycodo.mycodo_flask.utils.utils_general import delete_entry_with_id
from mycodo.mycodo_flask.utils.utils_general import flash_form_errors
from mycodo.mycodo_flask.utils.utils_general import flash_success_errors
from mycodo.mycodo_flask.utils.utils_general import reorder

logger = logging.getLogger(__name__)


#
# Math manipulation
#

def math_add(form_add_math):
    action = u'{action} {controller}'.format(
        action=gettext(u"Add"),
        controller=gettext(u"Math"))
    error = []

    if form_add_math.validate():
        new_math = Math()
        new_math.name = 'Math {name}'.format(name=form_add_math.math_type.data)
        new_math.math_type = form_add_math.math_type.data

        if new_math.math_type == 'humidity':
            new_math.measure = 'humidity,humidity_ratio,specific_enthalpy,specific_volume'
            new_math.measure_units = '%'

        try:
            new_math.save()

            display_order = csv_to_list_of_int(
                DisplayOrder.query.first().math)
            DisplayOrder.query.first().math = add_display_order(
                display_order, new_math.id)
            db.session.commit()

            flash(gettext(
                u"%(type)s Math with ID %(id)s (%(uuid)s) successfully added",
                type=form_add_math.math_type.data,
                id=new_math.id,
                uuid=new_math.unique_id),
                  "success")
        except sqlalchemy.exc.OperationalError as except_msg:
            error.append(except_msg)
        except sqlalchemy.exc.IntegrityError as except_msg:
            error.append(except_msg)
        flash_success_errors(error, action, url_for('page_routes.page_input'))
    else:
        flash_form_errors(form_add_math)


def math_mod(form_mod_math, form_mod_type=None):
    action = u'{action} {controller}'.format(
        action=gettext(u"Modify"),
        controller=gettext(u"Math"))
    error = []

    if not form_mod_math.validate():
        error.append(gettext("Error in form field(s)"))
        flash_form_errors(form_mod_math)

    try:
        mod_math = Math.query.filter(
            Math.id == form_mod_math.math_id.data).first()

        if mod_math.is_activated:
            error.append(gettext(
                u"Deactivate Math controller before modifying its "
                u"settings"))

        if not form_mod_type:
            raise ValueError('form_mod_type is not defined')
        if not form_mod_type.validate():
            error.append(gettext("Error in form field(s)"))
            flash_form_errors(form_mod_type)

        mod_math.name = form_mod_math.name.data
        mod_math.period = form_mod_math.period.data
        mod_math.max_measure_age = form_mod_math.max_measure_age.data

        if mod_math.math_type in ['average',
                                  'median',
                                  'maximum',
                                  'minimum',
                                  'verification']:
            if len(form_mod_type.inputs.data) < 2:
                error.append("At least two Inputs must be selected")
            if form_mod_type.inputs.data:
                inputs_joined = ";".join(form_mod_type.inputs.data)
                mod_math.inputs = inputs_joined
            else:
                mod_math.inputs = ''
            mod_math.measure = form_mod_type.measure.data
            mod_math.measure_units = form_mod_type.measure_units.data

        elif mod_math.math_type == 'humidity':
            mod_math.dry_bulb_t_id = form_mod_type.dry_bulb_temperature.data.split(',')[0]
            dbt_input = Input.query.filter(
                Input.unique_id == mod_math.dry_bulb_t_id).first()
            dbt_math = Input.query.filter(
                Math.unique_id == mod_math.dry_bulb_t_id).first()
            if (not dbt_input and not dbt_math) and 'temperature' not in dbt_input.measurements:
                error.append("Invalid dry-bulb temperature selection")
            mod_math.dry_bulb_t_measure = form_mod_type.dry_bulb_temperature.data.split(',')[1]

            mod_math.wet_bulb_t_id = form_mod_type.wet_bulb_temperature.data.split(',')[0]
            wbt_input = Input.query.filter(
                Input.unique_id == mod_math.wet_bulb_t_id).first()
            wbt_math = Input.query.filter(
                Math.unique_id == mod_math.wet_bulb_t_id).first()
            if (not wbt_input and not wbt_math) and 'temperature' not in wbt_input.measurements:
                error.append("Invalid wet-bulb temperature selection")
            mod_math.wet_bulb_t_measure = form_mod_type.wet_bulb_temperature.data.split(',')[1]

            if form_mod_type.pressure.data:
                mod_math.pressure_pa_id = form_mod_type.pressure.data.split(',')[0]
                pressure_input = Input.query.filter(
                    Input.unique_id == mod_math.pressure_pa_id).first()
                if not pressure_input or 'pressure' not in pressure_input.measurements:
                    error.append("Invalid pressure selection")
                mod_math.pressure_pa_measure = form_mod_type.pressure.data.split(',')[1]
            else:
                mod_math.pressure_pa_id = None
                mod_math.pressure_pa_measure = None

        elif mod_math.math_type == 'verification':
            mod_math.max_difference = form_mod_type.max_difference.data
            mod_math.measure = form_mod_type.measure.data
            mod_math.measure_units = form_mod_type.measure_units.data

        if not error:
            db.session.commit()
    except Exception as except_msg:
        error.append(except_msg)

    flash_success_errors(error, action, url_for('page_routes.page_input'))


def math_del(form_mod_math):
    action = u'{action} {controller}'.format(
        action=gettext(u"Delete"),
        controller=gettext(u"Math"))
    error = []

    try:
        math = Math.query.filter(
            Math.id == form_mod_math.math_id.data).first()
        if math.is_activated:
            controller_activate_deactivate(
                'deactivate',
                'Math',
                form_mod_math.math_id.data)

        # Delete any conditionals associated with the controller
        conditionals = Conditional.query.filter(
            Conditional.math_id == form_mod_math.math_id.data).all()
        for each_cond in conditionals:
            conditional_actions = ConditionalActions.query.filter(
                ConditionalActions.conditional_id == each_cond.id).all()
            for each_cond_action in conditional_actions:
                db.session.delete(each_cond_action)
            db.session.delete(each_cond)
        db.session.commit()

        delete_entry_with_id(Math, form_mod_math.math_id.data)
        try:
            display_order = csv_to_list_of_int(DisplayOrder.query.first().math)
            display_order.remove(int(form_mod_math.math_id.data))
            DisplayOrder.query.first().math = list_to_csv(display_order)
        except Exception:  # id not in list
            pass
        db.session.commit()
    except Exception as except_msg:
        error.append(except_msg)

    flash_success_errors(error, action, url_for('page_routes.page_input'))


def math_reorder(math_id, display_order, direction):
    action = u'{action} {controller}'.format(
        action=gettext(u"Reorder"),
        controller=gettext(u"Math"))
    error = []
    try:
        status, reord_list = reorder(display_order,
                                     math_id,
                                     direction)
        if status == 'success':
            DisplayOrder.query.first().math = ','.join(map(str, reord_list))
            db.session.commit()
        elif status == 'error':
            error.append(reord_list)
    except Exception as except_msg:
        error.append(except_msg)
    flash_success_errors(error, action, url_for('page_routes.page_input'))


def math_activate(form_mod_math):
    controller_activate_deactivate('activate',
                                   'Math',
                                   form_mod_math.math_id.data)


def math_deactivate(form_mod_math):
    controller_activate_deactivate('deactivate',
                                   'Math',
                                   form_mod_math.math_id.data)
