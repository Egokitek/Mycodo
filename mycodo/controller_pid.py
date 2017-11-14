# coding=utf-8
#
# controller_pid.py - PID controller that manages discrete control of a
#                     regulation system of inputs, relays, and devices
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
# PID controller code was used from the source below, with modifications.
#
# <http://code.activestate.com/recipes/577231-discrete-pid-controller/>
# Copyright (c) 2010 cnr437@gmail.com
#
# Licensed under the MIT License <http://opensource.org/licenses/MIT>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import calendar
import logging
import datetime
import requests
import threading
import time as t
import timeit

from databases.models import Method
from databases.models import MethodData
from databases.models import PID
from databases.models import Relay
from databases.models import Input
from databases.utils import session_scope
from mycodo_client import DaemonControl
from utils.database import db_retrieve_table_daemon
from utils.influx import read_last_influxdb
from utils.influx import write_influxdb_value
from utils.method import calculate_method_setpoint

from config import SQL_DATABASE_MYCODO

MYCODO_DB_PATH = 'sqlite:///' + SQL_DATABASE_MYCODO


class PIDController(threading.Thread):
    """
    Class to operate discrete PID controller

    """
    def __init__(self, ready, pid_id):
        threading.Thread.__init__(self)

        self.logger = logging.getLogger("mycodo.pid_{id}".format(id=pid_id))

        self.running = False
        self.thread_startup_timer = timeit.default_timer()
        self.thread_shutdown_timer = 0
        self.ready = ready
        self.pid_id = pid_id
        self.pid_unique_id = db_retrieve_table_daemon(
            PID, device_id=self.pid_id).unique_id
        self.control = DaemonControl()

        self.control_variable = 0.0
        self.derivator = 0.0
        self.integrator = 0.0
        self.error = 0.0
        self.P_value = None
        self.I_value = None
        self.D_value = None
        self.set_point = 0.0
        self.lower_seconds_on = 0.0
        self.raise_seconds_on = 0.0
        self.lower_duty_cycle = 0.0
        self.raise_duty_cycle = 0.0
        self.last_time = None
        self.last_measurement = None
        self.last_measurement_success = False

        self.is_activated = None
        self.is_held = None
        self.is_paused = None
        self.measurement = None
        self.method_id = None
        self.direction = None
        self.raise_relay_id = None
        self.raise_min_duration = None
        self.raise_max_duration = None
        self.raise_min_off_duration = None
        self.lower_relay_id = None
        self.lower_min_duration = None
        self.lower_max_duration = None
        self.lower_min_off_duration = None
        self.Kp = None
        self.Ki = None
        self.Kd = None
        self.integrator_min = None
        self.integrator_max = None
        self.period = None
        self.max_measure_age = None
        self.default_set_point = None
        self.set_point = None

        self.input_unique_id = None
        self.input_duration = None

        self.raise_relay_type = None
        self.lower_relay_type = None

        self.initialize_values()

        self.timer = t.time() + self.period

        # Check if a method is set for this PID
        self.method_start_act = None
        if self.method_id:
            method = db_retrieve_table_daemon(Method, device_id=self.method_id)
            method_data = db_retrieve_table_daemon(MethodData)
            method_data = method_data.filter(MethodData.method_id == self.method_id)
            method_data_repeat = method_data.filter(MethodData.duration_sec == 0).first()
            pid = db_retrieve_table_daemon(PID, device_id=self.pid_id)
            self.method_type = method.method_type
            self.method_start_act = pid.method_start_time
            self.method_start_time = None
            self.method_end_time = None

            if self.method_type == 'Duration':
                if self.method_start_act == 'Ended':
                    # Method has ended and hasn't been instructed to begin again
                    pass
                elif self.method_start_act == 'Ready' or self.method_start_act is None:
                    # Method has been instructed to begin
                    now = datetime.datetime.now()
                    self.method_start_time = now
                    if method_data_repeat and method_data_repeat.duration_end:
                        self.method_end_time = now + datetime.timedelta(
                            seconds=float(method_data_repeat.duration_end))

                    with session_scope(MYCODO_DB_PATH) as db_session:
                        mod_pid = db_session.query(PID)
                        mod_pid = mod_pid.filter(PID.id == self.pid_id).first()
                        mod_pid.method_start_time = self.method_start_time
                        mod_pid.method_end_time = self.method_end_time
                        db_session.commit()
                else:
                    # Method neither instructed to begin or not to
                    # Likely there was a daemon restart ot power failure
                    # Resume method with saved start_time
                    self.method_start_time = datetime.datetime.strptime(
                        str(pid.method_start_time), '%Y-%m-%d %H:%M:%S.%f')
                    if method_data_repeat and method_data_repeat.duration_end:
                        self.method_end_time = datetime.datetime.strptime(
                            str(pid.method_end_time), '%Y-%m-%d %H:%M:%S.%f')
                        if self.method_end_time > datetime.datetime.now():
                            self.logger.warning(
                                "Resuming method {id}: started {start}, "
                                "ends {end}".format(
                                    id=self.method_id,
                                    start=self.method_start_time,
                                    end=self.method_end_time))
                        else:
                            self.method_start_act = 'Ended'
                    else:
                        self.method_start_act = 'Ended'

    def run(self):
        try:
            self.running = True
            self.logger.info("Activated in {:.1f} ms".format(
                (timeit.default_timer() - self.thread_startup_timer) * 1000))
            if self.is_paused:
                self.logger.info("Paused")
            elif self.is_held:
                self.logger.info("Held")
            self.ready.set()

            while self.running:

                if self.method_start_act == 'Ended':
                    self.stop_controller(ended_normally=False,
                                         deactivate_pid=True)
                    self.logger.warning(
                        "Method has ended. "
                        "Activate the PID controller to start it again.")

                elif t.time() > self.timer:
                    # Ensure the timer ends in the future
                    while t.time() > self.timer:
                        self.timer = self.timer + self.period

                    # If PID is active, retrieve input measurement and update PID output
                    if self.is_activated and not self.is_paused:
                        self.get_last_measurement()

                        if self.last_measurement_success:
                            # Update setpoint using a method if one is selected
                            if self.method_id:
                                this_controller = db_retrieve_table_daemon(
                                    PID, device_id=self.pid_id)
                                setpoint, ended = calculate_method_setpoint(
                                    self.method_id,
                                    PID,
                                    this_controller,
                                    Method,
                                    MethodData,
                                    self.logger)
                                if ended:
                                    self.method_start_act = 'Ended'
                                if setpoint is not None:
                                    self.set_point = setpoint
                                else:
                                    self.set_point = self.default_set_point

                            write_setpoint_db = threading.Thread(
                                target=write_influxdb_value,
                                args=(self.pid_unique_id,
                                      'setpoint',
                                      self.set_point,))
                            write_setpoint_db.start()

                            # Update PID and get control variable
                            self.control_variable = self.update_pid_output(
                                self.last_measurement)

                    # If PID is active or on hold, activate relays
                    if ((self.is_activated and not self.is_paused) or
                            (self.is_activated and self.is_held)):
                        self.manipulate_output()
                t.sleep(0.1)

            # Turn off relay used in PID when the controller is deactivated
            if self.raise_relay_id and self.direction in ['raise', 'both']:
                self.control.relay_off(self.raise_relay_id, trigger_conditionals=True)
            if self.lower_relay_id and self.direction in ['lower', 'both']:
                self.control.relay_off(self.lower_relay_id, trigger_conditionals=True)

            self.running = False
            self.logger.info("Deactivated in {:.1f} ms".format(
                (timeit.default_timer() - self.thread_shutdown_timer) * 1000))
        except Exception as except_msg:
                self.logger.exception("Run Error: {err}".format(
                    err=except_msg))

    def initialize_values(self):
        """Set PID parameters"""
        pid = db_retrieve_table_daemon(PID, device_id=self.pid_id)
        self.is_activated = pid.is_activated
        self.is_held = pid.is_held
        self.is_paused = pid.is_paused
        self.method_id = pid.method_id
        self.direction = pid.direction
        self.raise_relay_id = pid.raise_relay_id
        self.raise_min_duration = pid.raise_min_duration
        self.raise_max_duration = pid.raise_max_duration
        self.raise_min_off_duration = pid.raise_min_off_duration
        self.lower_relay_id = pid.lower_relay_id
        self.lower_min_duration = pid.lower_min_duration
        self.lower_max_duration = pid.lower_max_duration
        self.lower_min_off_duration = pid.lower_min_off_duration
        self.Kp = pid.p
        self.Ki = pid.i
        self.Kd = pid.d
        self.integrator_min = pid.integrator_min
        self.integrator_max = pid.integrator_max
        self.period = pid.period
        self.max_measure_age = pid.max_measure_age
        self.default_set_point = pid.setpoint
        self.set_point = pid.setpoint

        input_unique_id = pid.measurement.split(',')[0]
        self.measurement = pid.measurement.split(',')[1]

        input = db_retrieve_table_daemon(Input, unique_id=input_unique_id)
        self.input_unique_id = input.unique_id
        self.input_duration = input.period

        try:
            self.raise_relay_type = db_retrieve_table_daemon(
                Relay, device_id=self.raise_relay_id).relay_type
        except AttributeError:
            self.raise_relay_type = None
        try:
            self.lower_relay_type = db_retrieve_table_daemon(
                Relay, device_id=self.lower_relay_id).relay_type
        except AttributeError:
            self.lower_relay_type = None

        return "success"

    def update_pid_output(self, current_value):
        """
        Calculate PID output value from reference input and feedback

        :return: Manipulated, or control, variable. This is the PID output.
        :rtype: float

        :param current_value: The input, or process, variable (the actual
            measured condition by the input)
        :type current_value: float
        """
        self.error = self.set_point - current_value

        # Calculate P-value
        self.P_value = self.Kp * self.error

        # Calculate I-value
        self.integrator += self.error

        # First method for managing integrator
        if self.integrator > self.integrator_max:
            self.integrator = self.integrator_max
        elif self.integrator < self.integrator_min:
            self.integrator = self.integrator_min

        # Second method for regulating integrator
        # if self.period is not None:
        #     if self.integrator * self.Ki > self.period:
        #         self.integrator = self.period / self.Ki
        #     elif self.integrator * self.Ki < -self.period:
        #         self.integrator = -self.period / self.Ki

        self.I_value = self.integrator * self.Ki

        # Calculate D-value
        self.D_value = self.Kd * (self.error - self.derivator)
        self.derivator = self.error

        # Produce output form P, I, and D values
        pid_value = self.P_value + self.I_value + self.D_value

        return pid_value

    def get_last_measurement(self):
        """
        Retrieve the latest input measurement from InfluxDB

        :rtype: None
        """
        self.last_measurement_success = False
        # Get latest measurement (from within the past minute) from influxdb
        try:
            if self.input_duration < 60:
                duration = 60
            else:
                duration = int(self.input_duration * 1.5)
            self.last_measurement = read_last_influxdb(
                self.input_unique_id,
                self.measurement,
                duration)
            if self.last_measurement:
                self.last_time = self.last_measurement[0]
                self.last_measurement = self.last_measurement[1]

                utc_dt = datetime.datetime.strptime(
                    self.last_time.split(".")[0],
                    '%Y-%m-%dT%H:%M:%S')
                utc_timestamp = calendar.timegm(utc_dt.timetuple())
                local_timestamp = str(datetime.datetime.fromtimestamp(utc_timestamp))
                self.logger.debug("Latest {meas}: {last} @ {ts}".format(
                    meas=self.measurement,
                    last=self.last_measurement,
                    ts=local_timestamp))
                if calendar.timegm(t.gmtime())-utc_timestamp > self.max_measure_age:
                    self.logger.error(
                        "Last measurement was {last_sec} seconds ago, however"
                        " the maximum measurement age is set to {max_sec}"
                        " seconds.".format(
                            last_sec=calendar.timegm(t.gmtime())-utc_timestamp,
                            max_sec=self.max_measure_age
                        ))
                self.last_measurement_success = True
            else:
                self.logger.warning("No data returned from influxdb")
        except requests.ConnectionError:
            self.logger.error("Failed to read measurement from the "
                              "influxdb database: Could not connect.")
        except Exception as except_msg:
            self.logger.exception(
                "Exception while reading measurement from the influxdb "
                "database: {err}".format(err=except_msg))

    def manipulate_output(self):
        """
        Activate output based on PID control variable and whether
        the manipulation directive is to raise, lower, or both.

        :rtype: None
        """
        # If the last measurement was able to be retrieved and was entered within the past minute
        if self.last_measurement_success:
            #
            # PID control variable is positive, indicating a desire to raise
            # the environmental condition
            #
            if self.direction in ['raise', 'both'] and self.raise_relay_id:

                if self.control_variable > 0:
                    # Turn off lower_relay if active, because we're now raising
                    if (self.direction == 'both' and
                            self.lower_relay_id and
                            self.control.relay_state(self.lower_relay_id) != 'off'):
                        self.control.relay_off(self.lower_relay_id)

                    # Determine if the output should be PWM or a duration
                    if self.raise_relay_type == 'pwm':
                        self.raise_duty_cycle = float("{0:.1f}".format(
                            self.control_var_to_duty_cycle(self.control_variable)))

                        # Ensure the duty cycle doesn't exceed the min/max
                        if (self.raise_max_duration and
                                self.raise_duty_cycle > self.raise_max_duration):
                            self.raise_duty_cycle = self.raise_max_duration
                        elif (self.raise_min_duration and
                                self.raise_duty_cycle < self.raise_min_duration):
                            self.raise_duty_cycle = self.raise_min_duration

                        self.logger.debug(
                            "Setpoint: {sp}, Control Variable: {cv}, Output: PWM output "
                            "{id} to {dc:.1f}%".format(
                                sp=self.set_point,
                                cv=self.control_variable,
                                id=self.raise_relay_id,
                                dc=self.raise_duty_cycle))

                        # Activate pwm with calculated duty cycle
                        self.control.relay_on(self.raise_relay_id,
                                              duty_cycle=self.raise_duty_cycle)

                        pid_entry_value = self.control_var_to_duty_cycle(
                            abs(self.control_variable))
                        if self.control_variable < 0:
                            pid_entry_value = -pid_entry_value
                        self.write_pid_output_influxdb('duty_cycle', pid_entry_value)

                    elif self.raise_relay_type in ['command', 'wired', 'wireless_433MHz_pi_switch']:
                        # Ensure the relay on duration doesn't exceed the set maximum
                        if (self.raise_max_duration and
                                self.control_variable > self.raise_max_duration):
                            self.raise_seconds_on = self.raise_max_duration
                        else:
                            self.raise_seconds_on = float("{0:.2f}".format(
                                self.control_variable))

                        if self.raise_seconds_on > self.raise_min_duration:
                            # Activate raise_relay for a duration
                            self.logger.debug(
                                "Setpoint: {sp} Output: {cv} to relay "
                                "{id}".format(
                                    sp=self.set_point,
                                    cv=self.control_variable,
                                    id=self.raise_relay_id))
                            self.control.relay_on(
                                self.raise_relay_id,
                                duration=self.raise_seconds_on,
                                min_off=self.raise_min_off_duration)

                        self.write_pid_output_influxdb('pid_output', self.control_variable)

                else:
                    if self.raise_relay_type == 'pwm':
                        self.control.relay_on(self.raise_relay_id,
                                              duty_cycle=0)
                    else:
                        self.control.relay_off(self.raise_relay_id)

            #
            # PID control variable is negative, indicating a desire to lower
            # the environmental condition
            #
            if self.direction in ['lower', 'both'] and self.lower_relay_id:

                if self.control_variable < 0:
                    # Turn off raise_relay if active, because we're now raising
                    if (self.direction == 'both' and
                            self.raise_relay_id and
                            self.control.relay_state(self.raise_relay_id) != 'off'):
                        self.control.relay_off(self.raise_relay_id)

                    # Determine if the output should be PWM or a duration
                    if self.lower_relay_type == 'pwm':
                        self.lower_duty_cycle = float("{0:.1f}".format(
                            self.control_var_to_duty_cycle(abs(self.control_variable))))

                        # Ensure the duty cycle doesn't exceed the min/max
                        if (self.lower_max_duration and
                                self.lower_duty_cycle > self.lower_max_duration):
                            self.lower_duty_cycle = self.lower_max_duration
                        elif (self.lower_min_duration and
                                self.lower_duty_cycle < self.lower_min_duration):
                            self.lower_duty_cycle = self.lower_min_duration

                        self.logger.debug(
                            "Setpoint: {sp}, Control Variable: {cv}, Output: PWM output "
                            "{id} to {dc:.1f}%".format(
                                sp=self.set_point,
                                cv=self.control_variable,
                                id=self.lower_relay_id,
                                dc=self.lower_duty_cycle))

                        # Turn back negative for proper logging
                        self.lower_duty_cycle = -self.lower_duty_cycle

                        # Activate pwm with calculated duty cycle
                        self.control.relay_on(
                            self.lower_relay_id,
                            duty_cycle=self.lower_duty_cycle)

                        pid_entry_value = self.control_var_to_duty_cycle(
                            abs(self.control_variable))
                        pid_entry_value = -pid_entry_value
                        self.write_pid_output_influxdb('duty_cycle', pid_entry_value)

                    elif self.lower_relay_type in ['command', 'wired', 'wireless_433MHz_pi_switch']:
                        # Ensure the relay on duration doesn't exceed the set maximum
                        if (self.lower_max_duration and
                                abs(self.control_variable) > self.lower_max_duration):
                            self.lower_seconds_on = self.lower_max_duration
                        else:
                            self.lower_seconds_on = abs(float("{0:.2f}".format(
                                self.control_variable)))

                        if self.lower_seconds_on > self.lower_min_duration:
                            # Activate lower_relay for a duration
                            self.logger.debug("Setpoint: {sp} Output: {cv} to "
                                              "relay {id}".format(
                                                sp=self.set_point,
                                                cv=self.control_variable,
                                                id=self.lower_relay_id))
                            self.control.relay_on(
                                self.lower_relay_id,
                                duration=self.lower_seconds_on,
                                min_off=self.lower_min_off_duration)

                        self.write_pid_output_influxdb('pid_output', self.control_variable)

                else:
                    if self.lower_relay_type == 'pwm':
                        self.control.relay_on(self.lower_relay_id,
                                              duty_cycle=0)
                    else:
                        self.control.relay_off(self.lower_relay_id)

        else:
            if self.direction in ['raise', 'both'] and self.raise_relay_id:
                self.control.relay_off(self.raise_relay_id)
            if self.direction in ['lower', 'both'] and self.lower_relay_id:
                self.control.relay_off(self.lower_relay_id)

    def control_var_to_duty_cycle(self, control_variable):
        # Convert control variable to duty cycle
        if control_variable > self.period:
            return 100.0
        else:
            return float((control_variable / self.period) * 100)

    def write_pid_output_influxdb(self, pid_entry_type, pid_entry_value):
        write_pid_out_db = threading.Thread(
            target=write_influxdb_value,
            args=(self.pid_unique_id,
                  pid_entry_type,
                  pid_entry_value,))
        write_pid_out_db.start()

    def pid_mod(self):
        if self.initialize_values():
            return "success"
        else:
            return "error"

    def pid_hold(self):
        self.is_held = True
        self.logger.info("Hold")
        return "success"

    def pid_pause(self):
        self.is_paused = True
        self.logger.info("Pause")
        return "success"

    def pid_resume(self):
        self.is_activated = True
        self.is_held = False
        self.is_paused = False
        self.logger.info("Resume")
        return "success"

    def set_setpoint(self, set_point):
        """ Initilize the setpoint of PID """
        self.set_point = set_point
        self.integrator = 0
        self.derivator = 0

    def set_integrator(self, integrator):
        """ Set the integrator of the controller """
        self.integrator = integrator

    def set_derivator(self, derivator):
        """ Set the derivator of the controller """
        self.derivator = derivator

    def set_kp(self, p):
        """ Set Kp gain of the controller """
        self.Kp = p

    def set_ki(self, i):
        """ Set Ki gain of the controller """
        self.Ki = i

    def set_kd(self, d):
        """ Set Kd gain of the controller """
        self.Kd = d

    def get_setpoint(self):
        return self.set_point

    def get_error(self):
        return self.error

    def get_integrator(self):
        return self.integrator

    def get_derivator(self):
        return self.derivator

    def is_running(self):
        return self.running

    def stop_controller(self, ended_normally=True, deactivate_pid=False):
        self.thread_shutdown_timer = timeit.default_timer()
        self.running = False
        # Unset method start time
        if self.method_id and ended_normally:
            with session_scope(MYCODO_DB_PATH) as db_session:
                mod_pid = db_session.query(PID).filter(
                    PID.id == self.pid_id).first()
                mod_pid.method_start_time = 'Ended'
                mod_pid.method_end_time = None
                db_session.commit()

        if deactivate_pid:
            with session_scope(MYCODO_DB_PATH) as db_session:
                mod_pid = db_session.query(PID).filter(
                    PID.id == self.pid_id).first()
                mod_pid.is_activated = False
                db_session.commit()
