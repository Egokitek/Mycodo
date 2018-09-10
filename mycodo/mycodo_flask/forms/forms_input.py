# -*- coding: utf-8 -*-
#
# forms_input.py - Input Flask Forms
#
import logging

from flask_babel import lazy_gettext
from flask_wtf import FlaskForm
from wtforms import BooleanField
from wtforms import DecimalField
from wtforms import IntegerField
from wtforms import SelectField
from wtforms import StringField
from wtforms import SubmitField
from wtforms import validators
from wtforms import widgets
from wtforms.validators import DataRequired

from mycodo.config_translations import TOOLTIPS_INPUT
from mycodo.utils.inputs import parse_input_information

logger = logging.getLogger("mycodo.forms_input")


class InputAdd(FlaskForm):
    choices_inputs = [('', lazy_gettext('Select Input to Add'))]

    dict_inputs = parse_input_information()

    # Sort dictionary entries by input_manufacturer, then common_name_input
    # Results in list of sorted dictionary keys
    list_tuples_sorted = sorted(dict_inputs.items(), key=lambda x: (x[1]['input_manufacturer'], x[1]['common_name_input']))
    list_inputs_sorted = []
    for each_input in list_tuples_sorted:
        list_inputs_sorted.append(each_input[0])

    for each_input in list_inputs_sorted:
        if 'interfaces' not in dict_inputs[each_input]:
            choices_inputs.append(
                ('{inp},'.format(inp=each_input),
                 '{manuf}: {name}: {meas}'.format(
                     manuf=dict_inputs[each_input]['input_manufacturer'],
                     name=dict_inputs[each_input]['common_name_input'],
                     meas=dict_inputs[each_input]['common_name_measurements'])))
        else:
            for each_interface in dict_inputs[each_input]['interfaces']:
                choices_inputs.append(
                    ('{inp},{int}'.format(inp=each_input, int=each_interface),
                     '{manuf}: {name}: {meas} ({int})'.format(
                        manuf=dict_inputs[each_input]['input_manufacturer'],
                        name=dict_inputs[each_input]['common_name_input'],
                        meas=dict_inputs[each_input]['common_name_measurements'],
                        int=each_interface)))

    input_type = SelectField(
        choices=choices_inputs,
        validators=[DataRequired()]
    )
    input_add = SubmitField(lazy_gettext('Add Input'))


class InputMod(FlaskForm):
    input_id = StringField('Input ID', widget=widgets.HiddenInput())
    name = StringField(
        lazy_gettext('Name'),
        validators=[DataRequired()]
    )
    period = DecimalField(
        TOOLTIPS_INPUT['period']['title'],
        validators=[DataRequired(),
                    validators.NumberRange(
                        min=5.0,
                        max=86400.0
                    )]
    )
    location = StringField(lazy_gettext('Location'))  # Access input (GPIO, I2C address, etc.)
    uart_location = StringField(lazy_gettext('UART Device'))  # UART device location type
    i2c_location = StringField(lazy_gettext('I<sup>2</sup>C Address'))  # I2C device location type
    gpio_location = IntegerField(lazy_gettext('GPIO Pin'))  # GPIO device location type

    i2c_bus = IntegerField(lazy_gettext('I<sup>2</sup>C Bus'))
    baud_rate = IntegerField(lazy_gettext('Baud Rate'))
    power_output_id = StringField(lazy_gettext('Power Output'))  # For powering input
    calibrate_sensor_measure = StringField(lazy_gettext('Calibration Measurement'))
    resolution = IntegerField(lazy_gettext('Resolution'))
    resolution_2 = IntegerField(lazy_gettext('Resolution'))
    sensitivity = IntegerField(lazy_gettext('Sensitivity'))
    convert_to_unit = StringField(lazy_gettext('Unit'))
    selected_measurement_unit = StringField(lazy_gettext('Unit Measurement'))

    # Server options
    host = StringField(lazy_gettext('Host'))
    port = IntegerField(TOOLTIPS_INPUT['port']['title'])
    times_check = IntegerField(TOOLTIPS_INPUT['times_check']['title'])
    deadline = IntegerField(TOOLTIPS_INPUT['deadline']['title'])

    # Linux Command
    cmd_command = StringField(TOOLTIPS_INPUT['cmd_command']['title'])

    # MAX chip options
    thermocouple_type = StringField(TOOLTIPS_INPUT['thermocouple_type']['title'])
    ref_ohm = IntegerField(TOOLTIPS_INPUT['ref_ohm']['title'])

    # SPI Communication
    pin_clock = IntegerField(TOOLTIPS_INPUT['pin_clock']['title'])
    pin_cs = IntegerField(TOOLTIPS_INPUT['pin_cs']['title'])
    pin_mosi = IntegerField(TOOLTIPS_INPUT['pin_mosi']['title'])
    pin_miso = IntegerField(TOOLTIPS_INPUT['pin_miso']['title'])

    # Bluetooth Communication
    bt_adapter = StringField(lazy_gettext('BT Adapter'))

    # ADC
    adc_channel = IntegerField(TOOLTIPS_INPUT['adc_channel']['title'])
    adc_gain = IntegerField(TOOLTIPS_INPUT['adc_gain']['title'])
    adc_resolution = IntegerField(TOOLTIPS_INPUT['adc_resolution']['title'])
    adc_volts_min = DecimalField(TOOLTIPS_INPUT['adc_volts_min']['title'])
    adc_volts_max = DecimalField(TOOLTIPS_INPUT['adc_volts_max']['title'])
    adc_units_min = DecimalField(TOOLTIPS_INPUT['adc_units_min']['title'])
    adc_units_max = DecimalField(TOOLTIPS_INPUT['adc_units_max']['title'])
    adc_inverse_unit_scale = BooleanField(TOOLTIPS_INPUT['adc_inverse_unit_scale']['title'])

    switch_edge = StringField(lazy_gettext('Edge'))
    switch_bounce_time = IntegerField(lazy_gettext('Bounce Time (ms)'))
    switch_reset_period = IntegerField(lazy_gettext('Reset Period'))

    # Pre-Output
    pre_output_id = StringField(TOOLTIPS_INPUT['pre_output_id']['title'])
    pre_output_duration = DecimalField(
        TOOLTIPS_INPUT['pre_output_duration']['title'],
        validators=[validators.NumberRange(
            min=0,
            max=86400
        )]
    )
    pre_output_during_measure = BooleanField(TOOLTIPS_INPUT['pre_output_during_measure']['title'])

    # RPM/Signal
    weighting = DecimalField(TOOLTIPS_INPUT['weighting']['title'])
    rpm_pulses_per_rev = DecimalField(TOOLTIPS_INPUT['rpm_pulses_per_rev']['title'])
    sample_time = DecimalField(TOOLTIPS_INPUT['sample_time']['title'])

    # SHT options
    sht_voltage = StringField(TOOLTIPS_INPUT['sht_voltage']['title'])

    input_mod = SubmitField(lazy_gettext('Save'))
    input_delete = SubmitField(lazy_gettext('Delete'))
    input_activate = SubmitField(lazy_gettext('Activate'))
    input_deactivate = SubmitField(lazy_gettext('Deactivate'))
    input_order_up = SubmitField(lazy_gettext('Up'))
    input_order_down = SubmitField(lazy_gettext('Down'))
