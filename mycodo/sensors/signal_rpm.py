# coding=utf-8

import logging
import pigpio
from .base_sensor import AbstractSensor

logger = logging.getLogger("mycodo.sensors.rpm")


class ReadRPM:
    """
    A class to read pulses and calculate the RPM
    """

    def __init__(self, pi, gpio, pulses_per_rev=1.0, weighting=0.0):
        """
        Instantiate with the Pi and gpio of the RPM signal
        to monitor.

        Optionally the number of pulses for a complete revolution
        may be specified. It defaults to 1.

        Optionally a weighting may be specified. This is a number
        between 0 and 1 and indicates how much the old reading
        affects the new reading. It defaults to 0 which means
        the old reading has no effect. This may be used to
        smooth the data.
        """
        self.pi = pi
        self.gpio = gpio
        self.pulses_per_rev = pulses_per_rev

        self._watchdog = 200  # Milliseconds.

        if weighting < 0.0:
            weighting = 0.0
        elif weighting > 0.99:
            weighting = 0.99

        self._new = 1.0 - weighting  # Weighting for new reading.
        self._old = weighting  # Weighting for old reading.

        self._high_tick = None
        self._period = None

        pi.set_mode(gpio, pigpio.INPUT)

        self._cb = pi.callback(gpio, pigpio.RISING_EDGE, self._cbf)
        pi.set_watchdog(gpio, self._watchdog)

    def _cbf(self, gpio, level, tick):
        if level == 1:  # Rising edge.
            if self._high_tick is not None:
                t = pigpio.tickDiff(self._high_tick, tick)
                if self._period is not None:
                    self._period = (self._old * self._period) + (self._new * t)
                else:
                    self._period = t
            self._high_tick = tick
        elif level == 2:  # Watchdog timeout.
            if self._period is not None:
                if self._period < 2000000000:
                    self._period += (self._watchdog * 1000)

    def RPM(self):
        """
        Returns the RPM.
        """
        RPM = 0.0
        if self._period is not None:
            RPM = 60000000.0 / (self._period * self.pulses_per_rev)
        return RPM

    def cancel(self):
        """
        Cancels the reader and releases resources.
        """
        self.pi.set_watchdog(self.gpio, 0)  # cancel watchdog
        self._cb.cancel()


class RPMInput(AbstractSensor):
    """ A sensor support class that monitors rpm """

    def __init__(self, pin, weighting, rpm_pulses_per_rev):
        super(RPMInput, self).__init__()
        self._rpm = 0
        self.pin = pin
        self.weighting = weighting
        self.rpm_pulses_per_rev = rpm_pulses_per_rev

    def __repr__(self):
        """  Representation of object """
        return "<{cls}(rpm={rpm})>".format(
            cls=type(self).__name__,
            rpm="{0:.2f}".format(self._rpm))

    def __str__(self):
        """ Return rpm information """
        return "RPM: {0:.2f}".format(self._rpm)

    def __iter__(self):  # must return an iterator
        """ Iterates through live rpm readings """
        return self

    def next(self):
        """ Get next rpm reading """
        if self.read():  # raised an error
            raise StopIteration  # required
        return dict(rpm=float('{0:.2f}'.format(self._rpm)))

    @property
    def rpm(self):
        """ rpm (revolutions per minute) """
        if not self._rpm:  # update if needed
            self.read()
        return self._rpm

    def get_measurement(self):
        """ Gets the rpm """
        try:
            pi = pigpio.pi()
            read_rpm = ReadRPM(
                pi, self.pin, self.weighting, self.rpm_pulses_per_rev)
        except Exception:
            return 0

        try:
            rpm = read_rpm.RPM()
            if rpm:
                return int(rpm + 0.5)
        except Exception:
            logger.exception(1)
        finally:
            read_rpm.cancel()
            pi.stop()
        return 0

    def read(self):
        """
        Takes a reading from the pin and updates the self._rpm value

        :returns: None on success or 1 on error
        """
        try:
            self._rpm = self.get_measurement()
            return  # success - no errors
        except IOError as e:
            logger.error("{cls}.get_measurement() method raised IOError: "
                         "{err}".format(cls=type(self).__name__, err=e))
        except Exception as e:
            logger.exception("{cls} raised an exception when taking a reading: "
                             "{err}".format(cls=type(self).__name__, err=e))
        return 1
