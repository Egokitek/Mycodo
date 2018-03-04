# -*- coding: utf-8 -*-
#
# forms_misc.py - Miscellaneous Flask Forms
#

from flask_babel import lazy_gettext
from flask_wtf import FlaskForm
from wtforms import DecimalField
from wtforms import IntegerField
from wtforms import StringField
from wtforms import SubmitField
from wtforms import widgets


#
# Conditionals
#

class Conditional(FlaskForm):
    conditional_id = IntegerField('Conditional ID', widget=widgets.HiddenInput())
    conditional_type = StringField('Conditional Type', widget=widgets.HiddenInput())
    sensor_id = IntegerField('Output ID', widget=widgets.HiddenInput())
    quantity = IntegerField(lazy_gettext('Quantity'))
    name = StringField(lazy_gettext('Name'))

    # Output conditional options
    if_relay_id = StringField(lazy_gettext('If Output'))
    if_relay_state = StringField(lazy_gettext('State'))
    if_relay_duration = DecimalField(lazy_gettext('Duration (seconds)'))

    # Input conditional options
    if_sensor_measurement = StringField(lazy_gettext('If Measurement'))
    if_sensor_direction = StringField(lazy_gettext('State'))
    if_sensor_setpoint = DecimalField(lazy_gettext('Value'))
    if_sensor_period = DecimalField(lazy_gettext('Period (seconds)'))
    if_sensor_max_age = IntegerField(lazy_gettext('Max Age (seconds)'))

    # Edge detection
    if_sensor_edge_detected = StringField(lazy_gettext('Edge Detected'))

    add_cond = SubmitField(lazy_gettext('Add Conditional'))
    save_cond = SubmitField(lazy_gettext('Save'))
    delete_cond = SubmitField(lazy_gettext('Delete'))
    activate_cond = SubmitField(lazy_gettext('Activate'))
    deactivate_cond = SubmitField(lazy_gettext('Deactivate'))
    order_up_cond = SubmitField(lazy_gettext('Up'))
    order_down_cond = SubmitField(lazy_gettext('Down'))


class ConditionalActions(FlaskForm):
    conditional_id = IntegerField(
        'Conditional ID', widget=widgets.HiddenInput())
    conditional_action_id = IntegerField(
        'Conditional Action ID', widget=widgets.HiddenInput())
    do_action = StringField(lazy_gettext('Action to Perform'))
    do_action_string = StringField(lazy_gettext('Action String'))
    do_relay_id = IntegerField(lazy_gettext('Output'))
    do_relay_state = StringField(lazy_gettext('Output State'))
    do_relay_duration = DecimalField(lazy_gettext('Duration'))
    do_camera_id = IntegerField(lazy_gettext('Camera'))
    do_camera_duration = DecimalField(lazy_gettext('Duration'))
    do_lcd_id = IntegerField(lazy_gettext('LCD'))
    do_pid_id = IntegerField(lazy_gettext('PID'))
    add_action = SubmitField(lazy_gettext('Add Action'))
    save_action = SubmitField(lazy_gettext('Save'))
    delete_action = SubmitField(lazy_gettext('Delete'))
