# coding=utf-8
import logging
import time

from mycodo.inputs.base_input import AbstractInput
from mycodo.inputs.sensorutils import convert_units
from mycodo.inputs.sensorutils import is_device

# Input information
INPUT_INFORMATION = {
    'input_name_unique': 'MH_Z19',
    'input_manufacturer': 'Winsen',
    'input_name': 'MH-Z19',
    'measurements_name': 'CO2',
    'measurements_list': ['co2'],
    'options_enabled': ['uart_location', 'uart_baud_rate', 'period',  'convert_unit', 'pre_output'],
    'options_disabled': ['interface'],

    'interfaces': ['UART'],
    'uart_location': '/dev/ttyAMA0',
    'uart_baud_rate': 9600
}


class InputModule(AbstractInput):
    """ A sensor support class that monitors the MH-Z19's CO2 concentration """

    def __init__(self, input_dev, testing=False):
        super(InputModule, self).__init__()
        self.logger = logging.getLogger("mycodo.inputs.mh_z19")
        self._co2 = None

        if not testing:
            import serial
            self.logger = logging.getLogger(
                "mycodo.inputs.mhz19_{id}".format(id=input_dev.id))
            self.uart_location = input_dev.uart_location
            self.baud_rate = input_dev.baud_rate
            self.convert_to_unit = input_dev.convert_to_unit
            # Check if device is valid
            self.serial_device = is_device(self.uart_location)
            if self.serial_device:
                try:
                    self.ser = serial.Serial(self.serial_device,
                                             baudrate=self.baud_rate,
                                             timeout=1)
                    self.abcoff()
                    self.set_measure_range(5000)
                except serial.SerialException:
                    self.logger.exception('Opening serial')
            else:
                self.logger.error(
                    'Could not open "{dev}". '
                    'Check the device location is correct.'.format(
                        dev=self.uart_location))

    def __repr__(self):
        """  Representation of object """
        return "<{cls}(co2={co2})>".format(
            cls=type(self).__name__,
            co2="{0:.2f}".format(self._co2))

    def __str__(self):
        """ Return CO2 information """
        return "CO2: {co2}".format(co2="{0:.2f}".format(self._co2))

    def __iter__(self):  # must return an iterator
        """ MH-Z19 iterates through live CO2 readings """
        return self

    def next(self):
        """ Get next CO2 reading """
        if self.read():  # raised an error
            raise StopIteration  # required
        return dict(co2=float('{0:.2f}'.format(self._co2)))

    @property
    def co2(self):
        """ CO2 concentration in ppmv """
        if self._co2 is None:  # update if needed
            self.read()
        return self._co2

    def get_measurement(self):
        """ Gets the MH-Z19's CO2 concentration in ppmv via UART"""
        self._co2 = None
        co2 = None

        if not self.serial_device:  # Don't measure if device isn't validated
            return None

        self.ser.flushInput()
        time.sleep(1)
        self.ser.write(bytearray([0xff, 0x01, 0x86, 0x00, 0x00, 0x00, 0x00, 0x00, 0x79]))
        time.sleep(.01)
        resp = self.ser.read(9)
        if len(resp) != 0:
            high = resp[2]
            low = resp[3]
            co2 = (high * 256) + low

        co2 = convert_units(
            'co2', 'ppm', self.convert_to_unit, co2)

        return co2

    def read(self):
        """
        Takes a reading from the MH-Z19 and updates the self._co2 value

        :returns: None on success or 1 on error
        """
        if self.acquiring_measurement:
            self.logger.error("Attempting to acquire a measurement when a"
                              " measurement is already being acquired.")
            return 1
        try:
            self.acquiring_measurement = True
            self._co2 = self.get_measurement()
            if self._co2 is not None:
                return  # success - no errors
        except Exception as e:
            self.logger.error(
                "{cls} raised an exception when taking a reading: "
                "{err}".format(cls=type(self).__name__, err=e))
        finally:
            self.acquiring_measurement = False
        return 1

    def abcoff(self):
        """
        Turns off Automatic Baseline Correction feature of "B" type sensor.
        Should be run once at the beginning of every activation.
        """
        self.ser.write(bytearray([0xff, 0x01, 0x79, 0x00, 0x00, 0x00, 0x00, 0x00, 0x86]))

    def abcon(self):
        """
        Turns on Automatic Baseline Correction feature of "B" type sensor.
        """
        self.ser.write(bytearray([0xff, 0x01, 0x79, 0xa0, 0x00, 0x00, 0x00, 0x00, 0xe6]))

    def set_measure_range(self, measure_range):
        """
        Sets the measurement range. Options are: 1000, 2000, 3000, or 5000 (ppmv)
        :param measure_range: int
        :return: None
        """
        if measure_range == 1000:
            self.ser.write(bytearray([0xff, 0x01, 0x99, 0x00, 0x00, 0x00, 0x03, 0xe8, 0x7b]))
        elif measure_range == 2000:
            self.ser.write(bytearray([0xff, 0x01, 0x99, 0x00, 0x00, 0x00, 0x07, 0xd0, 0x8f]))
        elif measure_range == 3000:
            self.ser.write(bytearray([0xff, 0x01, 0x99, 0x00, 0x00, 0x00, 0x0b, 0xb8, 0xa3]))
        elif measure_range == 5000:
            self.ser.write(bytearray([0xff, 0x01, 0x99, 0x00, 0x00, 0x00, 0x13, 0x88, 0xcb]))
        else:
            return "out of range"
