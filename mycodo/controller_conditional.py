# coding=utf-8
#
# controller_conditional.py - Conditional controller that checks measurements
#                             and performs functions on at predefined
#                             intervals
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

import datetime
import logging
import threading
import time
import timeit

import RPi.GPIO as GPIO

from mycodo.config import SQL_DATABASE_MYCODO
from mycodo.databases.models import Camera
from mycodo.databases.models import Conditional
from mycodo.databases.models import ConditionalActions
from mycodo.databases.models import Input
from mycodo.databases.models import LCD
from mycodo.databases.models import Math
from mycodo.databases.models import Output
from mycodo.databases.models import PID
from mycodo.databases.models import SMTP
from mycodo.databases.models import Timer
from mycodo.databases.utils import session_scope
from mycodo.devices.camera import camera_record
from mycodo.mycodo_client import DaemonControl
from mycodo.utils.database import db_retrieve_table_daemon
from mycodo.utils.influx import read_last_influxdb
from mycodo.utils.send_data import send_email
from mycodo.utils.sunriseset import Sun
from mycodo.utils.system_pi import cmd_output

MYCODO_DB_PATH = 'sqlite:///' + SQL_DATABASE_MYCODO


class ConditionalController(threading.Thread):
    """
    Class to operate Conditional controller

    Conditionals are conditional statements that can either be True or False
    When a conditional is True, one or more actions associated with that
    conditional are executed.

    The main loop in this class will continually check if the timers for
    Measurement Conditionals have elapsed, then check if any of the
    conditionals are True with the check_conditionals() function. If any are
    True, trigger_conditional_actions() will be ran to execute all actions
    associated with that particular conditional.

    Edge and Output conditionals are triggered from
    the Input and Output controllers, respectively, and the
    trigger_conditional_actions() function in this class will be ran.
    """
    def __init__(self):
        threading.Thread.__init__(self)

        self.logger = logging.getLogger("mycodo.conditional")

        self.running = False
        self.thread_startup_timer = timeit.default_timer()
        self.thread_shutdown_timer = 0
        self.pause_loop = False
        self.verify_pause_loop = True
        self.control = DaemonControl()

        self.is_activated = {}
        self.period = {}
        self.timer_period = {}
        self.refractory_period = {}
        self.timer_refractory_period = {}

        # Timer
        self.timer_duration = {}
        self.timer_timer_period = {}

        self.smtp_max_count = db_retrieve_table_daemon(
            SMTP, entry='first').hourly_max
        self.email_count = 0
        self.allowed_to_send_notice = True
        self.smtp_wait_timer = {}

        self.setup_conditionals()

    def run(self):
        try:
            self.running = True
            self.logger.info(
                "Conditional controller activated in {:.1f} ms".format(
                (timeit.default_timer() - self.thread_startup_timer) * 1000))

            while self.running:
                # Pause loop to modify conditional statements.
                # Prevents execution of conditional while variables are
                # being modified.
                if self.pause_loop:
                    self.verify_pause_loop = True
                    while self.pause_loop:
                        time.sleep(0.1)

                # Check each activated conditional
                for each_id in self.is_activated:

                    if self.is_activated[each_id]:
                        # Check if the conditional period has elapsed
                        if (self.timer_period and
                                (self.timer_period[each_id] < time.time() and
                                 self.timer_refractory_period[each_id] < time.time())
                                ):
                            # Update conditional timer
                            while self.timer_period[each_id] < time.time():
                                self.timer_period[each_id] += self.period[each_id]
                            self.check_conditionals(each_id)

                        # Check if a timer has been triggered
                        elif (self.timer_timer_period and
                                (self.timer_timer_period[each_id] < time.time())
                                ):
                            # Update timer timer
                            while self.timer_timer_period[each_id] < time.time():
                                self.timer_timer_period[each_id] += self.timer_duration[each_id]
                            self.check_conditionals(each_id)

                time.sleep(0.1)

            self.running = False
            self.logger.info(
                "Conditional controller deactivated in {:.1f} ms".format(
                    (timeit.default_timer() -
                     self.thread_shutdown_timer) * 1000))
        except Exception as except_msg:
            self.logger.exception("Run Error: {err}".format(
                err=except_msg))

    def setup_conditionals(self):
        """
        Refresh the conditional settings

        This is ran in response to settings being changed in the database
        by the web UI
        """
        # Signal to pause the main loop and wait for verification
        self.pause_loop = True
        while not self.verify_pause_loop:
            time.sleep(0.1)

        self.is_activated = {}
        self.period = {}
        self.timer_period = {}
        self.refractory_period = {}
        self.timer_refractory_period = {}

        # Timer
        self.timer_duration = {}
        self.timer_timer_period = {}

        self.smtp_wait_timer = {}

        now = time.time()

        # Set up all measurement conditionals
        conditional = db_retrieve_table_daemon(
            Conditional).filter(Conditional.conditional_type == 'conditional_measurement').all()
        for each_cond in conditional:
            self.is_activated[each_cond.unique_id] = each_cond.is_activated
            self.period[each_cond.unique_id] = each_cond.period
            self.refractory_period[each_cond.unique_id] = each_cond.refractory_period
            self.timer_refractory_period[each_cond.unique_id] = 0
            self.smtp_wait_timer[each_cond.unique_id] = now + 3600
            self.timer_period[each_cond.unique_id] = now + self.period[each_cond.unique_id]

        # Set up all timer conditionals
        conditional = db_retrieve_table_daemon(
            Conditional).filter(Conditional.conditional_type == 'conditional_timer_duration').all()
        for each_cond in conditional:
            self.is_activated[each_cond.unique_id] = each_cond.is_activated
            self.timer_duration[each_cond.unique_id] = each_cond.timer_duration
            if each_cond.timer_start_offset:
                self.timer_timer_period[each_cond.unique_id] = now + each_cond.timer_start_offset
            else:
                self.timer_timer_period[each_cond.unique_id] = now

        # Set up all sunrise/sunset conditionals
        conditional = db_retrieve_table_daemon(
            Conditional).filter(Conditional.conditional_type == 'conditional_sunrise_sunset').all()
        for each_cond in conditional:
            self.is_activated[each_cond.unique_id] = each_cond.is_activated
            self.timer_refractory_period[each_cond.unique_id] = 0
            self.period[each_cond.unique_id] = 1000
            # Set the next trigger at the specified sunrise/sunset time (+-offsets)
            self.timer_period[each_cond.unique_id] = self.calculate_sunrise_sunset_epoch(each_cond)

        self.logger.info("Conditional settings refreshed")

        self.pause_loop = False
        self.verify_pause_loop = False

    def check_conditionals(self, cond_id):
        """
        Check if any Conditionals are activated and
        execute their actions if the Conditional is true.

        For example, if measured temperature is above 30C, notify me@gmail.com

        "if measured temperature is above 30C" is the Conditional to check.
        "notify me@gmail.com" is the Conditional Action to execute if the
        Conditional is True.

        :param cond_id: The Conditional ID to check
        :return:
        """
        last_measurement = None
        gpio_state = None

        logger_cond = logging.getLogger("mycodo.conditional_{id}".format(
            id=cond_id))

        cond = db_retrieve_table_daemon(
            Conditional, unique_id=cond_id, entry='first')

        now = time.time()
        timestamp = datetime.datetime.fromtimestamp(now).strftime('%Y-%m-%d %H:%M:%S')
        message = "{ts}\n[Conditional {id} ({name})]".format(
            ts=timestamp,
            name=cond.name,
            id=cond_id)

        device_id = cond.measurement.split(',')[0]

        if len(cond.measurement.split(',')) > 1:
            device_measurement = cond.measurement.split(',')[1]
        else:
            device_measurement = None

        direction = cond.direction
        setpoint = cond.setpoint
        max_age = cond.max_age

        device = None

        input_dev = db_retrieve_table_daemon(
            Input, unique_id=device_id, entry='first')
        if input_dev:
            device = input_dev

        math = db_retrieve_table_daemon(
            Math, unique_id=device_id, entry='first')
        if math:
            device = math

        output = db_retrieve_table_daemon(
            Output, unique_id=device_id, entry='first')
        if output:
            device = output

        pid = db_retrieve_table_daemon(
            PID, unique_id=device_id, entry='first')
        if pid:
            device = pid

        if not device:
            message += " Error: Controller not Input, Math, Output, or PID"
            logger_cond.error(message)
            return

        # Check Measurement Conditionals
        if (cond.conditional_type == 'conditional_measurement' and
                direction and device_id and device_measurement):

            # Check if there hasn't been a measurement in the last set number
            # of seconds. If not, trigger conditional
            if direction == 'none_found':
                last_measurement = self.get_last_measurement(
                    device_id, device_measurement, max_age)
                if last_measurement is None:
                    message += " Measurement {meas} for device ID {id} not found in the past" \
                               " {value} seconds.".format(
                        meas=device_measurement,
                        id=device_id,
                        value=max_age)
                else:
                    return

            # Check if last measurement is greater or less than the set value
            else:
                last_measurement = self.get_last_measurement(
                    device_id,
                    device_measurement,
                    max_age)
                if last_measurement is None:
                    logger_cond.debug("Last measurement not found")
                    return
                elif ((direction == 'above' and
                       last_measurement > setpoint) or
                      (direction == 'below' and
                       last_measurement < setpoint)):

                    message += " Measurement {meas}: {value} ".format(
                        meas=device_measurement,
                        value=last_measurement)
                    if direction == 'above':
                        message += ">"
                    elif direction == 'below':
                        message += "<"
                    message += " {sp} (set value).".format(
                        sp=setpoint)
                else:
                    return  # Not triggered

        # If the edge detection variable is set, calling this function will
        # trigger an edge detection event. This will merely produce the correct
        # message based on the edge detection settings.
        elif cond.conditional_type == 'conditional_edge':
            try:
                GPIO.setmode(GPIO.BCM)
                GPIO.setup(int(input_dev.pin), GPIO.IN)
                gpio_state = GPIO.input(int(input_dev.pin))
            except:
                gpio_state = None
                logger_cond.error("Exception reading the GPIO pin")
            if (input_dev and
                    input_dev.location and
                    gpio_state is not None and
                    gpio_state == cond.if_sensor_gpio_state):
                message += " GPIO State Detected (state = {state}).".format(
                    state=cond.if_sensor_gpio_state)
            else:
                logger_cond.error("GPIO not configured correctly or GPIO state not verified")
                return

        # Calculate the sunrise/sunset times and find the next time this conditional should trigger
        elif cond.conditional_type == 'conditional_sunrise_sunset':
            # Since the check time is the trigger time, we will only calculate and set the next trigger time
            self.timer_period[cond_id] = self.calculate_sunrise_sunset_epoch(cond)

        # If the code hasn't returned by now, the conditional has been triggered
        # and the actions for that conditional should be executed
        if cond.conditional_type == 'conditional_measurement':
            self.timer_refractory_period[cond_id] = time.time() + self.refractory_period[cond_id]
        
        self.trigger_conditional_actions(
            cond_id, message=message, last_measurement=last_measurement,
            device_id=device_id, device_measurement=device_measurement,
            edge=gpio_state)

    def trigger_conditional_actions(self, cond_id,
                                    message='', last_measurement=None,
                                    device_id=None, device_measurement=None, edge=None,
                                    output_state=None, on_duration=None, duty_cycle=None):
        """
        If a Conditional has been triggered, this function will execute
        the Conditional Actions

        :param self: self from the Controller class
        :param cond_id: The ID of the Conditional
        :param device_id: The unique ID associated with the device_measurement
        :param message: The message generated from the conditional check
        :param last_measurement: The last measurement value
        :param device_measurement: The measurement (i.e. "temperature")
        :param edge: If edge conditional, rise/on (1) or fall/off (0)
        :param output_state: If output conditional, the output state (on/off) to trigger the action
        :param on_duration: If output conditional, the ON duration
        :param duty_cycle: If output conditional, the duty cycle
        :return:
        """
        logger_cond = logging.getLogger("mycodo.conditional_{id}".format(
            id=cond_id))

        # List of all email notification recipients
        # List is appended with TO email addresses when an email Action is
        # encountered. An email is sent to all recipients after all actions
        # have been executed.
        email_recipients = []

        attachment_file = False
        attachment_type = False
        input_dev = None
        output = None
        device = None

        cond_actions = db_retrieve_table_daemon(ConditionalActions)
        cond_actions = cond_actions.filter(
            ConditionalActions.conditional_id == cond_id).all()

        if device_id:
            input_dev = db_retrieve_table_daemon(
                Input, unique_id=device_id, entry='first')
            if input_dev:
                device = input_dev

            math = db_retrieve_table_daemon(
                Math, unique_id=device_id, entry='first')
            if math:
                device = math

            output = db_retrieve_table_daemon(
                Output, unique_id=device_id, entry='first')
            if output:
                device = output

            pid = db_retrieve_table_daemon(
                PID, unique_id=device_id, entry='first')
            if pid:
                device = pid

        for cond_action in cond_actions:
            message += "\n[Conditional Action {id}]:".format(
                id=cond_action.id, do_action=cond_action.do_action)

            # Actuate output (duration)
            if (cond_action.do_action == 'output' and cond_action.do_unique_id and
                    cond_action.do_output_state in ['on', 'off']):
                message += " Turn output {id} {state}".format(
                    id=cond_action.do_unique_id,
                    state=cond_action.do_output_state)
                if (cond_action.do_output_state == 'on' and
                        cond_action.do_output_duration):
                    message += " for {sec} seconds".format(
                        sec=cond_action.do_output_duration)
                message += "."

                output_on_off = threading.Thread(
                    target=self.control.output_on_off,
                    args=(cond_action.do_unique_id,
                          cond_action.do_output_state,),
                    kwargs={'duration': cond_action.do_output_duration})
                output_on_off.start()

            # Actuate output (PWM)
            elif (cond_action.do_action == 'output_pwm' and cond_action.do_unique_id and
                    cond_action.do_output_pwm):
                message += " Turn output {id} duty cycle to {duty_cycle}%.".format(
                    id=cond_action.do_unique_id,
                    duty_cycle=cond_action.do_output_pwm)

                output_on = threading.Thread(
                    target=self.control.output_on,
                    args=(cond_action.do_unique_id,),
                    kwargs={'duty_cycle': cond_action.do_output_pwm})
                output_on.start()

            # Execute command in shell
            elif cond_action.do_action == 'command':

                # Replace string variables with actual values
                command_str = cond_action.do_action_string

                # Replace measurement variables
                if last_measurement:
                    command_str = command_str.replace(
                        "((measure_{var}))".format(
                            var=device_measurement), str(last_measurement))
                if device and device.period:
                    command_str = command_str.replace(
                        "((measure_period))", str(device.period))
                if input_dev:
                    command_str = command_str.replace(
                        "((measure_location))", str(input_dev.location))
                if input_dev and device_measurement == input_dev.cmd_measurement:
                    command_str = command_str.replace(
                        "((measure_linux_command))", str(input_dev.location))

                # Replace output variables
                if output:
                    if output.pin:
                        command_str = command_str.replace(
                            "((output_pin))", str(output.pin))
                    if output_state:
                        command_str = command_str.replace(
                            "((output_action))", str(output_state))
                    if on_duration:
                        command_str = command_str.replace(
                            "((output_duration))", str(on_duration))
                    if duty_cycle:
                        command_str = command_str.replace(
                            "((output_pwm))", str(duty_cycle))

                # Replace edge variables
                if edge:
                    command_str = command_str.replace(
                        "((edge_state))", str(edge))

                message += " Execute '{com}' ".format(
                    com=command_str)

                _, _, cmd_status = cmd_output(command_str)

                message += "(return status: {stat}).".format(stat=cmd_status)

            # Capture photo
            elif cond_action.do_action in ['photo', 'photo_email']:
                message += "  Capturing photo with camera ({id}).".format(
                    id=cond_action.do_unique_id)
                camera_still = db_retrieve_table_daemon(
                    Camera, unique_id=cond_action.do_unique_id)
                attachment_file = camera_record('photo', camera_still.unique_id)

            # Capture video
            elif cond_action.do_action in ['video', 'video_email']:
                message += "  Capturing video with camera ({id}).".format(
                    id=cond_action.do_unique_id)
                camera_stream = db_retrieve_table_daemon(
                    Camera, unique_id=cond_action.do_unique_id)
                attachment_file = camera_record(
                    'video', camera_stream.unique_id,
                    duration_sec=cond_action.do_camera_duration)

            # Activate Controller
            elif cond_action.do_action == 'activate_controller':
                message += " Activate Controller ({id}).".format(
                    id=cond_action.do_unique_id)
                (controller_type,
                 controller_object,
                 controller_entry) = self.which_controller(
                    cond_action.do_unique_id)
                if controller_entry.is_activated:
                    message += " Notice: Controller is already active!"
                else:
                    with session_scope(MYCODO_DB_PATH) as new_session:
                        mod_cont = new_session.query(controller_object).filter(
                            controller_object.unique_id == cond_action.do_unique_id).first()
                        mod_cont.is_activated = True
                        new_session.commit()
                    activate_controller = threading.Thread(
                        target=self.control.controller_activate,
                        args=(controller_type,
                              cond_action.do_unique_id,))
                    activate_controller.start()

            # Deactivate Controller
            elif cond_action.do_action == 'deactivate_controller':
                message += " Deactivate Controller ({id}).".format(
                    id=cond_action.do_unique_id)
                (controller_type,
                 controller_object,
                 controller_entry) = self.which_controller(
                    cond_action.do_unique_id)
                if not controller_entry.is_activated:
                    message += " Notice: Controller is already inactive!"
                else:
                    with session_scope(MYCODO_DB_PATH) as new_session:
                        mod_cont = new_session.query(controller_object).filter(
                            controller_object.unique_id == cond_action.do_unique_id).first()
                        mod_cont.is_activated = False
                        new_session.commit()
                    deactivate_controller = threading.Thread(
                        target=self.control.controller_deactivate,
                        args=(controller_type,
                              cond_action.do_unique_id,))
                    deactivate_controller.start()

            # Resume PID controller
            elif cond_action.do_action == 'resume_pid':
                message += " Resume PID ({id}).".format(
                    id=cond_action.do_unique_id)
                pid = db_retrieve_table_daemon(
                    PID, unique_id=cond_action.do_unique_id, entry='first')
                if not pid.is_paused:
                    message += " Notice: PID is not paused!"
                elif pid.is_activated:
                    with session_scope(MYCODO_DB_PATH) as new_session:
                        mod_pid = new_session.query(PID).filter(
                            PID.unique_id == cond_action.do_unique_id).first()
                        mod_pid.is_paused = False
                        new_session.commit()
                    resume_pid = threading.Thread(
                        target=self.control.pid_resume,
                        args=(cond_action.do_unique_id,))
                    resume_pid.start()

            # Pause PID controller
            elif cond_action.do_action == 'pause_pid':
                message += " Pause PID ({id}).".format(
                    id=cond_action.do_unique_id)
                pid = db_retrieve_table_daemon(
                    PID, unique_id=cond_action.do_unique_id, entry='first')
                if pid.is_paused:
                    message += " Notice: PID is already paused!"
                elif pid.is_activated:
                    with session_scope(MYCODO_DB_PATH) as new_session:
                        mod_pid = new_session.query(PID).filter(
                            PID.unique_id == cond_action.do_unique_id).first()
                        mod_pid.is_paused = True
                        new_session.commit()
                    pause_pid = threading.Thread(
                        target=self.control.pid_pause,
                        args=(cond_action.do_unique_id,))
                    pause_pid.start()

            # Set PID Setpoint
            elif cond_action.do_action == 'setpoint_pid':
                message += " Set Setpoint of PID ({id}).".format(
                    id=cond_action.do_unique_id)
                pid = db_retrieve_table_daemon(
                    PID, unique_id=cond_action.do_unique_id, entry='first')
                if pid.is_activated:
                    setpoint_pid = threading.Thread(
                        target=self.control.pid_set,
                        args=(pid.unique_id,
                              'setpoint',
                              float(cond_action.do_action_string),))
                    setpoint_pid.start()
                else:
                    with session_scope(MYCODO_DB_PATH) as new_session:
                        mod_pid = new_session.query(PID).filter(
                            PID.unique_id == cond_action.do_unique_id).first()
                        mod_pid.setpoint = cond_action.do_action_string
                        new_session.commit()

            # Set PID Method and start method from beginning
            elif cond_action.do_action == 'method_pid':
                message += " Set Method of PID ({id}).".format(
                    id=cond_action.do_unique_id)

                # Instruct method to start
                with session_scope(MYCODO_DB_PATH) as new_session:
                    mod_pid = new_session.query(PID).filter(
                        PID.unique_id == cond_action.do_unique_id).first()
                    mod_pid.method_start_time = 'Ready'
                    new_session.commit()

                pid = db_retrieve_table_daemon(
                    PID, unique_id=cond_action.do_unique_id, entry='first')
                if pid.is_activated:
                    method_pid = threading.Thread(
                        target=self.control.pid_set,
                        args=(pid.unique_id,
                              'method',
                              cond_action.do_action_string,))
                    method_pid.start()
                else:
                    with session_scope(MYCODO_DB_PATH) as new_session:
                        mod_pid = new_session.query(PID).filter(
                            PID.unique_id == cond_action.do_unique_id).first()
                        mod_pid.method_id = cond_action.do_action_string
                        new_session.commit()

            # Email the Conditional message. Optionally capture a photo or
            # video and attach to the email.
            elif cond_action.do_action in ['email',
                                           'photo_email',
                                           'video_email']:

                if (self.email_count >= self.smtp_max_count and
                        time.time() < self.smtp_wait_timer[cond_id]):
                    self.allowed_to_send_notice = False
                else:
                    if time.time() > self.smtp_wait_timer[cond_id]:
                        self.email_count = 0
                        self.smtp_wait_timer[cond_id] = time.time() + 3600
                    self.allowed_to_send_notice = True
                self.email_count += 1

                # If the emails per hour limit has not been exceeded
                if self.allowed_to_send_notice:
                    email_recipients.append(cond_action.do_action_string)
                    message += " Notify {email}.".format(
                        email=cond_action.do_action_string)
                    # attachment_type != False indicates to
                    # attach a photo or video
                    if cond_action.do_action == 'photo_email':
                        message += " Photo attached to email."
                        attachment_type = 'still'
                    elif cond_action.do_action == 'video_email':
                        message += " Video attached to email."
                        attachment_type = 'video'
                else:
                    logger_cond.error(
                        "Wait {sec:.0f} seconds to email again.".format(
                            sec=self.smtp_wait_timer[cond_id] - time.time()))

            elif cond_action.do_action == 'flash_lcd_on':
                lcd = db_retrieve_table_daemon(
                    LCD, unique_id=cond_action.do_unique_id)
                message += " Flash LCD On {id} ({name}).".format(
                    id=lcd.id,
                    name=lcd.name)

                start_flashing = threading.Thread(
                    target=self.control.lcd_flash,
                    args=(cond_action.do_unique_id, True,))
                start_flashing.start()

            elif cond_action.do_action == 'flash_lcd_off':
                lcd = db_retrieve_table_daemon(
                    LCD, unique_id=cond_action.do_unique_id)
                message += " Flash LCD Off {id} ({name}).".format(
                    id=lcd.id,
                    name=lcd.name)

                start_flashing = threading.Thread(
                    target=self.control.lcd_flash,
                    args=(cond_action.do_unique_id, False,))
                start_flashing.start()

            elif cond_action.do_action == 'lcd_backlight_off':
                lcd = db_retrieve_table_daemon(
                    LCD, unique_id=cond_action.do_unique_id)
                message += " LCD Backlight Off {id} ({name}).".format(
                    id=lcd.id,
                    name=lcd.name)

                start_flashing = threading.Thread(
                    target=self.control.lcd_backlight,
                    args=(cond_action.do_unique_id, False,))
                start_flashing.start()

            elif cond_action.do_action == 'lcd_backlight_on':
                lcd = db_retrieve_table_daemon(
                    LCD, unique_id=cond_action.do_unique_id)
                message += " LCD Backlight On {id} ({name}).".format(
                    id=lcd.id,
                    name=lcd.name)

                start_flashing = threading.Thread(
                    target=self.control.lcd_backlight,
                    args=(cond_action.do_unique_id, True,))
                start_flashing.start()

        # Send email after all conditional actions have been checked
        # In order to append all action messages to send in the email
        # send_email_at_end will be None or the TO email address
        if email_recipients:
            smtp = db_retrieve_table_daemon(SMTP, entry='first')
            send_email(smtp.host, smtp.ssl, smtp.port,
                       smtp.user, smtp.passw, smtp.email_from,
                       email_recipients, message,
                       attachment_file, attachment_type)

        logger_cond.debug(message)

    def which_controller(self, unique_id):
        controller_type = None
        controller_object = None
        controller_entry = None
        if db_retrieve_table_daemon(Conditional, unique_id=unique_id):
            controller_type = 'Conditional'
            controller_object = Conditional
            controller_entry = db_retrieve_table_daemon(
                Conditional, unique_id=unique_id)
        elif db_retrieve_table_daemon(Input, unique_id=unique_id):
            controller_type = 'Input'
            controller_object = Input
            controller_entry = db_retrieve_table_daemon(
                Input, unique_id=unique_id)
        elif db_retrieve_table_daemon(LCD, unique_id=unique_id):
            controller_type = 'LCD'
            controller_object = LCD
            controller_entry = db_retrieve_table_daemon(
                LCD, unique_id=unique_id)
        elif db_retrieve_table_daemon(Math, unique_id=unique_id):
            controller_type = 'Math'
            controller_object = Math
            controller_entry = db_retrieve_table_daemon(
                Math, unique_id=unique_id)
        elif db_retrieve_table_daemon(PID, unique_id=unique_id):
            controller_type = 'PID'
            controller_object = PID
            controller_entry = db_retrieve_table_daemon(
                PID, unique_id=unique_id)
        elif db_retrieve_table_daemon(Timer, unique_id=unique_id):
            controller_type = 'Timer'
            controller_object = Timer
            controller_entry = db_retrieve_table_daemon(
                Timer, unique_id=unique_id)
        return controller_type, controller_object, controller_entry

    @staticmethod
    def calculate_sunrise_sunset_epoch(cond):
        try:
            # Adjust for date offset
            now = datetime.datetime.now()
            new_date = now + datetime.timedelta(days=cond.date_offset_days)

            sun = Sun(latitude=cond.latitude,
                      longitude=cond.longitude,
                      zenith=cond.zenith,
                      day=new_date.day,
                      month=new_date.month,
                      year=new_date.year)
            sunrise = sun.get_sunrise_time()
            sunset = sun.get_sunset_time()

            # Adjust for time offset
            new_sunrise = sunrise['time_local'] + datetime.timedelta(minutes=cond.time_offset_minutes)
            new_sunset = sunset['time_local'] + datetime.timedelta(minutes=cond.time_offset_minutes)

            if cond.rise_or_set == 'sunrise':
                # If the sunrise is in the past, add a day
                if float(new_sunrise.strftime('%s')) < time.time():
                    tomorrow_sunrise = new_sunrise + datetime.timedelta(days=1)
                    return float(tomorrow_sunrise.strftime('%s'))
                else:
                    return float(new_sunrise.strftime('%s'))
            elif cond.rise_or_set == 'sunset':
                # If the sunrise is in the past, add a day
                if float(new_sunset.strftime('%s')) < time.time():
                    tomorrow_sunset = new_sunset + datetime.timedelta(days=1)
                    return float(tomorrow_sunset.strftime('%s'))
                else:
                    return float(new_sunset.strftime('%s'))
        except:
            return None

    @staticmethod
    def get_last_measurement(unique_id, measurement, duration_sec):
        """
        Retrieve the latest input measurement

        :return: The latest input value or None if no data available
        :rtype: float or None

        :param unique_id: ID of controller
        :type unique_id: str
        :param measurement: Environmental condition of a input (e.g.
            temperature, humidity, pressure, etc.)
        :type measurement: str
        :param duration_sec: number of seconds to check for a measurement
            in the past.
        :type duration_sec: int
        """
        last_measurement = read_last_influxdb(
            unique_id, measurement, duration_sec=duration_sec)

        if last_measurement is not None:
            last_value = last_measurement[1]
            return last_value

    def is_running(self):
        return self.running

    def stop_controller(self):
        self.thread_shutdown_timer = timeit.default_timer()
        self.running = False
