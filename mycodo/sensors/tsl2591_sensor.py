# coding=utf-8
import logging
import tsl2591
from .base_sensor import AbstractSensor


class TSL2591Sensor(AbstractSensor):
    """ A sensor support class that monitors the TSL2591's lux """

    def __init__(self, address, bus):
        super(TSL2591Sensor, self).__init__()
        self.logger = logging.getLogger(
            "mycodo.sensors.tsl2591_{bus}_{add}".format(bus=bus, add=address))
        self.i2c_address = address
        self.i2c_bus = bus
        self._lux = 0.0

    def __repr__(self):
        """  Representation of object """
        return "<{cls}(lux={lux})>".format(cls=type(self).__name__,
                                           lux="{0:.2f}".format(self._lux))

    def __str__(self):
        """ Return lux information """
        return "Lux: {lux}".format(lux="{0:.2f}".format(self._lux))

    def __iter__(self):  # must return an iterator
        """ TSL2591Sensor iterates through live lux readings """
        return self

    def next(self):
        """ Get next lux reading """
        if self.read():  # raised an error
            raise StopIteration  # required
        return dict(lux=float('{0:.2f}'.format(self._lux)))

    def info(self):
        conditions_measured = [
            ("Lux", "lux", "float", "0.00", self._lux, self.lux)
        ]
        return conditions_measured

    @property
    def lux(self):
        """ TSL2591 luminosity in lux """
        if not self._lux:  # update if needed
            self.read()
        return self._lux

    def get_measurement(self):
        """ Gets the TSL2591's lux """
        tsl = tsl2591.Tsl2591(i2c_bus=self.i2c_bus, sensor_address=self.i2c_address)
        full, ir = tsl.get_full_luminosity()  # read raw values (full spectrum and ir spectrum)
        lux = tsl.calculate_lux(full, ir)  # convert raw values to lux
        return lux

    def read(self):
        """
        Takes a reading from the TSL2591 and updates the self._lux value

        :returns: None on success or 1 on error
        """
        try:
            self._lux = self.get_measurement()
            return  # success - no errors
        except Exception as e:
            self.logger.error("{cls} raised an exception when taking a reading: "
                              "{err}".format(cls=type(self).__name__, err=e))
        return 1
