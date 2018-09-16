# coding=utf-8
import logging
import time

from mycodo.inputs.base_input import AbstractInput
from mycodo.inputs.sensorutils import convert_units

# Input information
INPUT_INFORMATION = {
    'input_name_unique': 'SIGNAL_PWM',
    'input_manufacturer': 'Mycodo',
    'input_name': 'Signal (PWM)',
    'measurements_name': 'Frequency/Pulse Width/Duty Cycle',
    'measurements_list': ['frequency','pulse_width', 'duty_cycle'],
    'dependencies_module': [
        ('internal', 'pigpio', 'pigpio')
    ],
    'interfaces': ['GPIO'],
    'weighting': 0.0,
    'sample_time': 2.0,
    'options_enabled': ['gpio_location', 'weighting', 'sample_time', 'period', 'convert_unit', 'pre_output'],
    'options_disabled': ['interface']
}


class InputModule(AbstractInput):
    """ A sensor support class that monitors pwm """

    def __init__(self, input_dev, testing=False):
        super(InputModule, self).__init__()
        self.logger = logging.getLogger("mycodo.inputs.signal_pwm")
        self._frequency = None
        self._pulse_width = None
        self._duty_cycle = None

        if not testing:
            import pigpio
            self.logger = logging.getLogger(
                "mycodo.inputs.signal_pwm_{id}".format(id=input_dev.id))
            self.gpio = int(input_dev.gpio_location)
            self.convert_to_unit = input_dev.convert_to_unit
            self.weighting = input_dev.weighting
            self.sample_time = input_dev.sample_time
            self.pigpio = pigpio

    def __repr__(self):
        """  Representation of object """
        return "<{cls}(frequency={f})(pulse_width={pw})(duty_cycle={dc})>".format(
            cls=type(self).__name__,
            f="{0:.2f}".format(self._frequency),
            pw="{0:.2f}".format(self._pulse_width),
            dc="{0:.2f}".format(self._duty_cycle))

    def __str__(self):
        """ Return pwm information """
        return "Frequency: {f:.2f}, Pulse Width: {pw:.2f}, " \
               "Duty Cycle: {dc:.2f}".format(f=self._frequency,
                                             pw=self._pulse_width,
                                             dc=self._duty_cycle)

    def __iter__(self):  # must return an iterator
        """ Iterates through live pwm readings """
        return self

    def next(self):
        """ Get next pwm reading """
        if self.read():  # raised an error
            raise StopIteration  # required
        return dict(frequency=float('{0:.2f}'.format(self._frequency)),
                    pulse_width=float('{0:.2f}'.format(self._pulse_width)),
                    duty_cycle=float('{0:.2f}'.format(self._duty_cycle)))

    @property
    def frequency(self):
        """ frequency """
        if self._frequency is None:  # update if needed
            self.read()
        return self._frequency

    @property
    def pulse_width(self):
        """ pulse width """
        if self._pulse_width is None:  # update if needed
            self.read()
        return self._pulse_width

    @property
    def duty_cycle(self):
        """ duty cycle """
        if self._duty_cycle is None:  # update if needed
            self.read()
        return self._duty_cycle

    def get_measurement(self):
        """ Gets the pwm """
        self._frequency = None
        self._pulse_width = None
        self._duty_cycle = None

        pi = self.pigpio.pi()
        if not pi.connected:  # Check if pigpiod is running
            self.logger.error("Could not connect to pigpiod."
                         "Ensure it is running and try again.")
            return None, None, None

        read_pwm = ReadPWM(pi, self.gpio, self.pigpio, self.weighting)
        time.sleep(self.sample_time)
        frequency = convert_units(
            'frequency', 'Hz', self.convert_to_unit,
            read_pwm.frequency())
        pulse_width = int(read_pwm.pulse_width() + 0.5)
        duty_cycle = read_pwm.duty_cycle()
        read_pwm.cancel()
        pi.stop()

        duty_cycle = convert_units(
            'duty_cycle', 'percent', self.convert_to_unit,
            duty_cycle)

        return frequency, pulse_width, duty_cycle

    def read(self):
        """
        Takes a reading from the pin and updates the self._pwm value

        :returns: None on success or 1 on error
        """
        try:
            (self._frequency,
             self._pulse_width,
             self._duty_cycle) = self.get_measurement()
            if self._frequency is not None:
                return  # success - no errors
        except Exception as e:
            self.logger.error("{cls} raised an exception when taking a reading: "
                         "{err}".format(cls=type(self).__name__, err=e))
        return 1


class ReadPWM:
    """
    A class to read PWM pulses and calculate their frequency
    and duty cycle. The frequency is how often the pulse
    happens per second. The duty cycle is the percentage of
    pulse high time per cycle.
    """

    def __init__(self, pi, gpio, pigpio, weighting=0.0):
        """
        Instantiate with the Pi and gpio of the PWM signal
        to monitor.

        Optionally a weighting may be specified.  This is a number
        between 0 and 1 and indicates how much the old reading
        affects the new reading.  It defaults to 0 which means
        the old reading has no effect.  This may be used to
        smooth the data.
        """
        self.pi = pi
        self.gpio = gpio
        self.pigpio = pigpio

        if weighting < 0.0:
            weighting = 0.0
        elif weighting > 0.99:
            weighting = 0.99

        self._new = 1.0 - weighting  # Weighting for new reading.
        self._old = weighting  # Weighting for old reading.

        self._high_tick = None
        self._period = None
        self._high = None

        pi.set_mode(gpio, pigpio.INPUT)
        self._cb = pi.callback(gpio, self.pigpio.EITHER_EDGE, self._cbf)

    def _cbf(self, gpio, level, tick):
        if level == 1:
            if self._high_tick is not None:
                t = self.pigpio.tickDiff(self._high_tick, tick)
                if self._period is not None:
                    self._period = (self._old * self._period) + (self._new * t)
                else:
                    self._period = t
            self._high_tick = tick
        elif level == 0:
            if self._high_tick is not None:
                t = self.pigpio.tickDiff(self._high_tick, tick)
                if self._high is not None:
                    self._high = (self._old * self._high) + (self._new * t)
                else:
                    self._high = t

    def frequency(self):
        """
        Returns the PWM frequency.
        """
        if self._period is not None:
            return 1000000.0 / self._period
        else:
            return 0.0

    def pulse_width(self):
        """
        Returns the PWM pulse width in microseconds.
        """
        if self._high is not None:
            return self._high
        else:
            return 0.0

    def duty_cycle(self):
        """
        Returns the PWM duty cycle percentage.
        """
        if self._high is not None:
            return 100.0 * self._high / self._period
        else:
            return 0.0

    def cancel(self):
        """
        Cancels the reader and releases resources.
        """
        self._cb.cancel()
