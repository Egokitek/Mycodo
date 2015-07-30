#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#  mycodo.py - The Mycodo deamon (back-end)
#
#  Copyright (C) 2015  Kyle T. Gabriel
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

#### Install Directory ####
install_directory = "/var/www/mycodo"

# Mycodo modules
import mycodoGraph
import mycodoLog

# Other modules
import Adafruit_DHT
import datetime
import fcntl
import getopt
import logging
import os
import re
import rpyc
import RPi.GPIO as GPIO
import serial
import smtplib
import sqlite3
import traceback
import subprocess
import sys
import threading
import time
from array import *
from email.mime.text import MIMEText
from lockfile import LockFile
from rpyc.utils.server import ThreadedServer

mycodo_database = "%s/config/mycodo.db" % install_directory # SQLite database
image_path = "%s/images" % install_directory # Where generated graphs are stored
log_path = "%s/log" % install_directory # Where generated logs are stored

# Daemon log on tempfs
daemon_log_file_tmp = "%s/daemon-tmp.log" % log_path

logging.basicConfig(
    filename = daemon_log_file_tmp,
    level = logging.INFO,
    format = '%(asctime)s [%(levelname)s] %(message)s')

# Where lockfiles are stored for certain processes
lock_directory = "/var/lock/mycodo"
sql_lock_path = "%s/config" % lock_directory
daemon_lock_path = "%s/daemon" % lock_directory
sensor_t_lock_path = "%s/sensor-t" % lock_directory
sensor_ht_lock_path = "%s/sensor-ht" % lock_directory
sensor_co2_lock_path = "%s/sensor-co2" % lock_directory

# GPIO pins (BCM numbering) and name of devices attached to relay
relay_num = None
relay_pin = [0] * 9
relay_name = [0] * 9
relay_trigger = [0] * 9
relay_start_state = [0] * 9

# Temperature & Humidity Sensors
sensor_t_num = 0
sensor_t_name = [0] * 5
sensor_t_device = [0] * 5
sensor_t_pin = [0] * 5
sensor_t_period = [0] * 5
sensor_t_activated = [0] * 5
sensor_t_graph = [0] * 5
sensor_t_read_temp_c = [0] * 5
sensor_t_read_hum = [0] * 5
sensor_t_dewpt_c = [0] * 5

# T Sensor Temperature PID
pid_t_temp_relay_high = [0] * 5
pid_t_temp_relay_low = [0] * 5
pid_t_temp_set = [0] * 5
pid_t_temp_set_dir = [0] * 5
pid_t_temp_set_buf = [0] * 5
pid_t_temp_period = [0] * 5
pid_t_temp_p_high = [0] * 5
pid_t_temp_i_high = [0] * 5
pid_t_temp_d_high = [0] * 5
pid_t_temp_p_low = [0] * 5
pid_t_temp_i_low = [0] * 5
pid_t_temp_d_low = [0] * 5
pid_t_temp_or = [0] * 5
pid_t_temp_alive = [1] * 5
pid_t_temp_active = [0] * 5

# Temperature & Humidity Sensors
sensor_ht_num = 0
sensor_ht_name = [0] * 5
sensor_ht_device = [0] * 5
sensor_ht_pin = [0] * 5
sensor_ht_period = [0] * 5
sensor_ht_activated = [0] * 5
sensor_ht_graph = [0] * 5
sensor_ht_read_temp_c = [0] * 5
sensor_ht_read_hum = [0] * 5
sensor_ht_dewpt_c = [0] * 5

# HT Sensor Temperature PID
pid_ht_temp_relay_high = [0] * 5
pid_ht_temp_relay_low = [0] * 5
pid_ht_temp_set = [0] * 5
pid_ht_temp_set_dir = [0] * 5
pid_ht_temp_set_buf = [0] * 5
pid_ht_temp_period = [0] * 5
pid_ht_temp_p_high = [0] * 5
pid_ht_temp_i_high = [0] * 5
pid_ht_temp_d_high = [0] * 5
pid_ht_temp_p_low = [0] * 5
pid_ht_temp_i_low = [0] * 5
pid_ht_temp_d_low = [0] * 5
pid_ht_temp_or = [0] * 5
pid_ht_temp_alive = [1] * 5
pid_ht_temp_active = [0] * 5

# Humidity PID
pid_ht_hum_relay_high = [0] * 5
pid_ht_hum_relay_low = [0] * 5
pid_ht_hum_set = [0] * 5
pid_ht_hum_set_dir = [0] * 5
pid_ht_hum_set_buf = [0] * 5
pid_ht_hum_period = [0] * 5
pid_ht_hum_p_high = [0] * 5
pid_ht_hum_i_high = [0] * 5
pid_ht_hum_d_high = [0] * 5
pid_ht_hum_p_low = [0] * 5
pid_ht_hum_i_low = [0] * 5
pid_ht_hum_d_low = [0] * 5
pid_ht_hum_or = [0] * 5
pid_ht_hum_alive = [1] * 5
pid_ht_hum_active = [0] * 5

# CO2 Sensors
sensor_co2_num = 0
sensor_co2_name = [0] * 5
sensor_co2_device = [0] * 5
sensor_co2_pin = [0] * 5
sensor_co2_period = [0] * 5
sensor_co2_activated = [0] * 5
sensor_co2_graph = [0] * 5
sensor_co2_read_co2 = [0] * 5

# CO2 PID
pid_co2_relay_high = [0] * 5
pid_co2_relay_low = [0] * 5
pid_co2_set = [0] * 5
pid_co2_set_dir = [0] * 5
pid_co2_set_buf = [0] * 5
pid_co2_period = [0] * 5
pid_co2_p_high = [0] * 5
pid_co2_i_high = [0] * 5
pid_co2_d_high = [0] * 5
pid_co2_p_low = [0] * 5
pid_co2_i_low = [0] * 5
pid_co2_d_low = [0] * 5
pid_co2_or = [0] * 5
pid_co2_alive = [1] * 5
pid_co2_active = [0] * 2

# PID Restarting
pid_number = None
pid_t_temp_down = 0
pid_t_temp_up = 0
pid_ht_temp_down = 0
pid_ht_temp_up = 0
pid_ht_hum_down = 0
pid_ht_hum_up = 0
pid_co2_down = 0
pid_co2_up = 0

# Timers
timer_num = None
timer_name = [0] * 9
timer_relay = [0] * 9
timer_state = [0] * 9
timer_duration_on = [0] * 9
timer_duration_off = [0] * 9
timer_change = 0

# SMTP notify
smtp_host = None
smtp_ssl = None
smtp_port = None
smtp_user = None
smtp_pass = None
smtp_email_from = None
smtp_email_to = None

# Miscellaneous
camera_light = None
server = None
client_que = '0'
client_var = None

# Threaded server that receives commands from mycodo-client.py
class ComServer(rpyc.Service):
    def exposed_ChangeRelay(self, relay, state):
        if (state == 1):
            logging.info("[Client command] Changing Relay %s to HIGH", relay)
            relay_onoff(int(relay), 'on')
        elif (state == 0):
            logging.info("[Client command] Changing Relay %s to LOW", relay)
            relay_onoff(int(relay), 'off')
        else:
            logging.info("[Client command] Turning Relay %s On for %s seconds", relay, state)
            rod = threading.Thread(target = relay_on_duration,
                args = (int(relay), int(state), 0,))
            rod.start()
        return 1
    def exposed_GenerateGraph(self, sensor_type, graph_type, graph_span, graph_id, sensor_number):
        if (graph_span == 'default'):
            logging.info("[Client command] Generate Graph: %s %s %s %s", sensor_type, graph_span, graph_id, sensor_number)
        else:
            logging.info("[Client command] Generate Graph: %s %s %s %s %s", sensor_type, graph_type, graph_span, graph_id, sensor_number)
        mycodoGraph.generate_graph(sensor_type, graph_type, graph_span, graph_id, sensor_number, sensor_t_num, sensor_t_name, sensor_t_graph, sensor_t_period, pid_t_temp_relay_high, pid_t_temp_relay_low, sensor_ht_num, sensor_ht_name, sensor_ht_graph, sensor_ht_period, pid_ht_temp_relay_high, pid_ht_temp_relay_low, pid_ht_hum_relay_high, pid_ht_hum_relay_low, sensor_co2_num, sensor_co2_name, sensor_co2_graph, sensor_co2_period, pid_co2_relay_high, pid_co2_relay_low, relay_name)
        return 1
    def exposed_PID_start(self, pidtype, number):
        PID_start(pidtype, number)
    def exposed_PID_stop(self, pidtype, number):
        PID_stop(pidtype, number)
        return 1
    def exposed_ReadCO2Sensor(self, pin, sensor):
        logging.info("[Client command] Read CO2 Sensor %s from GPIO pin %s", sensor, pin)
        if (sensor == 'K30'):
            read_co2_sensor(sensor)
            return sensor_co2_read_co2
        else:
            return 'Invalid Sensor Name'
    def exposed_ReadHTSensor(self, pin, sensor):
        logging.info("[Client command] Read HT Sensor %s from GPIO pin %s", sensor, pin)
        if (sensor == 'DHT11'): device = Adafruit_DHT.DHT11
        elif (sensor == 'DHT22'): device = Adafruit_DHT.DHT22
        elif (sensor == 'AM2302'): device = Adafruit_DHT.AM2302
        else:
            return 'Invalid Sensor Name'
        hum, tc = Adafruit_DHT.read_retry(device, pin)
        return (tc, hum)
    def exposed_ReadTSensor(self, pin, device):
        logging.info("[Client command] Read T Sensor %s from GPIO pin %s", sensor, pin)
        if (sensor == 'DS18B20'):
            return read_t(0, device, pin)
        else:
            return 'Invalid Sensor Name'
    def exposed_SQLReload(self, relay):
        logging.info("[Client command] Reload SQLite database")
        read_sql()
        if relay:
            logging.info("[Client command] Relay %s GPIO pin changed to %s, initialize and turn off", relay, relay_pin[relay])
            initialize_gpio(relay)
        return 1
    def exposed_Status(self, var):
        logging.debug("[Client command] Request status report")

        return "1 Test1 Test2"
    def exposed_Terminate(self, remoteCommand):
        global client_que
        client_que = 'TerminateServer'
        logging.info("[Client command] terminate threads and shut down")
        return 1
    def exposed_WriteTSensorLog(self, sensor):
        global client_que
        global client_var
        client_var = sensor
        client_que = 'write_t_sensor_log'
        if sensor:
            logging.info("[Client command] Read T sensor number %s and append log", sensor)
        else:
            logging.info("[Client command] Read all T sensors and append log")
        global change_sensor_log
        change_sensor_log = 1
        while (change_sensor_log):
            time.sleep(0.1)
        return 1
    def exposed_WriteHTSensorLog(self, sensor):
        global client_que
        global client_var
        client_var = sensor
        client_que = 'write_ht_sensor_log'
        if sensor:
            logging.info("[Client command] Read HT sensor number %s and append log", sensor)
        else:
            logging.info("[Client command] Read all HT sensors and append log")
        global change_sensor_log
        change_sensor_log = 1
        while (change_sensor_log):
            time.sleep(0.1)
        return 1
    def exposed_WriteCO2SensorLog(self, sensor):
        global client_que
        global client_var
        client_var = sensor
        client_que = 'write_co2_sensor_log'
        if sensor:
            logging.info("[Client command] Read CO2 sensor number %s and append log", sensor)
        else:
            logging.info("[Client command] Read all CO2 sensors and append log")
        global change_sensor_log
        change_sensor_log = 1
        while (change_sensor_log):
            time.sleep(0.1)
        return 1

class ComThread(threading.Thread):
    def run(self):
        global server
        server = ThreadedServer(ComServer, port = 18812)
        server.start()

# PID controller
class PID:
    def __init__(self, P=2.0, I=0.0, D=1.0, Derivator=0, Integrator=0,
            Integrator_max=500, Integrator_min=-500):
        self.Kp=P
        self.Ki=I
        self.Kd=D
        self.Derivator=Derivator
        self.Integrator=Integrator
        self.Integrator_max=Integrator_max
        self.Integrator_min=Integrator_min
        self.set_point=0.0
        self.error=0.0
    def update(self, current_value):
        """Calculate PID output value from reference input and feedback"""
        self.error = self.set_point - current_value
        self.P_value = self.Kp * self.error
        self.D_value = self.Kd * ( self.error - self.Derivator)
        self.Derivator = self.error
        self.Integrator = self.Integrator + self.error
        if self.Integrator > self.Integrator_max:
            self.Integrator = self.Integrator_max
        elif self.Integrator < self.Integrator_min:
            self.Integrator = self.Integrator_min
        self.I_value = self.Integrator * self.Ki
        PID = self.P_value + self.I_value + self.D_value
        return PID
    def setPoint(self, set_point):
        """Initilize the setpoint of PID"""
        self.set_point = set_point
        self.Integrator=0
        self.Derivator=0
    def setIntegrator(self, Integrator):
        self.Integrator = Integrator
    def setDerivator(self, Derivator):
        self.Derivator = Derivator
    def setKp(self,P):
        self.Kp=P
    def setKi(self,I):
        self.Ki=I
    def setKd(self,D):
        self.Kd=D
    def getPoint(self):
        return self.set_point
    def getError(self):
        return self.error
    def getIntegrator(self):
        return self.Integrator
    def getDerivator(self):
        return self.Derivator


# Displays the program usage
def usage():
    print "mycodo.py: Daemon that reads sensors, writes logs, and operates"
    print "           relays to maintain set environmental conditions."
    print "           Run as root.\n"
    print "Usage:  mycodo.py [OPTION]...\n"
    print "Options:"
    print "    -h, --help"
    print "           Display this help and exit"
    print "    -l, --log level"
    print "           Set logging level: w < i < d (default: ""i"")"
    print "           Options:"
    print "           ""w"": warnings only"
    print "           ""i"": info and warnings"
    print "           ""d"": debug, info, and warnings"
    print "    -v, --verbose"
    print "           enables log output to the console\n"
    print "Examples: mycodo.py"
    print "          mycodo.py -l d"
    print "          mycodo.py -l w -v\n"

# Check for any command line options
def menu():
    a = 'silent'
    b = 'info'

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hl:v',
            ["help", "log", "verbose"])
    except getopt.GetoptError as err:
        print(err) # will print "option -a not recognized"
        usage()
        return 2

    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage()
            return 1
        elif opt in ("-l", "--log"):
            if (arg == 'w'): b = 'warning'
            elif (arg == 'd'): b = 'debug'
        elif opt in ("-v", "--verbose"):
            a = 'verbose'
        else:
            assert False, "Fail"

    daemon(a, b)
    return 1


#################################################
#                    Daemon                     #
#################################################

# Read sensors, modify relays based on sensor values, write sensor/relay
# logs, and receive/execute commands from mycodo-client.py
def daemon(output, log):
    global pid_t_temp_active
    global pid_t_temp_alive
    global pid_t_temp_down
    global pid_t_temp_up

    global pid_ht_temp_active
    global pid_ht_temp_alive
    global pid_ht_temp_down
    global pid_ht_temp_up

    global pid_ht_hum_active
    global pid_ht_hum_alive
    global pid_ht_hum_down
    global pid_ht_hum_up

    global pid_co2_active
    global pid_co2_alive
    global pid_co2_down
    global pid_co2_up
    
    global change_sensor_log
    global server
    global client_que
    timer_time = [0] * 9
    timerTSensorLog  = [0] * 5
    timerHTSensorLog  = [0] * 5
    timerCo2SensorLog  = [0] * 5

    # Set log level based on startup argument
    if (log == 'warning'):
        logging.getLogger().setLevel(logging.WARNING)
    elif (log == 'info'):
        logging.getLogger().setLevel(logging.INFO)
    else:
        logging.getLogger().setLevel(logging.DEBUG)

    if (output == 'verbose'):
        # define a Handler which writes DEBUG messages or higher to the sys.stderr
        console = logging.StreamHandler()
        console.setLevel(logging.DEBUG)
        # add the handler to the root logger
        logging.getLogger('').addHandler(console)

    logging.info("[Daemon] Daemon Started")

    logging.info("[Daemon} Communication server thread starting")
    ct = ComThread()
    ct.daemon = True
    ct.start()
    time.sleep(1)

    logging.info("[Daemon] Reading SQL database and initializing variables")
    read_sql()

    logging.info("[Daemon] Conducting initial sensor readings: %s T, %s HT, and %s CO2", sum(sensor_t_activated), sum(sensor_ht_activated), sum(sensor_co2_activated))

    for i in range(1, sensor_t_num+1):
        if sensor_t_device[i] != 'Other' and sensor_t_activated[i] == 1:
            read_t_sensor(i)

    for i in range(1, sensor_ht_num+1):
        if sensor_ht_device[i] != 'Other' and sensor_ht_activated[i] == 1:
            read_ht_sensor(i)

    for i in range(1, sensor_co2_num+1):
        if sensor_co2_device[i] != 'Other' and sensor_co2_activated[i] == 1:
            read_co2_sensor(i)

    logging.info("[Daemon] Initial sensor readings complete")

    # How often to backup all logs to SD card
    timerLogBackup = int(time.time()) + 21600  # 21600 seconds = 6 hours

    for i in range(1, 5):
        timerTSensorLog[i] = int(time.time()) + sensor_t_period[i]

    for i in range(1, 5):
        timerHTSensorLog[i] = int(time.time()) + sensor_ht_period[i]

    for i in range(1, 5):
        timerCo2SensorLog[i] = int(time.time()) + sensor_co2_period[i]

    for i in range(1, 9):
        timer_time[i] = int(time.time())

    threads_t_t = []
    threads_ht_t = []
    threads_ht_h = []
    threads_co2 = []

    for i in range(1, 5):
        if (pid_t_temp_or[i] == 0):
            pid_t_temp_active[i] = 1
            rod = threading.Thread(target = t_sensor_temperature_monitor,
                args = ('Thread-T-T-%d' % i, i,))
            rod.start()
            threads_t_t.append(rod)

    for i in range(1, 5):
        if (pid_ht_temp_or[i] == 0):
            pid_ht_temp_active[i] = 1
            rod = threading.Thread(target = ht_sensor_temperature_monitor,
                args = ('Thread-HT-T-%d' % i, i,))
            rod.start()
            threads_ht_t.append(rod)

    for i in range(1, 5):
        if (pid_ht_hum_or[i] == 0):
            pid_ht_hum_active[i] = 1
            rod = threading.Thread(target = ht_sensor_humidity_monitor,
                args = ('Thread-HT-H-%d' % i, i,))
            rod.start()
            threads_ht_h.append(rod)

    for i in range(1, 5):
        if (pid_co2_or[i] == 0):
            pid_co2_active[i] = 1
            rod = threading.Thread(target = co2_monitor,
                args = ('Thread-CO2-%d' % i, i,))
            rod.start()
            threads_co2.append(rod)

    while True: # Main loop of the daemon
        if client_que != '0': # Run remote commands issued by mycodo-client.py
            if client_que == 'write_t_sensor_log':
                logging.debug("[Client command] Write T Sensor Log")
                if (client_var != 0 and sensor_t_activated[client_var]):
                    if read_t_sensor(client_var) == 1:
                        mycodoLog.write_t_sensor_log(sensor_t_read_temp_c, client_var)
                    else:
                        logging.warning("Could not read Temp-%s sensor, not writing to sensor log", client_var)
                else:
                    for i in range(1, int(sensor_t_num)+1):
                        if sensor_t_activated[i]:
                            if read_t_sensor(i) == 1:
                                mycodoLog.write_t_sensor_log(sensor_t_read_temp_c, i)
                            else:
                                logging.warning("Could not read Temp-%s sensor, not writing to sensor log", i)
                            time.sleep(0.1)
                change_sensor_log = 0
            elif client_que == 'write_ht_sensor_log':
                logging.debug("[Client command] Write HT Sensor Log")
                if (client_var != 0 and sensor_ht_activated[client_var]):
                    if read_ht_sensor(client_var) == 1:
                        mycodoLog.write_ht_sensor_log(sensor_ht_read_temp_c, sensor_ht_read_hum, sensor_ht_dewpt_c, client_var)
                    else:
                        logging.warning("Could not read Hum/Temp-%s sensor, not writing to sensor log", client_var)
                else:
                    for i in range(1, int(sensor_ht_num)+1):
                        if sensor_ht_activated[i]:
                            if read_ht_sensor(i) == 1:
                                mycodoLog.write_ht_sensor_log(sensor_ht_read_temp_c, sensor_ht_read_hum, sensor_ht_dewpt_c, i)
                            else:
                                logging.warning("Could not read Hum/Temp-%s sensor, not writing to sensor log", i)
                            time.sleep(0.1)
                change_sensor_log = 0
            elif client_que == 'write_co2_sensor_log':
                logging.debug("[Client command] Write CO2 Sensor Log")
                if (client_var != 0 and sensor_co2_activated[client_var]):
                    if read_co2_sensor(client_var) == 1:
                        mycodoLog.write_co2_sensor_log(sensor_co2_read_co2, client_var)
                    else:
                        logging.warning("Could not read CO2-%s sensor, not writing to sensor log", client_var)
                else:
                    for i in range(1, int(sensor_co2_num)+1):
                        if sensor_co2_activated[i]:
                            if read_co2_sensor(i) == 1:
                                mycodoLog.write_co2_sensor_log(sensor_co2_read_co2, i)
                            else:
                                logging.warning("Could not read CO2-%s sensor, not writing to sensor log", i)
                            time.sleep(0.1)
                change_sensor_log = 0
            elif client_que == 'TerminateServer':
                logging.info("[Daemon] Backing up logs")
                mycodoLog.Concatenate_Logs()

                logging.info("[Daemon] Commanding all PIDs to turn off")
                pid_t_temp_alive = [0] * 5
                pid_ht_temp_alive =  [0] * 5
                pid_ht_hum_alive =  [0] * 5
                pid_co2_alive =  [0] * 5

                for t in threads_t_t:
                    t.join()
                for t in threads_ht_t:
                    t.join()
                for t in threads_ht_h:
                    t.join()
                for t in threads_co2:
                    t.join()
                server.close()

                logging.info("[Daemon] Waiting for all PIDs to turn off")
                for i in range(1, 5):
                    if pid_t_temp_or[i] == 0:
                        while pid_t_temp_alive[i] == 0:
                            time.sleep(0.1)

                for i in range(1, 5):
                    if pid_ht_temp_or[i] == 0:
                        while pid_ht_temp_alive[i] == 0:
                            time.sleep(0.1)

                for i in range(1, 5):
                    if pid_ht_hum_or[i] == 0:
                        while pid_ht_hum_alive[i] == 0:
                            time.sleep(0.1)

                for i in range(1, 5):
                    if pid_co2_or[i] == 0:
                        while pid_co2_alive[i] == 0:
                            time.sleep(0.1)
                logging.info("[Daemon] All PIDs have turned off")

                logging.info("[Daemon] Turning off all relays")
                Relays_Off()

                logging.info("[Daemon] Exiting Python")
                return 0
            elif client_que == 'TimerChange':
                timer_time[timer_change] = 0
                if (timer_state[timer_change] == 0 and timer_relay[timer_change] != 0):
                    relay_onoff(timer_relay[timer_change], 'off')

            client_que = '0'

        if pid_t_temp_down:
            if pid_t_temp_active[pid_number] == 1:
                logging.info("[Daemon] Shutting Down Temperature PID Thread-T-T-%s", pid_number)
                pid_t_temp_alive[pid_number] = 0
                while pid_t_temp_alive[pid_number] != 2:
                    time.sleep(0.1)
                relay_onoff(int(pid_t_temp_relay_high[pid_number]), 'off')
                relay_onoff(int(pid_t_temp_relay_low[pid_number]), 'off')
                pid_t_temp_alive[pid_number] = 1
                pid_t_temp_active[pid_number] = 0
            else:
                logging.warning("[Daemon] Cannot Shut Down Temperature PID Thread-T-T-%s: It isn't running.", pid_number)
            pid_t_temp_down = 0

        if pid_t_temp_up:
            if pid_t_temp_active[pid_number] == 0:
                logging.info("[Daemon] Starting Temperature PID Thread-T-T-%s", pid_number)
                rod = threading.Thread(target = ht_sensor_temperature_monitor,
                    args = ('Thread-T-T-%d' % pid_number, pid_number,))
                rod.start()
                pid_t_temp_active[pid_number] = 1
            else:
                logging.warning("[Daemon] Cannot Start Temperature PID Thread-T-T-%s: It's already running.", pid_number)
            pid_t_temp_up = 0

        if pid_ht_temp_down:
            if pid_ht_temp_active[pid_number] == 1:
                logging.info("[Daemon] Shutting Down Temperature PID Thread-HT-T-%s", pid_number)
                pid_ht_temp_alive[pid_number] = 0
                while pid_ht_temp_alive[pid_number] != 2:
                    time.sleep(0.1)
                relay_onoff(int(pid_ht_temp_relay_high[pid_number]), 'off')
                relay_onoff(int(pid_ht_temp_relay_low[pid_number]), 'off')
                pid_ht_temp_alive[pid_number] = 1
                pid_ht_temp_active[pid_number] = 0
            else:
                logging.warning("[Daemon] Cannot Shut Down Temperature PID Thread-HT-T-%s: It isn't running.", pid_number)
            pid_ht_temp_down = 0

        if pid_ht_temp_up:
            if pid_ht_temp_active[pid_number] == 0:
                logging.info("[Daemon] Starting Temperature PID Thread-%s", pid_number)
                rod = threading.Thread(target = ht_sensor_temperature_monitor,
                    args = ('Thread-%d' % pid_number, pid_number,))
                rod.start()
                pid_ht_temp_active[pid_number] = 1
            else:
                logging.warning("[Daemon] Cannot Start Temperature PID Thread-HT-T-%s: It's already running.", pid_number)
            pid_ht_temp_up = 0

        if pid_ht_hum_down:
            if pid_ht_hum_active[pid_number] == 1:
                logging.info("[Daemon] Shutting Down Humidity PID Thread-HT-H-%s", pid_number)
                pid_ht_hum_alive[pid_number] = 0
                while pid_ht_hum_alive[pid_number] != 2:
                    time.sleep(0.1)
                relay_onoff(int(pid_ht_hum_relay_high[pid_number]), 'off')
                relay_onoff(int(pid_ht_hum_relay_low[pid_number]), 'off')
                pid_ht_hum_alive[pid_number] = 1
                pid_ht_hum_active[pid_number] = 0
            else:
                logging.warning("[Daemon] Cannot Shut Down Humidity PID Thread-HT-H-%s: It isn't running.", pid_number)
            pid_ht_hum_down = 0

        if pid_ht_hum_up:
            if pid_ht_hum_active[pid_number] == 0:
                logging.info("[Daemon] Starting Humidity PID Thread-HT-H-%s", pid_number)
                rod = threading.Thread(target = ht_sensor_humidity_monitor,
                    args = ('Thread-%d' % pid_number, pid_number,))
                rod.start()
                pid_ht_hum_active[pid_number] = 1
            else:
                logging.warning("[Daemon] Cannot Start Humidity PID Thread-HT-H-%s: It's already running.", pid_number)
            pid_ht_hum_up = 0

        if pid_co2_down:
            if pid_co2_active[pid_number] == 1:
                logging.info("[Daemon] Shutting Down CO2 PID Thread-CO2-%s", pid_number)
                pid_co2_alive[pid_number] = 0
                while pid_co2_alive[pid_number] != 2:
                    time.sleep(0.1)
                relay_onoff(int(pid_co2_relay_high[pid_number]), 'off')
                relay_onoff(int(pid_co2_relay_low[pid_number]), 'off')
                pid_co2_alive[pid_number] = 1
                pid_co2_active[pid_number] = 0
            else:
                logging.warning("[Daemon] Cannot Shut Down CO2 PID Thread-CO2-%s: It isn't running.", pid_number)
            pid_co2_down = 0

        if pid_co2_up:
            if pid_co2_active[pid_number] == 0:
                logging.info("[Daemon] Starting CO2 PID Thread-CO2-%s", pid_number)
                rod = threading.Thread(target = co2_monitor,
                    args = ('Thread-%d' % pid_number, pid_number,))
                rod.start()
                pid_co2_active[pid_number] = 1
            else:
                logging.warning("[Daemon] Cannot Start CO2 PID Thread-CO2-%s: It's already running.", pid_number)
            pid_co2_up = 0

        # Write temperature to sensor log
        for i in range(1, 5):
            if int(time.time()) > timerTSensorLog[i] and sensor_t_device[i] != 'Other' and sensor_t_activated[i] == 1:
                logging.debug("[Timer Expiration] Read sensor %s every %s seconds: Write sensor log", i, sensor_t_period[i])
                if read_t_sensor(i) == 1:
                    mycodoLog.write_t_sensor_log(sensor_t_read_temp_c, i)
                else:
                    logging.warning("Could not read Temp-%s sensor, not writing to sensor log", i)
                timerTSensorLog[i] = int(time.time()) + sensor_t_period[i]

        # Write temperature and humidity to sensor log
        for i in range(1, 5):
            if int(time.time()) > timerHTSensorLog[i] and sensor_ht_device[i] != 'Other' and sensor_ht_activated[i] == 1:
                logging.debug("[Timer Expiration] Read sensor %s every %s seconds: Write sensor log", i, sensor_ht_period[i])
                if read_ht_sensor(i) == 1:
                    mycodoLog.write_ht_sensor_log(sensor_ht_read_temp_c, sensor_ht_read_hum, sensor_ht_dewpt_c, i)
                else:
                    logging.warning("Could not read Hum/Temp-%s sensor, not writing to sensor log", i)
                timerHTSensorLog[i] = int(time.time()) + sensor_ht_period[i]

        # Write CO2 to sensor log
        for i in range(1, 5):
            if int(time.time()) > timerCo2SensorLog[i] and sensor_co2_device[i] != 'Other' and sensor_co2_activated[i] == 1:
                if read_co2_sensor(i) == 1:
                    mycodoLog.write_co2_sensor_log(sensor_co2_read_co2, i)
                else:
                    logging.warning("Could not read CO2-%s sensor, not writing to sensor log", i)
                timerCo2SensorLog[i] = int(time.time()) + sensor_co2_period[i]

        # Concatenate local log with tempfs log every 6 hours
        if int(time.time()) > timerLogBackup:
            mycodoLog.Concatenate_Logs()
            timerLogBackup = int(time.time()) + 21600

        # Handle timers
        if timer_num != 0:
            for i in range(1, 9):
                if int(time.time()) > timer_time[i]:
                    if timer_state[i] == 1:
                        logging.debug("[Timer Expiration] Timer %s: Turn Relay %s on for %s seconds, off %s seconds.", i, timer_relay[i], timer_duration_on[i], timer_duration_off[i])
                        rod = threading.Thread(target = relay_on_duration,
                            args = (timer_relay[i], timer_duration_on[i], 0,))
                        rod.start()
                        timer_time[i] = int(time.time()) + timer_duration_on[i] + timer_duration_off[i]

        time.sleep(0.1)


#################################################
#                  PID Control                  #
#################################################

# Temperature Sensor Temperature modulation by PID control
def t_sensor_temperature_monitor(ThreadName, sensor):
    global pid_t_temp_alive
    timerTemp = 0
    PIDTemp = 0

    logging.info("[PID T-Temperature-%s] Starting %s", sensor, ThreadName)

    # Turn activated PID relays off
    if pid_t_temp_relay_high[sensor] != 0:
        relay_onoff(int(pid_t_temp_relay_high[sensor]), 'off')
    if pid_t_temp_relay_low[sensor] != 0:
        relay_onoff(int(pid_t_temp_relay_low[sensor]), 'off')

    # Add buffer to PID set point to create a low and high margin
    high = pid_t_temp_set[sensor] + pid_t_temp_set_buf[sensor]
    low = pid_t_temp_set[sensor] - pid_t_temp_set_buf[sensor]

    # Create a low and high PID from buffer
    p_temp_high = PID(pid_t_temp_p_high[sensor], pid_t_temp_i_high[sensor], pid_t_temp_d_high[sensor])
    p_temp_high.setPoint(high)
    p_temp_low = PID(pid_t_temp_p_low[sensor], pid_t_temp_i_low[sensor], pid_t_temp_d_low[sensor])
    p_temp_low.setPoint(low)

    while (pid_t_temp_alive[sensor]):
        if ( ( (pid_t_temp_set_dir[sensor] == 0 and
            pid_t_temp_relay_high[sensor] != 0 and
            pid_t_temp_relay_low[sensor] != 0) or 

            (pid_t_temp_set_dir[sensor] == -1 and
            pid_t_temp_relay_high[sensor] != 0) or

            (pid_t_temp_set_dir[sensor] == 1 and
            pid_t_temp_relay_low[sensor] != 0) ) and

            pid_t_temp_or[sensor] == 0 and
            pid_t_temp_down == 0 and
            sensor_t_activated[sensor] == 1):

            if int(time.time()) > timerTemp:

                logging.debug("[PID T-Temperature-%s] Reading temperature...", sensor)
                if read_t_sensor(sensor) == 1:

                    PIDTempHigh = abs(p_temp_high.update(float(sensor_t_read_temp_c[sensor])))
                    PIDTempLow = abs(p_temp_low.update(float(sensor_t_read_temp_c[sensor])))

                    if (sensor_t_read_temp_c[sensor] > high) or (sensor_t_read_temp_c[sensor] < low):

                        if (sensor_t_read_temp_c[sensor] > high) and (pid_t_temp_set_dir[sensor] < 1):

                            logging.debug("[PID T-Temperature-%s] Temperature: %.1f°C now > %.1f°C set_high", sensor, sensor_t_read_temp_c[sensor], high)
                            logging.debug("[PID T-Temperature-%s] PID = %.1f (seconds)", sensor, PIDTempHigh)

                            if (PIDTempHigh > 0):
                                rod = threading.Thread(target = relay_on_duration,
                                    args = (pid_t_temp_relay_high[sensor], round(PIDTempHigh,2), sensor,))
                                rod.start()
                            timerTemp = int(time.time()) + int(PIDTempHigh) + int(pid_t_temp_period[sensor])

                        elif (sensor_t_read_temp_c[sensor] < low) and (pid_t_temp_set_dir[sensor] > -1):

                            logging.debug("[PID T-Temperature-%s] Temperature: %.1f°C now < %.1f°C set_low", sensor, sensor_t_read_temp_c[sensor], low)
                            logging.debug("[PID T-Temperature-%s] PID = %.1f (seconds)", sensor, PIDTempLow)

                            if (PIDTempLow > 0):
                                rod = threading.Thread(target = relay_on_duration,
                                    args = (pid_t_temp_relay_low[sensor], round(PIDTempLow,2), sensor,))
                                rod.start()
                            timerTemp = int(time.time()) + int(PIDTempLow) + pid_t_temp_period[sensor]

                        else:

                            if sensor_t_read_temp_c[sensor] < low:
                                logging.debug("[PID T-Temperature-%s] %.1f°C now <= %.1f°C low, wait %s seconds", sensor, sensor_t_read_temp_c[sensor], low, pid_t_temp_period[sensor])
                            if sensor_t_read_temp_c[sensor] > high:
                                logging.debug("[PID T-Temperature-%s] %.1f°C now >= %.1f°C high, wait %s seconds", sensor, sensor_t_read_temp_c[sensor], high, pid_t_temp_period[sensor])

                            timerTemp = int(time.time()) + pid_ht_temp_period[sensor]

                    else:
                        logging.debug("[PID T-Temperature-%s] %.1f°C low <= %.1f°C now <= %.1f°C high, wait %s seconds", sensor, low, sensor_t_read_temp_c[sensor], high, pid_t_temp_period[sensor])
                        timerTemp = int(time.time()) + pid_t_temp_period[sensor]

                else:
                    logging.warning("[PID T-Temperature-%s] Could not read Temp sensor, not updating PID", sensor)

        time.sleep(0.1)
    logging.info("[PID T-Temperature-%s] Shutting Down %s", sensor, ThreadName)
    pid_t_temp_alive[sensor] = 2


# HT Sensor Temperature modulation by PID control
def ht_sensor_temperature_monitor(ThreadName, sensor):
    global pid_ht_temp_alive
    timerTemp = 0
    PIDTempHigh = 0
    PIDTempLow = 0

    logging.info("[PID HT-Temperature-%s] Starting %s", sensor, ThreadName)

    if pid_ht_temp_relay_high[sensor] != 0:
        relay_onoff(int(pid_ht_temp_relay_high[sensor]), 'off')
    if pid_ht_temp_relay_low[sensor] != 0:
        relay_onoff(int(pid_ht_temp_relay_low[sensor]), 'off')

    high = pid_ht_temp_set[sensor] + pid_ht_temp_set_buf[sensor]
    low = pid_ht_temp_set[sensor] - pid_ht_temp_set_buf[sensor]

    p_temp_high = PID(pid_ht_temp_p_high[sensor], pid_ht_temp_i_high[sensor], pid_ht_temp_d_high[sensor])
    p_temp_high.setPoint(high)

    p_temp_low = PID(pid_ht_temp_p_low[sensor], pid_ht_temp_i_low[sensor], pid_ht_temp_d_low[sensor])
    p_temp_low.setPoint(low)

    while (pid_ht_temp_alive[sensor]):
        if ( ( (pid_ht_temp_set_dir[sensor] == 0 and
            pid_ht_temp_relay_high[sensor] != 0 and
            pid_ht_temp_relay_low[sensor] != 0) or

            (pid_ht_temp_set_dir[sensor] == -1 and
            pid_ht_temp_relay_high[sensor] != 0) or

            (pid_ht_temp_set_dir[sensor] == 1 and
            pid_ht_temp_relay_low[sensor] != 0) ) and

            pid_ht_temp_or[sensor] == 0 and
            pid_ht_temp_down == 0 and
            sensor_ht_activated[sensor] == 1):

            if int(time.time()) > timerTemp:

                logging.debug("[PID HT-Temperature-%s] Reading temperature...", sensor)
                if read_ht_sensor(sensor) == 1:

                    PIDTempHigh = abs(p_temp_high.update(float(sensor_ht_read_temp_c[sensor])))
                    PIDTempLow = abs(p_temp_low.update(float(sensor_ht_read_temp_c[sensor])))

                    if (sensor_ht_read_temp_c[sensor] > high) or (sensor_ht_read_temp_c[sensor] < low):

                        if (sensor_ht_read_temp_c[sensor] > high) and (pid_ht_temp_set_dir[sensor] < 1):
                            
                            logging.debug("[PID HT-Temperature-%s] Temperature: %.1f°C now > %.1f°C set_high", sensor, sensor_ht_read_temp_c[sensor], high)
                            logging.debug("[PID HT-Temperature-%s] PID = %.1f (seconds)", sensor, PIDTempHigh)

                            if (PIDTempHigh > 0):
                                rod = threading.Thread(target = relay_on_duration,
                                    args = (pid_ht_temp_relay_high[sensor], round(PIDTempHigh,2), sensor,))
                                rod.start()

                            timerTemp = int(time.time()) + int(PIDTempHigh) + int(pid_ht_temp_period[sensor])

                        elif (sensor_ht_read_temp_c[sensor] < low) and (pid_ht_temp_set_dir[sensor] > -1):

                            logging.debug("[PID HT-Temperature-%s] Temperature: %.1f°C now < %.1f°C set_low", sensor, sensor_ht_read_temp_c[sensor], low)
                            logging.debug("[PID HT-Temperature-%s] PID = %.1f (seconds)", sensor, PIDTempLow)

                            if (PIDTempLow > 0):
                                rod = threading.Thread(target = relay_on_duration,
                                    args = (pid_ht_temp_relay_low[sensor], round(PIDTempLow,2), sensor,))
                                rod.start()

                            timerTemp = int(time.time()) + int(PIDTempLow) + pid_ht_temp_period[sensor]

                        else:

                            if sensor_ht_read_temp_c[sensor] < low:
                                logging.debug("[PID HT-Temperature-%s] %.1f°C now <= %.1f°C low, wait %s seconds", sensor, sensor_ht_read_temp_c[sensor], low, pid_ht_temp_period[sensor])
                            if sensor_ht_read_temp_c[sensor] > high:
                                logging.debug("[PID HT-Temperature-%s] %.1f°C now >= %.1f°C high, wait %s seconds", sensor, sensor_ht_read_temp_c[sensor], high, pid_ht_temp_period[sensor])

                            timerTemp = int(time.time()) + pid_ht_temp_period[sensor]

                    else:
                        logging.debug("[PID HT-Temperature-%s] %.1f°C low <= %.1f°C now <= %.1f°C high, wait %s seconds", sensor, low, sensor_ht_read_temp_c[sensor], high, pid_ht_temp_period[sensor])
                        timerTemp = int(time.time()) + pid_ht_temp_period[sensor]

                else:
                    logging.warning("[PID HT-Temperature-%s] Could not read Hum/Temp sensor, not updating PID", sensor)

        time.sleep(0.1)
    logging.info("[PID HT-Temperature-%s] Shutting Down %s", sensor, ThreadName)
    pid_ht_temp_alive[sensor] = 2


# HT Sensor ]Humidity modulation by PID control
def ht_sensor_humidity_monitor(ThreadName, sensor):
    global pid_ht_hum_alive
    timerHum = 0
    PIDHum = 0

    logging.info("[PID HT-Humidity-%s] Starting %s", sensor, ThreadName)

    if pid_ht_hum_relay_high[sensor] != 0:
        relay_onoff(int(pid_ht_hum_relay_high[sensor]), 'off')
    if pid_ht_hum_relay_low[sensor] != 0:
        relay_onoff(int(pid_ht_hum_relay_low[sensor]), 'off')

    high = pid_ht_hum_set[sensor] + pid_ht_hum_set_buf[sensor]
    low = pid_ht_hum_set[sensor] - pid_ht_hum_set_buf[sensor]

    p_hum_high = PID(pid_ht_hum_p_high[sensor], pid_ht_hum_i_high[sensor], pid_ht_hum_d_high[sensor])
    p_hum_high.setPoint(high)
    p_hum_low = PID(pid_ht_hum_p_low[sensor], pid_ht_hum_i_low[sensor], pid_ht_hum_d_low[sensor])
    p_hum_low.setPoint(low)

    while (pid_ht_hum_alive[sensor]):
        if ( ( (pid_ht_hum_set_dir[sensor] == 0 and
            pid_ht_hum_relay_high[sensor] != 0 and
            pid_ht_hum_relay_low[sensor] != 0) or 

            (pid_ht_hum_set_dir[sensor] == -1 and
            pid_ht_hum_relay_high[sensor] != 0) or

            (pid_ht_hum_set_dir[sensor] == 1 and
            pid_ht_hum_relay_low[sensor] != 0) ) and

            pid_ht_hum_or[sensor] == 0 and
            pid_ht_hum_down == 0 and
            sensor_ht_activated[sensor] == 1):

            if int(time.time()) > timerTemp:

                logging.debug("[PID HT-Humidity-%s] Reading humidity...", sensor)

                if read_ht_sensor(sensor) == 1:

                    PIDTempHigh = abs(p_temp_high.update(float(sensor_ht_read_hum[sensor])))
                    PIDTempLow = abs(p_temp_low.update(float(sensor_ht_read_hum[sensor])))

                    if (sensor_ht_read_hum[sensor] > high) or (sensor_ht_read_hum[sensor] < low):

                        if (sensor_ht_read_hum[sensor] > high) and (pid_ht_hum_set_dir[sensor] < 1):

                            logging.debug("[PID HT-Humidity-%s] Humidity: %.1f°C now > %.1f°C set_high", sensor, sensor_ht_read_hum[sensor], high)
                            logging.debug("[PID HT-Humidity-%s] PID = %.1f (seconds)", sensor, PIDTempHigh)

                            if (PIDTempHigh > 0):
                                rod = threading.Thread(target = relay_on_duration,
                                    args = (pid_ht_hum_relay_high[sensor], round(PIDTempHigh,2), sensor,))
                                rod.start()
                            timerTemp = int(time.time()) + int(PIDTempHigh) + int(pid_ht_hum_period[sensor])

                        elif (sensor_ht_read_hum[sensor] < low) and (pid_ht_hum_set_dir[sensor] > -1):

                            logging.debug("[PID HT-Humidity-%s] Humidity: %.1f°C now < %.1f°C set_low", sensor, sensor_ht_read_hum[sensor], low)
                            logging.debug("[PID HT-Humidity-%s] PID = %.1f (seconds)", sensor, PIDTempLow)

                            if (PIDTempLow > 0):
                                rod = threading.Thread(target = relay_on_duration,
                                    args = (pid_ht_hum_relay_low[sensor], round(PIDTempLow,2), sensor,))
                                rod.start()
                            timerTemp = int(time.time()) + int(PIDTempLow) + pid_ht_hum_period[sensor]

                        else:

                            if sensor_ht_read_hum_c[sensor] < low:
                                logging.debug("[PID HT-Temperature-%s] %.1f%% now <= %.1f%% low, wait %s seconds", sensor, sensor_ht_read_hum_c[sensor], low, pid_ht_hum_period[sensor])
                            if sensor_ht_read_hum_c[sensor] > high:
                                logging.debug("[PID HT-Temperature-%s] %.1f%% now >= %.1f%% high, wait %s seconds", sensor, sensor_ht_read_hum_c[sensor], high, pid_ht_hum_period[sensor])

                            timerTemp = int(time.time()) + pid_ht_hum_period[sensor]

                    else:
                        logging.debug("[PID HT-Humidity-%s] %.1f%% low < %.1f%% now < %.1f%% high, wait %s seconds", sensor, low, sensor_ht_read_hum[sensor], high, pid_ht_hum_period[sensor])
                        timerTemp = int(time.time()) + pid_ht_hum_period[sensor]

                else:
                    logging.warning("[PID HT-Humidity-%s] Could not read Hum/Temp sensor, not updating PID", sensor)

        time.sleep(0.1)
    logging.info("[PID HT-Humidity-%s] Shutting Down %s", sensor, ThreadName)
    pid_ht_hum_alive[sensor] = 2


# CO2 modulation by PID control
def co2_monitor(ThreadName, sensor):
    global pid_co2_alive
    timerCo2 = 0
    PIDCo2 = 0

    logging.info("[PID CO2-%s] Starting %s", sensor, ThreadName)

    if pid_co2_relay_high[sensor] != 0:
        relay_onoff(int(pid_co2_relay_high[sensor]), 'off')
    if pid_co2_relay_low[sensor] != 0:
        relay_onoff(int(pid_co2_relay_low[sensor]), 'off')

    high = pid_co2_set[sensor] + pid_co2_set_buf[sensor]
    low = pid_co2_set[sensor] - pid_co2_set_buf[sensor]

    p_co2_high = PID(pid_co2_p_high[sensor], pid_co2_i_high[sensor], pid_co2_d_high[sensor])
    p_co2_high.setPoint(high)
    p_co2_low = PID(pid_co2_p_low[sensor], pid_co2_i_low[sensor], pid_co2_d_low[sensor])
    p_co2_low.setPoint(low)

    while (pid_co2_alive[sensor]):
        if ( ( (pid_co2_set_dir[sensor] == 0 and
            pid_co2_relay_high[sensor] != 0 and
            pid_co2_relay_low[sensor] != 0) or

            (pid_co2_set_dir[sensor] == -1 and
            pid_co2_relay_high[sensor] != 0) or

            (pid_co2_set_dir[sensor] == 1 and
            pid_co2_relay_low[sensor] != 0) ) and

            pid_co2_or[sensor] == 0 and
            pid_co2_down == 0 and
            sensor_co2_activated[sensor] == 1):
            if int(time.time()) > timerTemp:

                logging.debug("[PID CO2-%s] Reading CO2...", sensor)

                if read_co2_sensor(sensor) == 1:

                    PIDTempHigh = abs(p_temp_high.update(float(sensor_co2_read_co2[sensor])))
                    PIDTempLow = abs(p_temp_low.update(float(sensor_co2_read_co2[sensor])))

                    if (sensor_co2_read_co2[sensor] > high) or (sensor_co2_read_co2[sensor] < low):

                        if (sensor_co2_read_co2[sensor] > high) and (pid_co2_set_dir[sensor] < 1):

                            logging.debug("[PID CO2-%s] CO2: %.1f ppm now > %.1f ppm set_high", sensor, sensor_co2_read_co2[sensor], high)
                            logging.debug("[PID CO2-%s] PID = %.1f (seconds)", sensor, PIDTempHigh)

                            if (PIDTempHigh > 0):
                                rod = threading.Thread(target = relay_on_duration,
                                    args = (pid_co2_relay_high[sensor], round(PIDTempHigh,2), sensor,))
                                rod.start()
                            timerTemp = int(time.time()) + int(PIDTempHigh) + int(pid_co2_period[sensor])

                        elif (sensor_co2_read_co2[sensor] < low) and (pid_co2_set_dir[sensor] > -1):

                            logging.debug("[PID CO2-%s] CO2: %.1f ppm now < %.1f ppm set_low", sensor, sensor_co2_read_co2[sensor], low)
                            logging.debug("[PID CO2-%s] PID = %.1f (seconds)", sensor, PIDTempLow)

                            if (PIDTempLow > 0):
                                rod = threading.Thread(target = relay_on_duration,
                                    args = (pid_co2_relay_low[sensor], round(PIDTempLow,2), sensor,))
                                rod.start()
                            timerTemp = int(time.time()) + int(PIDTempLow) + pid_co2_period[sensor]

                        else:

                            if sensor_co2_read_co2[sensor] < low:
                                logging.debug("[PID HT-Temperature-%s] %.1f ppm now <= %.1f ppm low, wait %s seconds", sensor, sensor_co2_read_co2[sensor], low, pid_co2_period[sensor])
                            if sensor_co2_read_co2[sensor] > high:
                                logging.debug("[PID HT-Temperature-%s] %.1f ppm now >= %.1f ppm high, wait %s seconds", sensor, sensor_co2_read_co2[sensor], high, pid_co2_period[sensor])

                            timerTemp = int(time.time()) + pid_co2_period[sensor]

                    else:
                        logging.debug("[PID CO2-%s] %.1f ppm low < %.1f ppm now < %.1f ppm high, wait %s seconds", sensor, low, sensor_co2_read_co2[sensor], high, pid_co2_period[sensor])
                        timerTemp = int(time.time()) + pid_co2_period[sensor]

                else:
                    logging.warning("[PID CO2-%s] Could not read CO2 sensor, not updating PID", sensor)
        time.sleep(0.1)
    logging.info("[PID CO2-%s] Shutting Down %s", sensor, ThreadName)
    pid_co2_alive[sensor] = 2


def PID_start(type, number):
    global pid_number
    pid_number = number
    if type == 'TTemp':
        global pid_t_temp_up
        pid_t_temp_up = 1
        while pid_t_temp_up:
            time.sleep(0.1)
    if type == 'HTTemp':
        global pid_ht_temp_up
        pid_ht_temp_up = 1
        while pid_ht_temp_up:
            time.sleep(0.1)
    elif type == 'HTHum':
        global pid_ht_hum_up
        pid_ht_hum_up = 1
        while pid_ht_hum_up:
            time.sleep(0.1)
    elif type == 'CO2':
        global pid_co2_up
        pid_co2_up = 1
        while pid_co2_up:
            time.sleep(0.1)
    return 1

def PID_stop(type, number):
    global pid_number
    pid_number = number
    if type == 'TTemp':
        global pid_t_temp_down
        pid_t_temp_down = 1
        while pid_t_temp_down == 1:
            time.sleep(0.1)
    if type == 'HTTemp':
        global pid_ht_temp_down
        pid_ht_temp_down = 1
        while pid_ht_temp_down == 1:
            time.sleep(0.1)
    if type == 'HTHum':
        global pid_ht_hum_down
        pid_ht_hum_down = 1
        while pid_ht_hum_down == 1:
            time.sleep(0.1)
    if type == 'CO2':
        global pid_co2_down
        pid_co2_down = 1
        while pid_co2_down == 1:
            time.sleep(0.1)
    return 1


#################################################
#                Sensor Reading                 #
#################################################

# Read the temperature and humidity from sensor
def read_t_sensor(sensor):
    global sensor_t_read_temp_c
    tempc = None
    tempc2 = None
    t_read_tries = 5

    for r in range(0, t_read_tries): # Multiple attempts to get similar consecutive readings
        logging.debug("[Read T Sensor-%s] Taking first Temperature/Humidity reading", sensor)

        # Begin HT Sensor
        if (sensor_t_device[sensor] == 'DS18B20'): device = 'DS18B20'
        else:
            device = 'Other'
            return 0

        for i in range(0, t_read_tries):
            if not pid_t_temp_alive[sensor]:
                return 0

            # Begin T Sensor
            tempc2 = read_t(sensor, device, sensor_t_pin[sensor])
            # End T Sensor

            if tempc2 != None:
                break

        if tempc2 == None:
            logging.warning("[Read T Sensor-%s] Could not read first Temp measurement! (%s tries)", sensor, ht_read_tries)
            return 0
        else:
            logging.debug("[Read T Sensor-%s] %.1f°C", sensor, tempc2)
            logging.debug("[Read T Sensor-%s] Taking second Temperature reading", sensor)

        
        for i in range(0, t_read_tries): # Multiple attempts to get first reading
            if not pid_t_temp_alive[sensor]:
                return 0
            
            # Begin T Sensor
            tempc = read_t(sensor, device, sensor_t_pin[sensor])
            # End T Sensor
           
            if tempc != None:
                break
        

        if tempc == None:
            logging.warning("[Read T Sensor-%s] Could not read Temperature!", sensor)
            return 0
        else:
            logging.debug("[Read T Sensor-%s] %.1f°C", sensor, tempc)
            logging.debug("[Read T Sensor-%s] Differences: %.1f°C", sensor, abs(tempc2-tempc))

            if abs(tempc2-tempc) > 1:
                tempc2 = tempc
                logging.debug("[Read T Sensor-%s] Successive readings > 1 difference: Rereading", sensor)
            else:
                logging.debug("[Read T Sensor-%s] Successive readings < 1 difference: keeping.", sensor)
                temperature_f = float(tempc)*9.0/5.0 + 32.0
                logging.debug("[Read T Sensor-%s] Temp: %.1f°C", sensor, tempc)
                sensor_t_read_temp_c[sensor] = tempc
                return 1

    logging.warning("[Read T Sensor-%s] Could not get two consecutive Temp measurements that were consistent.", sensor)
    return 0

# Obtain reading form T sensor
def read_t(sensor, device, pin):
    time.sleep(1) # Wait 1 seconds between sensor reads

    if not os.path.exists(lock_directory):
        os.makedirs(lock_directory)

    lock = LockFile(sensor_t_lock_path)
    while not lock.i_am_locking():
        try:
            logging.debug("[Read T Sensor-%s] Acquiring Lock: %s", sensor, lock.path)
            lock.acquire(timeout=60)    # wait up to 60 seconds
        except:
            logging.warning("[Read T Sensor-%s] Breaking Lock to Acquire: %s", sensor, lock.path)
            lock.break_lock()
            lock.acquire()

    logging.debug("[Read T Sensor-%s] Gained lock: %s", sensor, lock.path)

    # Begin DS18B20 Sensor
    if device == 'DS18B20':
        import glob
        os.system('modprobe w1-gpio')
        os.system('modprobe w1-therm')
        base_dir = '/sys/bus/w1/devices/'
        #device_folder = glob.glob(base_dir + '28*')[0]
        device_file = base_dir + '28-' + pin + '/w1_slave'
        def read_temp_raw():
            f = open(device_file, 'r')
            lines = f.readlines()
            f.close()
            return lines

        lines = read_temp_raw()
        while lines[0].strip()[-3:] != 'YES':
            time.sleep(0.2)
            lines = read_temp_raw()
        equals_pos = lines[1].find('t=')
    if equals_pos != -1:
        temp_string = lines[1][equals_pos+2:]
        tempc = float(temp_string) / 1000.0
        #temp_f = temp_c * 9.0 / 5.0 + 32.0
    else:
        return None
    # End DS18B20 Sensor

    logging.debug("[Read T Sensor-%s] Removing lock: %s", sensor, lock.path)
    lock.release()

    return tempc

# Read the temperature and humidity from sensor
def read_ht_sensor(sensor):
    global sensor_ht_read_temp_c
    global sensor_ht_read_hum
    global sensor_ht_dewpt_c
    tempc = None
    tempc2 = None
    humidity = None
    humidity2 = None
    ht_read_tries = 5

    for r in range(0, ht_read_tries): # Multiple attempts to get similar consecutive readings
        logging.debug("[Read HT Sensor-%s] Taking first Temperature/Humidity reading", sensor)

        # Begin HT Sensor
        if (sensor_ht_device[sensor] == 'DHT11'): device = Adafruit_DHT.DHT11
        elif (sensor_ht_device[sensor] == 'DHT22'): device = Adafruit_DHT.DHT22
        elif (sensor_ht_device[sensor] == 'AM2302'): device = Adafruit_DHT.AM2302
        else:
            device = 'Other'
            return 0

        for i in range(0, ht_read_tries):
            if not pid_ht_temp_alive[sensor] and not pid_ht_hum_alive[sensor]:
                return 0

            # Begin HT Sensor
            humidity2, tempc2 = read_ht(sensor, device, sensor_ht_pin[sensor])
            # End HT Sensor

            if humidity2 != None and tempc2 != None:
                break

        if humidity2 == None or tempc2 == None:
            logging.warning("[Read HT Sensor-%s] Could not read first Hum/Temp measurement! (%s tries)", sensor, ht_read_tries)
            return 0
        else:
            logging.debug("[Read HT Sensor-%s] %.1f°C, %.1f%%", sensor, tempc2, humidity2)
            logging.debug("[Read HT Sensor-%s] Taking second Temperature/Humidity reading", sensor)

        
        for i in range(0, ht_read_tries): # Multiple attempts to get first reading
            logging.debug("[TEST Sensor-%s] %s %s %s", sensor, pid_ht_temp_alive[sensor], pid_ht_hum_alive[sensor], (not pid_ht_temp_alive[sensor] and not pid_ht_hum_alive[sensor]))
            if not pid_ht_temp_alive[sensor] and not pid_ht_hum_alive[sensor]:
                return 0
            
            # Begin HT Sensor
            humidity, tempc = read_ht(sensor, device, sensor_ht_pin[sensor])
            # End HT Sensor
           
            if humidity != None and tempc != None:
                break
        

        if humidity == None or tempc == None:
            logging.warning("[Read HT Sensor-%s] Could not read Temperature/Humidity!", sensor)
            return 0
        else:
            logging.debug("[Read HT Sensor-%s] %.1f°C, %.1f%%", sensor, tempc, humidity)
            logging.debug("[Read HT Sensor-%s] Differences: %.1f°C, %.1f%%", sensor, abs(tempc2-tempc), abs(humidity2-humidity))

            if abs(tempc2-tempc) > 1 or abs(humidity2-humidity) > 1:
                tempc2 = tempc
                humidity2 = humidity
                logging.debug("[Read HT Sensor-%s] Successive readings > 1 difference: Rereading", sensor)
            else:
                logging.debug("[Read HT Sensor-%s] Successive readings < 1 difference: keeping.", sensor)
                temperature_f = float(tempc)*9.0/5.0 + 32.0
                sensor_ht_dewpt_c[sensor] = tempc - ((100-humidity) / 5)
                #sensor_ht_dewpt_f[sensor] = sensor_ht_dewpt_c[sensor] * 9 / 5 + 32
                #sensor_ht_heatindex_f = -42.379 + 2.04901523 * temperature_f + 10.14333127 * sensor_ht_read_hum - 0.22475541 * temperature_f * sensor_ht_read_hum - 6.83783 * 10**-3 * temperature_f**2 - 5.481717 * 10**-2 * sensor_ht_read_hum**2 + 1.22874 * 10**-3 * temperature_f**2 * sensor_ht_read_hum + 8.5282 * 10**-4 * temperature_f * sensor_ht_read_hum**2 - 1.99 * 10**-6 * temperature_f**2 * sensor_ht_read_hum**2
                #sensor_ht_heatindex_c[sensor] = (heatindexf - 32) * (5 / 9)
                logging.debug("[Read HT Sensor-%s] Temp: %.1f°C, Hum: %.1f%%, DP: %.1f°C", sensor, tempc, humidity, sensor_ht_dewpt_c[sensor])
                sensor_ht_read_hum[sensor] = humidity
                sensor_ht_read_temp_c[sensor] = tempc
                return 1

    logging.warning("[Read HT Sensor-%s] Could not get two consecutive Hum/Temp measurements that were consistent.", sensor)
    return 0

# Obtain reading form HT sensor
def read_ht(sensor, device, pin):
    time.sleep(2) # Wait 2 seconds between sensor reads

    if not os.path.exists(lock_directory):
        os.makedirs(lock_directory)

    lock = LockFile(sensor_ht_lock_path)
    while not lock.i_am_locking():
        try:
            logging.debug("[Read HT Sensor-%s] Acquiring Lock: %s", sensor, lock.path)
            lock.acquire(timeout=60)    # wait up to 60 seconds
        except:
            logging.warning("[Read HT Sensor-%s] Breaking Lock to Acquire: %s", sensor, lock.path)
            lock.break_lock()
            lock.acquire()

    logging.debug("[Read HT Sensor-%s] Gained lock: %s", sensor, lock.path)

    humidity, temp = Adafruit_DHT.read_retry(device, pin)

    logging.debug("[Read HT Sensor-%s] Removing lock: %s", sensor, lock.path)
    lock.release()
    return humidity, temp

# Read CO2 sensor
def read_co2_sensor(sensor):
    global sensor_co2_read_co2
    co2 = None
    co22 = None
    co2_read_tries = 5

    if (sensor_co2_device[sensor] != 'K30'):
        logging.warning("[Read CO2 Sensor-%s] Cannot read CO2 from an unknown device!", sensor)
        return 0

    for r in range(0, co2_read_tries):
        logging.debug("[Read CO2 Sensor-%s] Taking first CO2 reading", sensor)

        # Begin K30 Sensor
        if sensor_co2_device[sensor] == 'K30':
            for i in range(1, co2_read_tries): # Multiple attempts to get first reading
                if not pid_co2_alive[sensor]:
                    return 0
                co22 = read_K30(sensor)
                if co22 != None:
                    break
        # End K30 Sensor

        if co22 == None:
            logging.warning("[Read CO2 Sensor-%s] Could not read first CO2 measurement! (of %s tries)", sensor, co2_read_tries)
            break
        else:
            logging.debug("[Read CO2 Sensor-%s] CO2: %s", sensor, co22)
            logging.debug("[Read CO2 Sensor-%s] Taking second CO2 reading", sensor)

        # Begin K30 Sensor
        if sensor_co2_device[sensor] == 'K30':
            for i in range(0, co2_read_tries): # Multiple attempts to get second reading
                if not pid_co2_alive[sensor]:
                    return 0
                co2 = read_K30(sensor)
                if co2 != None:
                    break
        # End K30 Sensor

        if co2 == None:
            logging.warning("[Read CO2 Sensor-%s] Could not read second CO2 measurement! (of %s tries)", sensor, co2_read_tries)
            break
        else:
            logging.debug("[Read CO2 Sensor-%s] CO2: %s", sensor, co2)
            logging.debug("[Read CO2 Sensor-%s] Difference: %s", sensor, abs(co22 - co2))

            if abs(co22-co2) > 20:
                co22 = co2
                logging.debug("[Read CO2 Sensor-%s] Successive readings > 20 difference: Rereading", sensor)
            else:
                logging.debug("[Read CO2 Sensor-%s] Successive readings < 20 difference: keeping.", sensor)
                logging.debug("[Read CO2 Sensor-%s] CO2: %s", sensor, co2)
                sensor_co2_read_co2[sensor] = co2
                return 1

    logging.warning("[Read CO2 Sensor-%s] Could not get two consecutive CO2 measurements that were consistent.", sensor)
    return 0

# Read K30 CO2 Sensor
def read_K30(sensor):
    if not os.path.exists(lock_directory):
        os.makedirs(lock_directory)

    lock = LockFile(sensor_co2_lock_path)
    while not lock.i_am_locking():
        try:
            logging.debug("[Read CO2 Sensor-%s] Acquiring Lock: %s", sensor, lock.path)
            lock.acquire(timeout=60)    # wait up to 60 seconds
        except:
            logging.warning("[Read CO2 Sensor-%s] Breaking Lock to Acquire: %s", sensor, lock.path)
            lock.break_lock()
            lock.acquire()

    logging.debug("[Read CO2 Sensor-%s] Gained lock: %s", sensor, lock.path)

    time.sleep(2) # Ensure at least 2 seconds between sensor reads
    ser = serial.Serial("/dev/ttyAMA0", timeout=1) # Wait 1 second for reply
    ser.flushInput()
    time.sleep(1)
    ser.write("\xFE\x44\x00\x08\x02\x9F\x25")
    time.sleep(.01)
    resp = ser.read(7)
    if len(resp) == 0:
        return None
    high = ord(resp[3])
    low = ord(resp[4])
    co2 = (high*256) + low

    logging.debug("[Read CO2 Sensor-%s] Removing lock: %s", sensor, lock.path)
    lock.release()
    return co2


#################################################
#          SQLite Database Read/Write           #
#################################################

# Read variables from the SQLite database
def read_sql():
    global sensor_t_num
    global sensor_t_name
    global sensor_t_device
    global sensor_t_pin
    global sensor_t_period
    global sensor_t_activated
    global sensor_t_graph

    global pid_t_temp_relay_high
    global pid_t_temp_relay_low
    global pid_t_temp_set
    global pid_t_temp_set_dir
    global pid_t_temp_set_buf
    global pid_t_temp_or
    global pid_t_temp_period
    global pid_t_temp_p_high
    global pid_t_temp_i_high
    global pid_t_temp_d_high
    global pid_t_temp_p_low
    global pid_t_temp_i_low
    global pid_t_temp_d_low

    global sensor_ht_num
    global sensor_ht_name
    global sensor_ht_device
    global sensor_ht_pin
    global sensor_ht_period
    global sensor_ht_activated
    global sensor_ht_graph

    global pid_ht_temp_relay_high
    global pid_ht_temp_relay_low
    global pid_ht_temp_set
    global pid_ht_temp_set_dir
    global pid_ht_temp_set_buf
    global pid_ht_temp_or
    global pid_ht_temp_period
    global pid_ht_temp_p_high
    global pid_ht_temp_i_high
    global pid_ht_temp_d_high
    global pid_ht_temp_p_low
    global pid_ht_temp_i_low
    global pid_ht_temp_d_low

    global pid_ht_hum_relay_high
    global pid_ht_hum_relay_low
    global pid_ht_hum_set
    global pid_ht_hum_set_dir
    global pid_ht_hum_set_buf
    global pid_ht_hum_or
    global pid_ht_hum_period
    global pid_ht_hum_p_high
    global pid_ht_hum_i_high
    global pid_ht_hum_d_high
    global pid_ht_hum_p_low
    global pid_ht_hum_i_low
    global pid_ht_hum_d_low

    global sensor_co2_num
    global sensor_co2_name
    global sensor_co2_device
    global sensor_co2_pin
    global sensor_co2_period
    global sensor_co2_activated
    global sensor_co2_graph

    global pid_co2_relay_high
    global pid_co2_relay_low
    global pid_co2_set
    global pid_co2_set_dir
    global pid_co2_set_buf
    global pid_co2_or
    global pid_co2_period
    global pid_co2_p_high
    global pid_co2_i_high
    global pid_co2_d_high
    global pid_co2_p_low
    global pid_co2_i_low
    global pid_co2_d_low

    global relay_name
    global relay_pin
    global relay_trigger
    global relay_start_state

    global factorHumSeconds
    global factorTempSeconds
    global camera_light
    global relay_num
    global timer_num
    global timer_name
    global timer_relay
    global timer_state
    global timer_duration_on
    global timer_duration_off
    global smtp_host
    global smtp_ssl
    global smtp_port
    global smtp_user
    global smtp_pass
    global smtp_email_from
    global smtp_email_to

    verbose = 0
    # Check if all required tables exist in the SQL database
    conn = sqlite3.connect(mycodo_database)
    cur = conn.cursor()
    tables = ['Relays', 'TSensor', 'HTSensor', 'CO2Sensor', 'Timers', 'Numbers', 'SMTP']
    missing = []
    for i in range(0, len(tables)):
        query = "SELECT name FROM sqlite_master WHERE type='table' AND name='%s'" % tables[i]
        cur.execute(query)
        if cur.fetchone() == None:
            missing.append(tables[i])
    if missing != []:
        print "Missing required table(s):",
        for i in range(0, len(missing)):
            if len(missing) == 1:
                print "%s" % missing[i]
            elif len(missing) != 1 and i != len(missing)-1:
                print "%s," % missing[i],
            else:
                print "%s" % missing[i]
        print "Reinitialize database to correct."
        return 0

    # Begin setting global variables from SQL database values
    cur.execute('SELECT Id, Name, Pin, Trigger, Start_State FROM Relays')
    if verbose:
        print "Table: Relays"
    for row in cur :
        if verbose:
            print "%s %s %s %s" % (row[0], row[1], row[2], row[3])
        relay_name[row[0]] = row[1]
        relay_pin[row[0]] = row[2]
        relay_trigger[row[0]] = row[3]
        relay_start_state[row[0]] = row[4]

    cur.execute('SELECT Id, Name, Pin, Device, Period, Activated, Graph, Temp_Relay_High, Temp_Relay_Low, Temp_OR, Temp_Set, Temp_Set_Direction, Temp_Set_Buffer, Temp_Period, Temp_P_High, Temp_I_High, Temp_D_High, Temp_P_Low, Temp_I_Low, Temp_D_Low FROM TSensor')
    if verbose:
        print "Table: TSensor"
    for row in cur :
        if verbose:
            print "%s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s" % (row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9], row[10], row[11], row[12], row[13], row[14], row[15], row[16], row[17], row[18], row[19])
        sensor_t_name[row[0]] = row[1]
        sensor_t_pin[row[0]] = row[2]
        sensor_t_device[row[0]] = row[3]
        sensor_t_period[row[0]] = row[4]
        sensor_t_activated[row[0]] = row[5]
        sensor_t_graph[row[0]] = row[6]
        pid_t_temp_relay_high[row[0]] = row[7]
        pid_t_temp_relay_low[row[0]] = row[8]
        pid_t_temp_or[row[0]] = row[9]
        pid_t_temp_set[row[0]] = row[10]
        pid_t_temp_set_dir[row[0]] = row[11]
        pid_t_temp_set_buf[row[0]] = row[12]
        pid_t_temp_period[row[0]] = row[13]
        pid_t_temp_p_high[row[0]] = row[14]
        pid_t_temp_i_high[row[0]] = row[15]
        pid_t_temp_d_high[row[0]] = row[16]
        pid_t_temp_p_low[row[0]] = row[17]
        pid_t_temp_i_low[row[0]] = row[18]
        pid_t_temp_d_low[row[0]] = row[19]

    cur.execute('SELECT Id, Name, Pin, Device, Period, Activated, Graph, Temp_Relay_High, Temp_Relay_Low, Temp_OR, Temp_Set, Temp_Set_Direction, Temp_Set_Buffer, Temp_Period, Temp_P_High, Temp_I_High, Temp_D_High, Temp_P_Low, Temp_I_Low, Temp_D_Low, Hum_Relay_High, Hum_Relay_Low, Hum_OR, Hum_Set, Hum_Set_Direction, Hum_Set_Buffer, Hum_Period, Hum_P_High, Hum_I_High, Hum_D_High, Hum_P_Low, Hum_I_Low, Hum_D_low FROM HTSensor')
    if verbose:
        print "Table: HTSensor"
    for row in cur :
        if verbose:
            print "%s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s" % (row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9], row[10], row[11], row[12], row[13], row[14], row[15], row[16], row[17], row[18], row[19], row[20], row[21], row[22], row[23], row[24], row[25], row[26], row[27], row[28], row[29], row[30], row[31], row[32])
        sensor_ht_name[row[0]] = row[1]
        sensor_ht_pin[row[0]] = row[2]
        sensor_ht_device[row[0]] = row[3]
        sensor_ht_period[row[0]] = row[4]
        sensor_ht_activated[row[0]] = row[5]
        sensor_ht_graph[row[0]] = row[6]
        pid_ht_temp_relay_high[row[0]] = row[7]
        pid_ht_temp_relay_low[row[0]] = row[8]
        pid_ht_temp_or[row[0]] = row[9]
        pid_ht_temp_set[row[0]] = row[10]
        pid_ht_temp_set_dir[row[0]] = row[11]
        pid_ht_temp_set_buf[row[0]] = row[12]
        pid_ht_temp_period[row[0]] = row[13]
        pid_ht_temp_p_high[row[0]] = row[14]
        pid_ht_temp_i_high[row[0]] = row[15]
        pid_ht_temp_d_high[row[0]] = row[16]
        pid_ht_temp_p_low[row[0]] = row[17]
        pid_ht_temp_i_low[row[0]] = row[18]
        pid_ht_temp_d_low[row[0]] = row[19]
        pid_ht_hum_relay_high[row[0]] = row[20]
        pid_ht_hum_relay_low[row[0]] = row[21]
        pid_ht_hum_or[row[0]] = row[22]
        pid_ht_hum_set[row[0]] = row[23]
        pid_ht_hum_set_dir[row[0]] = row[24]
        pid_ht_hum_set_buf[row[0]] = row[25]
        pid_ht_hum_period[row[0]] = row[26]
        pid_ht_hum_p_high[row[0]] = row[27]
        pid_ht_hum_i_high[row[0]] = row[28]
        pid_ht_hum_d_high[row[0]] = row[29]
        pid_ht_hum_p_low[row[0]] = row[30]
        pid_ht_hum_i_low[row[0]] = row[31]
        pid_ht_hum_d_low[row[0]] = row[32]

    cur.execute('SELECT Id, Name, Pin, Device, Period, Activated, Graph, CO2_Relay_High, CO2_Relay_Low, CO2_OR, CO2_Set, CO2_Set_Direction, CO2_Set_Buffer, CO2_Period, CO2_P_High, CO2_I_High, CO2_D_High, CO2_P_Low, CO2_I_Low, CO2_D_Low FROM CO2Sensor ')
    if verbose:
        print "Table: CO2Sensor "
    for row in cur :
        if verbose:
            print "%s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s" % (
                row[0], row[1], row[2], row[3], row[4], row[5], row[6],
                row[7], row[8], row[9], row[10], row[11], row[12], row[13], row[14], row[15], row[16], row[17], row[18], row[19])
        sensor_co2_name[row[0]] = row[1]
        sensor_co2_pin[row[0]] = row[2]
        sensor_co2_device[row[0]] = row[3]
        sensor_co2_period[row[0]] = row[4]
        sensor_co2_activated[row[0]] = row[5]
        sensor_co2_graph[row[0]] = row[6]
        pid_co2_relay_high[row[0]] = row[7]
        pid_co2_relay_low[row[0]] = row[8]
        pid_co2_or[row[0]] = row[9]
        pid_co2_set[row[0]] = row[10]
        pid_co2_set_dir[row[0]] = row[11]
        pid_co2_set_buf[row[0]] = row[12]
        pid_co2_period[row[0]] = row[13]
        pid_co2_p_high[row[0]] = row[14]
        pid_co2_i_high[row[0]] = row[15]
        pid_co2_d_high[row[0]] = row[16]
        pid_co2_p_low[row[0]] = row[17]
        pid_co2_i_low[row[0]] = row[18]
        pid_co2_d_low[row[0]] = row[19]

    cur.execute('SELECT Id, Name, Relay, State, DurationOn, DurationOff FROM Timers ')
    if verbose:
        print "Table: Timers "
    for row in cur :
        if verbose:
            print "%s %s %s %s %s %s" % (
                row[0], row[1], row[2], row[3], row[4], row[5])
        timer_name[row[0]] = row[1]
        timer_relay[row[0]] = row[2]
        timer_state[row[0]] = row[3]
        timer_duration_on[row[0]] = row[4]
        timer_duration_off[row[0]] = row[5]

    cur.execute('SELECT Relays, TSensors, HTSensors, CO2Sensors, Timers FROM Numbers ')
    if verbose:
        print "Table: Numbers "
    for row in cur :
        if verbose:
            print "%s %s %s %s %s" % (
                row[0], row[1], row[2], row[3], row[4])
        relay_num = row[0]
        sensor_t_num = row[1]
        sensor_ht_num = row[2]
        sensor_co2_num = row[3]
        timer_num = row[4]

    cur.execute('SELECT Host, SSL, Port, User, Pass, Email_From, Email_To FROM SMTP ')
    if verbose:
        print "Table: SMTP "
    for row in cur :
        if verbose:
            print "%s %s %s %s %s %s %s" % (
                row[0], row[1], row[2], row[3], row[4], row[5], row[6])
        smtp_host = row[0]
        smtp_ssl = row[1]
        smtp_port = row[2]
        smtp_user = row[3]
        smtp_pass = row[4]
        smtp_email_from = row[5]
        smtp_email_to = row[6]

    cur.close()

# Write variables to the SQLite database
def write_sql():
    if not os.path.exists(lock_directory):
        os.makedirs(lock_directory)

    lock = LockFile(sql_lock_path)

    while not lock.i_am_locking():
        try:
            logging.debug("[Write SQL] Waiting, Acquiring Lock: %s", lock.path)
            lock.acquire(timeout=60)    # wait up to 60 seconds
        except:
            logging.warning("[Write SQL] Breaking Lock to Acquire: %s", lock.path)
            lock.break_lock()
            lock.acquire()

    logging.debug("[Write SQL] Gained lock: %s", lock.path)
    logging.debug("[Write SQL] Writing SQL Database %s", mycodo_database)

    conn = sqlite3.connect(mycodo_database)
    cur = conn.cursor()
    cur.execute('DROP TABLE IF EXISTS Relays ')
    cur.execute('DROP TABLE IF EXISTS TSensor ')
    cur.execute('DROP TABLE IF EXISTS HTSensor ')
    cur.execute('DROP TABLE IF EXISTS CO2Sensor ')
    cur.execute('DROP TABLE IF EXISTS Timers ')
    cur.execute('DROP TABLE IF EXISTS Numbers ')
    cur.execute('DROP TABLE IF EXISTS SMTP ')
    cur.execute("CREATE TABLE Relays (Id INT, Name TEXT, Pin INT, Trigger INT)")
    cur.execute("CREATE TABLE TSensor (Id INT, Name TEXT, Pin INT, Device TEXT, Period INT, Activated INT, Graph INT, Temp_Relay INT, Temp_OR INT, Temp_Set REAL, Temp_Period INT, Temp_P REAL, Temp_I REAL, Temp_D REAL)")
    cur.execute("CREATE TABLE HTSensor (Id INT, Name TEXT, Pin INT, Device TEXT, Period INT, Activated INT, Graph INT, Temp_Relay INT, Temp_OR INT, Temp_Set REAL, Temp_Period INT, Temp_P REAL, Temp_I REAL, Temp_D REAL, Hum_Relay INT, Hum_OR INT, Hum_Set REAL, Hum_Period INT, Hum_P REAL, Hum_I REAL, Hum_D REAL)")
    cur.execute("CREATE TABLE CO2Sensor (Id INT, Name TEXT, Pin INT, Device TEXT, Period INT, Activated INT, Graph INT, CO2_Relay INT, CO2_OR INT, CO2_Set INT, CO2_Period INT, CO2_P REAL, CO2_I REAL, CO2_D REAL)")
    cur.execute("CREATE TABLE Timers (Id INT, Name TEXT, Relay INT, State INT, DurationOn INT, DurationOff INT)")
    cur.execute("CREATE TABLE Numbers (Relays INT, TSensors INT, HTSensors INT, CO2Sensors INT, Timers INT)")
    cur.execute("CREATE TABLE SMTP (Host TEXT, SSL INT, Port INT, User TEXT, Pass TEXT, Email_From TEXT, Email_To TEXT)")
    for i in range(1, 9):
        query = "INSERT INTO Relays VALUES(%d, '%s', %s, %s)" % (i, relay_name[i], relay_pin[i], relay_trigger[i])
        cur.execute(query)
    for i in range(1, 5):
        query = "INSERT INTO TSensor VALUES(%d, '%s', %s, '%s', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)" % (i, sensor_t_name[i], sensor_t_pin[i], sensor_t_device[i], sensor_t_period[i], sensor_t_activated[i], sensor_t_graph[i], pid_t_temp_relay[i], pid_t_temp_or[i], pid_t_temp_set[i], pid_t_temp_period[i], pid_t_temp_p[i], pid_t_temp_i[i], pid_t_temp_d[i])
        cur.execute(query)
    for i in range(1, 5):
        query = "INSERT INTO HTSensor VALUES(%d, '%s', %s, '%s', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)" % (i, sensor_ht_name[i], sensor_ht_pin[i], sensor_ht_device[i], sensor_ht_period[i], sensor_ht_activated[i], sensor_ht_graph[i], pid_ht_temp_relay[i], pid_ht_temp_or[i], pid_ht_temp_set[i], pid_ht_temp_period[i], pid_ht_temp_p[i], pid_ht_temp_i[i], pid_ht_temp_d[i], pid_ht_hum_relay[i], pid_ht_hum_or[i], pid_ht_hum_set[i], pid_ht_hum_period[i], pid_ht_hum_p[i], pid_ht_hum_i[i], pid_ht_hum_d[i])
        cur.execute(query)
    for i in range(1, 5):
        query = "INSERT INTO CO2Sensor VALUES(%d, '%s', %s, '%s', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)" % (i, sensor_co2_name[i], sensor_co2_pin[i], sensor_co2_device[i], sensor_co2_period[i], sensor_co2_activated[i], sensor_co2_graph[i], pid_co2_relay[i], pid_co2_or[i], pid_co2_set[i], pid_co2_period[i], pid_co2_p[i], pid_co2_i[i], pid_co2_d[i])
        cur.execute(query)
    for i in range(1, 9):
        query = "INSERT INTO Timers VALUES(%d, '%s', %s, %s, %s, %s)" % (i, timer_name[i], timer_state[i], timer_relay[i], timer_duration_on[i], timer_duration_off[i])
        cur.execute(query)
    query = "INSERT INTO Numbers VALUES(%s, %s, %s, %s, %s)" % (relay_num, sensor_t_num, sensor_ht_num, sensor_co2_num, timer_num)
    cur.execute(query)
    query = "INSERT INTO SMTP VALUES('%s', %s, %s, '%s', '%s', '%s', '%s')" % (smtp_host, smtp_ssl, smtp_port, smtp_user, smtp_pass, smtp_email_from, smtp_email_to)
    cur.execute(query)
    conn.commit()
    cur.close()

    logging.debug("[Write SQL] Removing lock: %s", lock.path)
    lock.release()


#################################################
#               GPIO Manipulation               #
#################################################

# Initialize all relay GPIO pins
def initialize_all_gpio():
    logging.info("[GPIO Initialize] Set GPIO mode to BCM numbering, all as output")

    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    # Initialize GPIOs from all 8 relays
    for i in range(1, 9):
        if relay_pin[i] > 0:
            GPIO.setup(relay_pin[i], GPIO.OUT)

    Relays_Off()

# Initialize specified GPIO pin
def initialize_gpio(relay):
    logging.info("[GPIO Initialize] Set GPIO mode to BCM numbering, pin %s as output", relay_pin[relay])

    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    #initialize one GPIO
    if relay_pin[relay] > 0:
        GPIO.setup(relay_pin[relay], GPIO.OUT)
        relay_onoff(relay, 'off')

# Turn Relays Off
def Relays_Off():
    for i in range(1, 9):
        if relay_pin[i] > 0:
            if relay_trigger[i] == 0:
                GPIO.output(relay_pin[i], 1)
            else: GPIO.output(relay_pin[i], 0)

# Read states (HIGH/LOW) of GPIO pins
def gpio_read():
    for x in range(1, 9):
        if GPIO.input(relay_pin[x]): logging.info("[GPIO Read] Relay %s: OFF", x)
        else: logging.info("[GPIO Read] Relay %s: ON", x)

# Change GPIO (Select) to a specific state (State)
def gpio_change(relay, State):
    if relay == 0:
        logging.warning("[GPIO Write] 0 is an invalid relay number. Check your configuration.")
    else:
        logging.debug("[GPIO Write] Setting relay %s (%s) to %s (was %s)",
            relay, relay_name[relay],
            State, GPIO.input(relay_pin[relay]))
        GPIO.output(relay_pin[relay], State)

# Turn relay on or off (accounts for trigger)
def relay_onoff(relay, state):
    if (relay_trigger[relay] == 1 and state == 'on'):
        gpio_change(relay, 1)
    elif (relay_trigger[relay] == 1 and state == 'off'):
        gpio_change(relay, 0)
    elif (relay_trigger[relay] == 0 and state == 'on'):
        gpio_change(relay, 0)
    elif (relay_trigger[relay] == 0 and state == 'off'):
        gpio_change(relay, 1)

# Set relay on for a specific duration
def relay_on_duration(relay, seconds, sensor):
    if (relay_trigger[relay] == 0 and GPIO.input(relay_pin[relay]) == 0) or (
            relay_trigger[relay] == 1 and GPIO.input(relay_pin[relay]) == 1):
        logging.warning("[Relay Duration] Relay %s (%s) is already On. Turning off in %s seconds.",
            relay, relay_name[relay], seconds)
    else:
        logging.debug("[Relay Duration] Relay %s (%s) ON for %s seconds",
            relay, relay_name[relay], round(seconds, 1))

    GPIO.output(relay_pin[relay], relay_trigger[relay]) # Turn relay on
    timer_on = int(time.time()) + seconds
    mycodoLog.write_relay_log(relay, seconds, sensor)

    while (client_que != 'TerminateServer' and timer_on > int(time.time())):
        time.sleep(0.1)

    # Turn relay off
    if relay_trigger[relay] == 0: GPIO.output(relay_pin[relay], 1)
    else: GPIO.output(relay_pin[relay], 0)

    logging.debug("[Relay Duration] Relay %s (%s) Off (was On for %s sec)",
        relay, relay_name[relay], round(seconds, 1))
    return 1

#################################################
#                 Email Notify                  #
#################################################

# Email if temperature or humidity is outside of critical range (Not yet implemented)
def email(message):
    if (smtp_ssl):
        server = smtplib.SMTP_SSL(smtp_host, smtp_port)
        server.ehlo()
    else:
        server = smtplib.SMTP(smtp_host, smtp_port)
        server.ehlo()
        server.starttls()

    server.ehlo
    server.login(smtp_user, smtp_pass)

    # Body of email
    # message = "Critical warning!"

    msg = MIMEText(message)
    msg['Subject'] = "Critical warning!"
    msg['From'] = "Raspberry Pi"
    msg['To'] = smtp_email_from
    server.sendmail(smtp_email_from, smtp_email_to, msg.as_string())
    server.quit()


#################################################
#                 Miscellaneous                 #
#################################################

# Check if string represents an integer value
def represents_int(s):
    try:
        int(s)
        return True
    except ValueError:
        return False

# Check if string represents a float value
def represents_float(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

# Timestamp format used in sensor and relay logs
def timestamp():
    return datetime.datetime.fromtimestamp(time.time()).strftime('%Y %m %d %H %M %S')


#################################################
#                 Main Program                  #
#################################################
def main():
    if not os.geteuid() == 0:
        print "\nScript must be executed as root\n"
        logging.warning("Must be executed as root.")
        usage()
        sys.exit("Must be executed as root")

    if not os.path.exists(lock_directory):
        os.makedirs(lock_directory)

    runlock = LockFile(daemon_lock_path)

    while not runlock.i_am_locking():
        try:
            runlock.acquire(timeout=1)
        except:
            logging.warning("Lock file present: %s. Delete it or run 'sudo service mycodo restart'", runlock.path)
            error = "Error: Lock file present: %s" % runlock.path
            print error
            sys.exit(error)

    read_sql()
    initialize_all_gpio()
    menu()
    runlock.release()

try:
    main()
except:
    logging.exception(1)
