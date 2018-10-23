# coding=utf-8
#
# controller_math.py - Math controller that performs math on other controllers
#                      to create new values
#
#  Copyright (C) 2017  Kyle T. Gabriel
#
#  This file is part of Mycodo
#
#  Mycodo is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Mycodo is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Mycodo. If not, see <http://www.gnu.org/licenses/>.
#
#  Contact at kylegabriel.com
#

import logging
import threading
import time
import timeit
from statistics import median

import urllib3

import mycodo.utils.psypy as SI
from mycodo.databases.models import Input
from mycodo.databases.models import Math
from mycodo.databases.models import Misc
from mycodo.databases.models import SMTP
from mycodo.inputs.sensorutils import convert_units
from mycodo.mycodo_client import DaemonControl
from mycodo.utils.database import db_retrieve_table_daemon
from mycodo.utils.influx import add_measure_influxdb
from mycodo.utils.influx import check_if_adc_measurement
from mycodo.utils.influx import read_last_influxdb
from mycodo.utils.influx import read_past_influxdb


class Measurement:
    """
    Class for holding all measurement values in a dictionary.
    The dictionary is formatted in the following way:

    {'measurement type':measurement value}

    Measurement type: The environmental or physical condition
    being measured, such as 'temperature', or 'pressure'.

    Measurement value: The actual measurement of the condition.
    """

    def __init__(self, raw_data):
        self.rawData = raw_data

    @property
    def values(self):
        return self.rawData


class MathController(threading.Thread):
    """
    Class to operate discrete PID controller

    """
    def __init__(self, ready, math_id):
        threading.Thread.__init__(self)

        self.logger = logging.getLogger("mycodo.math_{id}".format(id=math_id.split('-')[0]))

        try:
            self.measurements = None
            self.running = False
            self.thread_startup_timer = timeit.default_timer()
            self.thread_shutdown_timer = 0
            self.ready = ready
            self.pause_loop = False
            self.verify_pause_loop = True
            self.control = DaemonControl()

            self.sample_rate = db_retrieve_table_daemon(
                Misc, entry='first').sample_rate_controller_math

            smtp = db_retrieve_table_daemon(SMTP, entry='first')
            self.smtp_max_count = smtp.hourly_max
            self.email_count = 0
            self.allowed_to_send_notice = True

            self.math_id = math_id
            math = db_retrieve_table_daemon(Math, unique_id=self.math_id)

            # General variables
            self.unique_id = math.unique_id
            self.name = math.name
            self.math_type = math.math_type
            self.is_activated = math.is_activated
            self.period = math.period
            self.max_measure_age = math.max_measure_age
            self.measure = math.measure

            # Inputs to calculate with
            self.inputs = math.inputs

            # Difference variables
            self.difference_reverse_order = math.difference_reverse_order
            self.difference_absolute = math.difference_absolute

            # Equation variables
            self.equation_input = math.equation_input
            self.equation = math.equation

            # Verification variables
            self.max_difference = math.max_difference

            # Humidity variables
            self.dry_bulb_t_id = math.dry_bulb_t_id
            self.dry_bulb_t_measure = math.dry_bulb_t_measure
            self.wet_bulb_t_id = math.wet_bulb_t_id
            self.wet_bulb_t_measure = math.wet_bulb_t_measure
            self.pressure_pa_id = math.pressure_pa_id
            self.pressure_pa_measure = math.pressure_pa_measure

            self.timer = time.time() + self.period
        except Exception as except_msg:
            self.logger.exception("Init Error: {err}".format(
                err=except_msg))

    def run(self):
        try:
            self.running = True
            self.logger.info("Activated in {:.1f} ms".format(
                (timeit.default_timer() - self.thread_startup_timer) * 1000))
            self.ready.set()

            while self.running:
                # Pause loop to modify conditional statements.
                # Prevents execution of conditional while variables are
                # being modified.
                if self.pause_loop:
                    self.verify_pause_loop = True
                    while self.pause_loop:
                        time.sleep(0.1)

                if self.is_activated and time.time() > self.timer:

                    self.calculate_math()

                    # Ensure the next timer ends in the future
                    while time.time() > self.timer:
                        self.timer += self.period

                time.sleep(self.sample_rate)

            self.running = False
            self.logger.info("Deactivated in {:.1f} ms".format(
                (timeit.default_timer() - self.thread_shutdown_timer) * 1000))
        except Exception as except_msg:
            self.logger.exception("Run Error: {err}".format(
                err=except_msg))

    def calculate_math(self):
        if self.math_type == 'average':
            success, measure = self.get_measurements_from_str(self.inputs)
            if success:
                measure_dict = {
                    self.measure: float('{0:.4f}'.format(
                        sum(measure) / float(len(measure))))
                }
                self.measurements = Measurement(measure_dict)
                add_measure_influxdb(self.unique_id, self.measurements)
            elif measure:
                self.logger.error(measure)
            else:
                self.error_not_within_max_age()

        elif self.math_type == 'average_single':
            device_id = self.inputs.split(',')[0]
            measurement = self.inputs.split(',')[1]
            try:
                last_measurements = read_past_influxdb(
                    device_id,
                    measurement,
                    self.max_measure_age)

                if last_measurements:
                    measure_list = []
                    for each_set in last_measurements:
                        if len(each_set) == 2:
                            measure_list.append(each_set[1])
                    average = sum(measure_list) / float(len(measure_list))

                    measure_dict = {
                        self.measure: float('{0:.4f}'.format(average))
                    }
                    self.measurements = Measurement(measure_dict)
                    add_measure_influxdb(self.unique_id, self.measurements)
                else:
                    self.error_not_within_max_age()
            except Exception as msg:
                self.logger.error("average_single Error: {err}".format(err=msg))

        elif self.math_type == 'difference':
            success, measure = self.get_measurements_from_str(self.inputs)
            if success:
                if self.difference_reverse_order:
                    difference = measure[1] - measure[0]
                else:
                    difference = measure[0] - measure[1]
                if self.difference_absolute:
                    difference = abs(difference)
                measure_dict = {
                    self.measure: float('{0:.4f}'.format(difference))
                }
                self.measurements = Measurement(measure_dict)
                add_measure_influxdb(self.unique_id, self.measurements)
            elif measure:
                self.logger.error(measure)
            else:
                self.error_not_within_max_age()

        elif self.math_type == 'equation':
            success, measure = self.get_measurements_from_str(self.equation_input)
            if success:
                replaced_str = self.equation.replace('x', str(measure[0]))
                equation_output = eval(replaced_str)
                measure_dict = {
                    self.measure: float('{0:.4f}'.format(equation_output))
                }
                self.measurements = Measurement(measure_dict)
                add_measure_influxdb(self.unique_id, self.measurements)
            elif measure:
                self.logger.error(measure)
            else:
                self.error_not_within_max_age()

        elif self.math_type == 'median':
            success, measure = self.get_measurements_from_str(self.inputs)
            if success:
                measure_dict = {
                    self.measure: float('{0:.4f}'.format(median(measure)))
                }
                self.measurements = Measurement(measure_dict)
                add_measure_influxdb(self.unique_id, self.measurements)
            elif measure:
                self.logger.error(measure)
            else:
                self.error_not_within_max_age()

        elif self.math_type == 'maximum':
            success, measure = self.get_measurements_from_str(self.inputs)
            if success:
                measure_dict = {
                    self.measure: float('{0:.4f}'.format(max(measure)))
                }
                self.measurements = Measurement(measure_dict)
                add_measure_influxdb(self.unique_id, self.measurements)
            elif measure:
                self.logger.error(measure)
            else:
                self.error_not_within_max_age()

        elif self.math_type == 'minimum':
            success, measure = self.get_measurements_from_str(self.inputs)
            if success:
                measure_dict = {
                    self.measure: float('{0:.4f}'.format(min(measure)))
                }
                self.measurements = Measurement(measure_dict)
                add_measure_influxdb(self.unique_id, self.measurements)
            elif measure:
                self.logger.error(measure)
            else:
                self.error_not_within_max_age()

        elif self.math_type == 'verification':
            success, measure = self.get_measurements_from_str(self.inputs)
            if (success and
                    max(measure) - min(measure) <
                    self.max_difference):
                measure_dict = {
                    self.measure: float('{0:.4f}'.format(
                        sum(measure) / float(len(measure))))
                }
                self.measurements = Measurement(measure_dict)
                add_measure_influxdb(self.unique_id, self.measurements)
            elif measure:
                self.logger.error(measure)
            else:
                self.error_not_within_max_age()

        elif self.math_type == 'humidity':
            pressure_pa = 101325

            if self.pressure_pa_id and self.pressure_pa_measure:
                success_pa, pressure = self.get_measurements_from_id(
                    self.pressure_pa_id, self.pressure_pa_measure)
                if success_pa:
                    pressure_pa = int(pressure[1])
                    # Pressure must be in Pa, convert if not
                    pressure_conf = db_retrieve_table_daemon(
                        Input, unique_id=self.pressure_pa_id)
                    for each_measure in pressure_conf.convert_to_unit.split(';'):
                        measure = each_measure.split(',')[0]
                        unit = each_measure.split(',')[1]
                        if measure == 'pressure' and unit != 'Pa':
                            pressure_pa = convert_units(
                                'pressure', unit, 'Pa',
                                pressure_pa)

            success_dbt, dry_bulb_t = self.get_measurements_from_id(
                self.dry_bulb_t_id, self.dry_bulb_t_measure)
            success_wbt, wet_bulb_t = self.get_measurements_from_id(
                self.wet_bulb_t_id, self.wet_bulb_t_measure)

            if success_dbt and success_wbt:
                dbt_kelvin = float(dry_bulb_t[1])
                wbt_kelvin = float(wet_bulb_t[1])

                # Temperatures must be in Kelvin, convert if not
                dry_bulb_conf = db_retrieve_table_daemon(
                    Input, unique_id=self.dry_bulb_t_id)
                for each_measure in dry_bulb_conf.convert_to_unit.split(';'):
                    measure = each_measure.split(',')[0]
                    unit = each_measure.split(',')[1]
                    if measure == 'temperature' and unit != 'K':
                        dbt_kelvin = convert_units(
                            'temperature', unit, 'temperature,K',
                            dbt_kelvin)

                wet_bulb_conf = db_retrieve_table_daemon(
                    Input, unique_id=self.wet_bulb_t_id)
                for each_measure in wet_bulb_conf.convert_to_unit.split(';'):
                    measure = each_measure.split(',')[0]
                    unit = each_measure.split(',')[1]
                    if measure == 'temperature' and unit != 'K':
                        wbt_kelvin = convert_units(
                            'temperature', unit, 'temperature,K',
                            wbt_kelvin)

                # Convert temperatures to Kelvin (already done above)
                # dbt_kelvin = celsius_to_kelvin(dry_bulb_t_c)
                # wbt_kelvin = celsius_to_kelvin(wet_bulb_t_c)
                psypi = None

                try:
                    psypi = SI.state(
                        "DBT", dbt_kelvin, "WBT", wbt_kelvin, pressure_pa)
                except TypeError as err:
                    self.logger.error("TypeError: {msg}".format(msg=err))

                if psypi:
                    percent_relative_humidity = psypi[2] * 100

                    # Ensure percent humidity stays within 0 - 100 % range
                    if percent_relative_humidity > 100:
                        percent_relative_humidity = 100
                    elif percent_relative_humidity < 0:
                        percent_relative_humidity = 0

                    # Dry bulb temperature: psypi[0])
                    # Wet bulb temperature: psypi[5])

                    measure_dict = dict(
                        specific_enthalpy=float('{0:.5f}'.format(psypi[1])),
                        humidity=float('{0:.5f}'.format(percent_relative_humidity)),
                        specific_volume=float('{0:.5f}'.format(psypi[3])),
                        humidity_ratio=float('{0:.5f}'.format(psypi[4])))
                    self.measurements = Measurement(measure_dict)
                    add_measure_influxdb(self.unique_id, self.measurements)
            else:
                self.error_not_within_max_age()

    def error_not_within_max_age(self):
        self.logger.error(
            "One or more inputs were not within the Max Age that has been "
            "set. Ensure all Inputs are operating properly.")

    def get_measurements_from_str(self, inputs):
        try:
            measurements = []
            inputs_list = inputs.split(';')
            for each_input_set in inputs_list:
                input_id = each_input_set.split(',')[0]
                input_measure = each_input_set.split(',')[1]

                # Handle ADC request
                input_measure = check_if_adc_measurement(input_measure)

                last_measurement = read_last_influxdb(
                    input_id,
                    input_measure,
                    self.max_measure_age)
                if not last_measurement:
                    return False, None
                else:
                    measurements.append(last_measurement[1])
            return True, measurements
        except urllib3.exceptions.NewConnectionError:
            return False, "Influxdb: urllib3.exceptions.NewConnectionError"
        except Exception as msg:
            return False, "Influxdb: Unknown Error: {err}".format(err=msg)

    def get_measurements_from_id(self, measure_id, measure_name):
        measurement = read_last_influxdb(
            measure_id,
            measure_name,
            self.max_measure_age)
        if not measurement:
            return False, None
        return True, measurement

    def is_running(self):
        return self.running

    def stop_controller(self):
        self.thread_shutdown_timer = timeit.default_timer()
        self.running = False
