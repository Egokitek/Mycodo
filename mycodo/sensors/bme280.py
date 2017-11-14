# coding=utf-8
# Copyright (c) 2014 Adafruit Industries
# Author: Tony DiCola
# Based on the BMP280 driver with BME280 changes provided by
# David J Taylor, Edinburgh (www.satsignal.eu)
import logging
from Adafruit_BME280 import BME280
from sensorutils import dewpoint
from sensorutils import altitude
from .base_sensor import AbstractSensor


class BME280Sensor(AbstractSensor):
    """
    A sensor support class that measures the BME280's humidity, temperature,
    and pressure, them calculates the altitude and dew point

    """

    def __init__(self, address, bus):
        super(BME280Sensor, self).__init__()
        self.logger = logging.getLogger("mycodo.sensors.bme280")
        self.I2C_address = address
        self.I2C_bus_number = bus
        self._altitude = 0.0
        self._dew_point = 0.0
        self._humidity = 0.0
        self._pressure = 0
        self._temperature = 0.0
        self.sensor = BME280(address=address, busnum=bus)

    def __repr__(self):
        """  Representation of object """
        return "<{cls}(altitude={alt})(dewpoint={dpt})" \
               "(humidity={hum})(temperature={temp})>".format(
                cls=type(self).__name__,
                alt="{0:.2f}".format(self._altitude),
                dpt="{0:.2f}".format(self._dew_point),
                hum="{0:.2f}".format(self._humidity),
                press=self._pressure,
                temp="{0:.2f}".format(self._temperature))

    def __str__(self):
        """ Return measurement information """
        return "Altitude: {alt}, Dew Point: {dpt}, " \
               "Humidity: {hum}, Pressure: {press}, " \
               "Temperature: {temp}".format(
                alt="{0:.2f}".format(self._altitude),
                dpt="{0:.2f}".format(self._dew_point),
                hum="{0:.2f}".format(self._humidity),
                press=self._pressure,
                temp="{0:.2f}".format(self._temperature))

    def __iter__(self):  # must return an iterator
        """ SensorClass iterates through live measurement readings """
        return self

    def next(self):
        """ Get next measurement reading """
        if self.read():  # raised an error
            raise StopIteration  # required
        return dict(altitude=float('{0:.2f}'.format(self._altitude)),
                    dewpoint=float('{0:.2f}'.format(self._dew_point)),
                    humidity=float('{0:.2f}'.format(self._humidity)),
                    pressure=int(self._pressure),
                    temperature=float('{0:.2f}'.format(self._temperature)))

    @property
    def altitude(self):
        """ BME280 altitude in meters """
        if not self._altitude:  # update if needed
            self.read()
        return self._altitude

    @property
    def dew_point(self):
        """ BME280 dew point in Celsius """
        if not self._dew_point:  # update if needed
            self.read()
        return self._dew_point

    @property
    def humidity(self):
        """ BME280 relative humidity in percent """
        if not self._humidity:  # update if needed
            self.read()
        return self._humidity

    @property
    def pressure(self):
        """ BME280 pressure in Pascals """
        if not self._pressure:  # update if needed
            self.read()
        return self._pressure

    @property
    def temperature(self):
        """ BME280 temperature in Celsius """
        if not self._temperature:  # update if needed
            self.read()
        return self._temperature

    def get_measurement(self):
        """ Gets the measurement in units by reading the """
        temperature = self.sensor.read_temperature()
        pressure = self.sensor.read_pressure()
        humidity = self.sensor.read_humidity()
        alt = altitude(pressure)
        dew_pt = dewpoint(temperature, humidity)
        return alt, dew_pt, humidity, pressure, temperature

    def read(self):
        """
        Takes a reading from the BME280 and updates the self._humidity and
        self._temperature values

        :returns: None on success or 1 on error
        """
        try:
            (self._altitude,
             self._dew_point,
             self._humidity,
             self._pressure,
             self._temperature) = self.get_measurement()
            if self._altitude is not None:
                return  # success - no errors
        except Exception as e:
            self.logger.exception(
                "{cls} raised an exception when taking a reading: "
                "{err}".format(cls=type(self).__name__, err=e))
        return 1
