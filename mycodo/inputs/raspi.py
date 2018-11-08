# coding=utf-8
import logging
import subprocess

from mycodo.databases.models import InputMeasurements
from mycodo.inputs.base_input import AbstractInput
from mycodo.utils.database import db_retrieve_table_daemon

# Measurements
measurements = {
    'temperature': {
        'C': {
            0: {'name': 'CPU'},
            1: {'name': 'GPU'}
        }
    }
}

# Input information
INPUT_INFORMATION = {
    'input_name_unique': 'RPi',
    'input_manufacturer': 'Raspberry Pi',
    'input_name': 'RPi CPU Temp',
    'measurements_name': 'Temperature',
    'measurements_dict': measurements,

    'options_enabled': [
        'measurements_convert',
        'period'
    ],
    'options_disabled': ['interface'],

    'interfaces': ['RPi']
}


class InputModule(AbstractInput):
    """ A sensor support class that monitors the raspberry pi's cpu temperature """

    def __init__(self, input_dev, testing=False):
        super(InputModule, self).__init__()
        self.logger = logging.getLogger("mycodo.inputs.raspi")
        self._measurements = None

        if not testing:
            self.logger = logging.getLogger(
                "mycodo.raspi_{id}".format(id=input_dev.unique_id.split('-')[0]))

            self.input_measurements = db_retrieve_table_daemon(
                InputMeasurements).filter(
                    InputMeasurements.input_id == input_dev.unique_id)

    def get_measurement(self):
        """ Gets the Raspberry pi's temperature in Celsius by reading the temp file and div by 1000 """
        # import psutil
        # import resource
        # open_files_count = 0
        # for proc in psutil.process_iter():
        #     if proc.open_files():
        #         open_files_count += 1
        # self.logger.info("Open files: {of}".format(of=open_files_count))
        # soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
        # self.logger.info("LIMIT: Soft: {sft}, Hard: {hrd}".format(sft=soft, hrd=hard))

        return_dict = {
            'temperature': {
                'C': {}
            }
        }

        if self.is_enabled('temperature', 'C', 0):
            # CPU temperature
            with open('/sys/class/thermal/thermal_zone0/temp') as cpu_temp_file:
                temperature_cpu = float(cpu_temp_file.read()) / 1000
                return_dict['temperature']['C'][0] = temperature_cpu

        if self.is_enabled('temperature', 'C', 1):
            # GPU temperature
            temperature_gpu = subprocess.check_output(
                ('/opt/vc/bin/vcgencmd', 'measure_temp'))
            return_dict['temperature']['C'][1] = float(
                temperature_gpu.split('=')[1].split("'")[0])

        return return_dict
