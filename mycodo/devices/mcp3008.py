# coding=utf-8
import argparse
import logging
import time

import Adafruit_MCP3008
import fasteners


class MCP3008Read(object):
    """ ADC Read """
    def __init__(self, clockpin, cspin, misopin, mosipin, channel, volts_max):
        self.logger = logging.getLogger(
            'mycodo.mcp3008-{clock}-{cs}-{miso}-{mosi}-{chan}'.format(
                clock=clockpin, cs=cspin, miso=misopin,
                mosi=mosipin, chan=channel))
        self._voltage = None
        self.channel = channel
        self.volts_max = volts_max

        self.lock_file = '/var/lock/mcp3008-{clock}-{cs}-{miso}-{mosi}-{chan}'.format(
                clock=clockpin, cs=cspin, miso=misopin,
                mosi=mosipin, chan=channel)
        self.adc = Adafruit_MCP3008.MCP3008(clk=clockpin,
                                            cs=cspin,
                                            miso=misopin,
                                            mosi=mosipin)

    def read(self):
        """ Take a measurement """
        self._voltage = None
        lock_acquired = False
        try:
            lock = fasteners.InterProcessLock(self.lock_file)
            for _ in range(600):
                lock_acquired = lock.acquire(blocking=False)
                if lock_acquired:
                    break
                else:
                    time.sleep(0.1)

            if lock_acquired:
                self._voltage = (self.adc.read_adc(self.channel) / 1023.0) * self.volts_max
                lock.release()
            else:
                self.logger.error("Could not acquire lock")
        except Exception as e:
            self.logger.exception(
                "{cls} raised exception during read(): "
                "{err}".format(cls=type(self).__name__, err=e))
            return 1

    @property
    def voltage(self):
        return self._voltage

    def __iter__(self):
        """
        Support the iterator protocol.
        """
        return self

    def next(self):
        """
        Call the read method and return voltage information.
        """
        if self.read():
            return None
        return dict(voltage=float('{0:.4f}'.format(self._voltage)))


def parse_args(parser):
    """ Add arguments for argparse """
    parser.add_argument('--clockpin', metavar='CLOCKPIN', type=int,
                        help='SPI Clock Pin',
                        required=True)
    parser.add_argument('--misopin', metavar='MISOPIN', type=int,
                        help='SPI MISO Pin',
                        required=True)
    parser.add_argument('--mosipin', metavar='MOSIPIN', type=int,
                        help='SPI MOSI Pin',
                        required=True)
    parser.add_argument('--cspin', metavar='CSPIN', type=int,
                        help='SPI CS Pin',
                        required=True)
    parser.add_argument('--adcchannel', metavar='ADCCHANNEL', type=int,
                        help='channel to read from the ADC (0 - 7)',
                        required=False, choices=range(0,8))
    return parser.parse_args()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='MCP3008 Analog-to-Digital Converter Read Test Script')
    args = parse_args(parser)

    # Example Software SPI pins: CLK = 18, MISO = 23, MOSI = 24, CS = 25
    mcp = Adafruit_MCP3008.MCP3008(clk=args.clockpin,
                                   cs=args.cspin,
                                   miso=args.misopin,
                                   mosi=args.mosipin)

    if -1 < args.adcchannel < 8:
        # Read the specified channel
        value = mcp.read_adc(args.adcchannel)
        print("ADC Channel: {chan}, Output: {out}".format(
            chan=args.adcchannel, out=value))
    else:
        # Create a list for the ADC channel values
        values = [0] * 8

        # Conduct measurements of channels 0 - 7, add them to the list
        for i in range(8):
            values[i] = mcp.read_adc(i)

        # Print the list of ADC values
        print('| {0:>4} | {1:>4} | {2:>4} | {3:>4} | {4:>4} | {5:>4} | {6:>4} | {7:>4} |'.format(*values))
