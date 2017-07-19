# coding=utf-8
import datetime
from RPi import GPIO

from mycodo.databases import CRUDMixin
from mycodo.databases import set_uuid
from mycodo.mycodo_flask.extensions import db

from mycodo.devices.wireless_433mhz_pi_switch import Transmit433MHz
from mycodo.utils.system_pi import cmd_output


class Relay(CRUDMixin, db.Model):
    __tablename__ = "relay"

    id = db.Column(db.Integer, unique=True, primary_key=True)
    unique_id = db.Column(db.String, nullable=False, unique=True, default=set_uuid)  # ID for influxdb entries
    relay_type = db.Column(db.Text, default='wired')  # Options: 'command', 'wired', 'wireless_433MHz_pi_switch', 'pwm'
    name = db.Column(db.Text, default='Relay')
    pin = db.Column(db.Integer, default=None)  # Pin connected to the device/relay
    trigger = db.Column(db.Boolean, default=True)  # GPIO output to turn relay on (True=HIGH, False=LOW)
    amps = db.Column(db.Float, default=0.0)  # The current drawn by the device connected to the relay
    on_at_start = db.Column(db.Boolean, default=None)  # Turn relay on or off when daemon starts
    on_until = db.Column(db.DateTime, default=None)  # Stores time to turn off relay (if on for a duration)
    last_duration = db.Column(db.Float, default=None)  # Stores the last on duration (seconds)
    on_duration = db.Column(db.Boolean, default=None)  # Stores if the relay is currently on for a duration
    protocol = db.Column(db.Integer, default=None)
    pulse_length = db.Column(db.Integer, default=None)
    bit_length = db.Column(db.Integer, default=None)
    on_command = db.Column(db.Text, default=None)
    off_command = db.Column(db.Text, default=None)

    # PWM
    pwm_hertz = db.Column(db.Integer, default=None)  # PWM Hertz
    pwm_library = db.Column(db.Text, default=None)  # Library to produce PWM

    def __reper__(self):
        return "<{cls}(id={s.id})>".format(s=self, cls=self.__class__.__name__)

    def _is_setup(self):
        """
        This function checks to see if the GPIO pin is setup and ready to use.  This is for safety
        and to make sure we don't blow anything.

        # TODO Make it do that.

        :return: Is it safe to manipulate this relay?
        :rtype: bool
        """
        if self.relay_type == 'wired' and self.pin:
            self.setup_pin()
            return True

    def setup_pin(self):
        """
        Setup pin for this relay

        :rtype: None
        """
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(True)
        GPIO.setup(self.pin, GPIO.OUT)

    def turn_off(self):
        """
        Turn this relay off

        :rtype: None
        """
        self.on_duration = False
        self.on_until = datetime.datetime.now()
        if self.relay_type == 'wired' and self._is_setup():
            GPIO.output(self.pin, not self.trigger)
        elif self.relay_type == 'wireless_433MHz_pi_switch' and self.off_command:
            wireless_pi_switch = Transmit433MHz(
                self.pin,
                protocol=int(self.protocol),
                pulse_length=int(self.pulse_length),
                bit_length=int(self.bit_length))
            wireless_pi_switch.transmit(int(self.off_command))
        elif self.relay_type == 'command' and self.off_command:
            cmd_return, _, cmd_status = cmd_output(self.off_command)

    def turn_on(self):
        """
        Turn this relay on

        :rtype: None
        """
        if self.relay_type == 'wired' and self._is_setup():
            GPIO.output(self.pin, self.trigger)
        elif self.relay_type == 'wireless_433MHz_pi_switch' and self.on_command:
            wireless_pi_switch = Transmit433MHz(
                self.pin,
                protocol=int(self.protocol),
                pulse_length=int(self.pulse_length),
                bit_length=int(self.bit_length))
            wireless_pi_switch.transmit(int(self.on_command))
        elif self.relay_type == 'command' and self.on_command:
            cmd_return, _, cmd_status = cmd_output(self.on_command)

    def is_on(self):
        """
        :return: Whether the relay is currently "ON"
        :rtype: bool
        """
        if self.relay_type == 'wired' and self._is_setup():
            return self.trigger == GPIO.input(self.pin)

