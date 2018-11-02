# coding=utf-8
import logging
import time

from mycodo.inputs.base_input import AbstractInput
from mycodo.utils.calibration import AtlasScientificCommand
from mycodo.utils.influx import read_last_influxdb
from mycodo.utils.system_pi import str_is_float

# Measurements
measurements = {
    'ion_concentration': {
        'pH': {0: {}}
    }
}

# Input information
INPUT_INFORMATION = {
    'input_name_unique': 'ATLAS_PH',
    'input_manufacturer': 'Atlas',
    'input_name': 'Atlas pH',
    'measurements_name': 'Ion Concentration',
    'measurements_dict': measurements,

    'options_enabled': [
        'i2c_location',
        'uart_location',
        'measurements_convert',
        'period',
        'pre_output'
    ],
    'options_disabled': ['interface'],

    'interfaces': ['I2C', 'UART'],
    'i2c_location': ['0x66'],
    'i2c_address_editable': True,
    'uart_location': '/dev/ttyAMA0'
}


class InputModule(AbstractInput):
    """A sensor support class that monitors the Atlas Scientific sensor pH"""

    def __init__(self, input_dev, testing=False):
        super(InputModule, self).__init__()
        self.logger = logging.getLogger("mycodo.inputs.atlas_ph")
        self._measurements = None
        self.atlas_sensor_uart = None
        self.atlas_sensor_i2c = None
        self.uart_location = None
        self.i2c_address = None
        self.i2c_bus = None

        if not testing:
            self.logger = logging.getLogger(
                "mycodo.inputs.atlas_ph_{id}".format(id=input_dev.unique_id.split('-')[0]))

            self.input_dev = input_dev
            self.interface = input_dev.interface
            self.calibrate_sensor_measure = input_dev.calibrate_sensor_measure
            try:
                self.initialize_sensor()
            except Exception:
                self.logger.exception("Exception while initializing sensor")

    def initialize_sensor(self):
        from mycodo.devices.atlas_scientific_i2c import AtlasScientificI2C
        from mycodo.devices.atlas_scientific_uart import AtlasScientificUART
        if self.interface == 'UART':
            self.uart_location = self.input_dev.uart_location
            self.logger = logging.getLogger(
                "mycodo.inputs.atlas_ph_{uart}".format(
                    uart=self.uart_location))
            self.atlas_sensor_uart = AtlasScientificUART(self.uart_location)
        elif self.interface == 'I2C':
            self.i2c_address = int(str(self.input_dev.i2c_location), 16)
            self.logger = logging.getLogger(
                "mycodo.inputs.atlas_ph_{bus}_{add}".format(
                    bus=self.i2c_bus, add=self.i2c_address))
            self.i2c_bus = self.input_dev.i2c_bus
            self.atlas_sensor_i2c = AtlasScientificI2C(
                i2c_address=self.i2c_address, i2c_bus=self.i2c_bus)

    def get_measurement(self):
        """ Gets the sensor's pH measurement via UART/I2C """
        self._measurements = None
        ph = None

        return_dict = {
            'ion_concentration': {
                'pH': {}
            }
        }

        # Calibrate the pH measurement based on a temperature measurement
        if (self.calibrate_sensor_measure and
                ',' in self.calibrate_sensor_measure):
            self.logger.debug("pH sensor set to calibrate temperature")

            device_id = self.calibrate_sensor_measure.split(',')[0]
            measurement = self.calibrate_sensor_measure.split(',')[1]
            last_measurement = read_last_influxdb(
                device_id, measurement, duration_sec=300)
            if last_measurement:
                self.logger.debug(
                    "Latest temperature used to calibrate: {temp}".format(
                        temp=last_measurement[1]))

                atlas_command = AtlasScientificCommand(self.input_dev)
                ret_value, ret_msg = atlas_command.calibrate(
                    'temperature', temperature=last_measurement[1])
                time.sleep(0.5)

                self.logger.debug(
                    "Calibration returned: {val}, {msg}".format(
                        val=ret_value, msg=ret_msg))

        # Read sensor via UART
        if self.interface == 'UART':
            if self.atlas_sensor_uart.setup:
                lines = self.atlas_sensor_uart.query('R')
                if lines:
                    self.logger.debug(
                        "All Lines: {lines}".format(lines=lines))

                    # 'check probe' indicates an error reading the sensor
                    if 'check probe' in lines:
                        self.logger.error(
                            '"check probe" returned from sensor')
                    # if a string resembling a float value is returned, this
                    # is out measurement value
                    elif str_is_float(lines[0]):
                        ph = float(lines[0])
                        self.logger.debug(
                            'Value[0] is float: {val}'.format(val=ph))
                    else:
                        # During calibration, the sensor is put into
                        # continuous mode, which causes a return of several
                        # values in one string. If the return value does
                        # not represent a float value, it is likely to be a
                        # string of several values. This parses and returns
                        # the first value.
                        if str_is_float(lines[0].split(b'\r')[0]):
                            ph = lines[0].split(b'\r')[0]
                        # Lastly, this is called if the return value cannot
                        # be determined. Watchthe output in the GUI to see
                        # what it is.
                        else:
                            ph = lines[0]
                            self.logger.error(
                                'Value[0] is not float or "check probe": '
                                '{val}'.format(val=ph))
            else:
                self.logger.error('UART device is not set up.'
                                  'Check the log for errors.')

        # Read sensor via I2C
        elif self.interface == 'I2C':
            if self.atlas_sensor_i2c.setup:
                ph_status, ph_str = self.atlas_sensor_i2c.query('R')
                if ph_status == 'error':
                    self.logger.error(
                        "Sensor read unsuccessful: {err}".format(
                            err=ph_str))
                elif ph_status == 'success':
                    ph = float(ph_str)
            else:
                self.logger.error(
                    'I2C device is not set up. Check the log for errors.')

        return_dict['ion_concentration']['pH'][0] = ph

        if return_dict['ion_concentration']['pH'][0] is not None:
            return return_dict
