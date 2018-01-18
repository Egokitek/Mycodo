# -*- coding: utf-8 -*-
#
# forms_graph.py - Graph Flask Forms
#

from flask_babel import lazy_gettext
from flask_wtf import FlaskForm
from wtforms import BooleanField
from wtforms import DecimalField
from wtforms import IntegerField
from wtforms import SelectField
from wtforms import SelectMultipleField
from wtforms import StringField
from wtforms import SubmitField
from wtforms import validators
from wtforms import widgets
from wtforms.validators import DataRequired


class DashboardBase(FlaskForm):
    dashboard_id = IntegerField('Dash Object ID', widget=widgets.HiddenInput())
    dashboard_type = SelectField(
        lazy_gettext('Dashboard Object Type'),
        choices=[
            ('', lazy_gettext('Select a Dashboard Object')),
            ('graph', lazy_gettext('Graph')),
            ('gauge', lazy_gettext('Gauge')),
            ('camera', lazy_gettext('Camera')),
        ],
        validators=[DataRequired()]
    )
    name = StringField(
        lazy_gettext('Name'),
        validators=[DataRequired()]
    )
    create = SubmitField(lazy_gettext('Create'))
    modify = SubmitField(lazy_gettext('Save'))
    delete = SubmitField(lazy_gettext('Delete'))
    order_up = SubmitField(lazy_gettext('Up'))
    order_down = SubmitField(lazy_gettext('Down'))


class DashboardGraph(FlaskForm):
    math_ids = SelectMultipleField(lazy_gettext('Maths'))
    pid_ids = SelectMultipleField(lazy_gettext('PIDs'))
    relay_ids = SelectMultipleField(lazy_gettext('Outputs'))
    sensor_ids = SelectMultipleField(lazy_gettext('Inputs'))
    width = IntegerField(
        lazy_gettext('Width'),
        validators=[validators.NumberRange(
            min=1,
            max=12
        )]
    )
    height = IntegerField(
        lazy_gettext('Height (pixels)'),
        validators=[validators.NumberRange(
            min=100,
            max=10000
        )]
    )
    xaxis_duration = DecimalField(
        lazy_gettext('X-Axis (minutes)'),
        validators=[validators.NumberRange(
            min=0.1,
            message=lazy_gettext("Number of minutes to display of past "
                                 "measurements.")
        )]
    )
    refresh_duration = DecimalField(
        lazy_gettext('Period (seconds)'),
        validators=[validators.NumberRange(
            min=0.2,
            message=lazy_gettext("Number of seconds to wait between acquiring"
                                 " any new measurements.")
        )]
    )
    enable_auto_refresh = BooleanField(lazy_gettext('Enable Auto Refresh'))
    enable_xaxis_reset = BooleanField(lazy_gettext('Enable X-Axis Reset'))
    enable_title = BooleanField(lazy_gettext('Enable Title'))
    enable_navbar = BooleanField(lazy_gettext('Enable Navbar'))
    enable_export = BooleanField(lazy_gettext('Enable Export'))
    enable_range = BooleanField(lazy_gettext('Enable Range Selector'))
    enable_manual_y_axis = BooleanField(lazy_gettext('Manual Y-Axis Min/Max'))
    y_axis_min = DecimalField(lazy_gettext('Y-Axis Minimum'))
    y_axis_max = DecimalField(lazy_gettext('Y-Axis Maximum'))
    use_custom_colors = BooleanField(lazy_gettext('Enable Custom Colors'))


class DashboardGauge(FlaskForm):
    sensor_ids = SelectMultipleField(lazy_gettext('Measurement'))
    width = IntegerField(
        lazy_gettext('Width'),
        validators=[validators.NumberRange(
            min=1,
            max=12
        )]
    )
    height = IntegerField(
        lazy_gettext('Height (pixels)'),
        validators=[validators.NumberRange(
            min=100,
            max=10000
        )]
    )
    y_axis_min = DecimalField(lazy_gettext('Gauge Min'))
    y_axis_max = DecimalField(lazy_gettext('Gauge Max'))
    max_measure_age = DecimalField(lazy_gettext('Max Age (seconds)'))
    refresh_duration = DecimalField(
        lazy_gettext('Refresh (seconds)'),
        validators=[validators.NumberRange(
            min=1,
            message=lazy_gettext("Number of seconds to wait between acquiring"
                                 " any new measurements.")
        )]
    )


class DashboardCamera(FlaskForm):
    camera_id = StringField(lazy_gettext('Camera'))
    width = IntegerField(
        lazy_gettext('Width'),
        validators=[validators.NumberRange(
            min=1,
            max=12
        )]
    )
    height = IntegerField(
        lazy_gettext('Height (pixels)'),
        validators=[validators.NumberRange(
            min=100,
            max=10000
        )]
    )
    refresh_duration = IntegerField(
        lazy_gettext('Refresh (seconds)'),
        validators=[validators.NumberRange(
            min=1,
            message=lazy_gettext("Number of seconds to wait between acquiring"
                                 " any new measurements.")
        )]
    )
    camera_image_type = StringField(lazy_gettext('Image Display Type'))
    camera_max_age = IntegerField(lazy_gettext('Max Age (seconds)'))
