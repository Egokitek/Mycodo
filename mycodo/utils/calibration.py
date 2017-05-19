# coding=utf-8
import logging
import time
from lockfile import LockFile

from mycodo.devices.atlas_scientific_i2c import AtlasScientificI2C
from mycodo.devices.atlas_scientific_uart import AtlasScientificUART\

from mycodo.config import ATLAS_PH_LOCK_FILE

logger = logging.getLogger("mycodo.atlas_scientific")


class AtlasScientificCommand:
    """
    Class to handle issuing commands to the Atlas Scientific sensor boards
    """

    def __init__(self, sensor_sel):
        self.cmd_send = None
        self.ph_sensor_uart = None
        self.ph_sensor_i2c = None
        self.interface = sensor_sel.interface

        if self.interface == 'UART':
            self.ph_sensor_uart = AtlasScientificUART(
                serial_device=sensor_sel.device_loc,
                baudrate=sensor_sel.baud_rate)
        elif self.interface == 'I2C':
            self.ph_sensor_i2c = AtlasScientificI2C(
                i2c_address=sensor_sel.i2c_address,
                i2c_bus=sensor_sel.i2c_bus)

        self.board_version, self.board_info = self.board_version()

        if self.board_version == 0:
            logger.info("Unable to retrieve device info (this indicates the "
                        "device was not properly initialized or connected)")
        else:
            logger.info("Device Info: {info}".format(info=self.board_info))
            logger.info("Detected Version: {ver}".format(ver=self.board_version))

    def board_version(self):
        """Return the board version of the Atlas Scientific pH sensor"""
        info = None

        lock = LockFile(ATLAS_PH_LOCK_FILE)
        try:
            while not lock.i_am_locking():
                try:
                    lock.acquire(timeout=60)  # wait up to 60 seconds before breaking lock
                except Exception as e:
                    logger.error("{cls} 60 second timeout, {lock} lock broken: "
                                 "{err}".format(cls=type(self).__name__,
                                                lock=ATLAS_PH_LOCK_FILE,
                                                err=e))
                    lock.break_lock()
                    lock.acquire()
            if self.interface == 'UART':
                self.ph_sensor_uart.send_cmd('i')
                time.sleep(1.3)
                info = self.ph_sensor_uart.read_lines()[0]
            elif self.interface == 'I2C':
                info = self.ph_sensor_i2c.query('i')
            lock.release()
        except Exception as err:
            info = None
            logger.error("{cls} raised an exception when taking a reading: "
                         "{err}".format(cls=type(self).__name__, err=err))
            lock.release()

        # Check first letter of info response
        # "P" indicates a legacy board version
        if info is None:
            return 0, None
        elif info[0] == 'P':
            return 1, info  # Older board version
        else:
            return 2, info  # Newer board version

    def calibrate(self, command, temperature=None, custom_cmd=None):
        """
        Determine and send the correct command to an Atlas Scientific sensor,
        based on the board version
        """
        # Formulate command based on calibration step and board version.
        # Legacy boards requires a different command than recent boards.
        # Some commands are not necessary for recent boards and will not
        # generate a response.
        err = 1
        msg = "Default message"
        if command == 'temperature' and temperature is not None:
            if self.board_version == 1:
                err, msg = self.send_command(temperature)
            elif self.board_version == 2:
                err, msg = self.send_command('T,{temp}'.format(temp=temperature))
        elif command == 'clear_calibration':
            if self.board_version == 1:
                err, msg = self.send_command('X')
                self.send_command('L0')
            elif self.board_version == 2:
                err, msg = self.send_command('Cal,clear')
        elif command == 'continuous':
            if self.board_version == 1:
                err, msg = self.send_command('C')
        elif command == 'low':
            if self.board_version == 1:
                err, msg = self.send_command('F')
            elif self.board_version == 2:
                err, msg = self.send_command('Cal,low,4.00')
        elif command == 'mid':
            if self.board_version == 1:
                err, msg = self.send_command('S')
            elif self.board_version == 2:
                err, msg = self.send_command('Cal,mid,7.00')
        elif command == 'high':
            if self.board_version == 1:
                err, msg = self.send_command('T')
            elif self.board_version == 2:
                err, msg = self.send_command('Cal,high,10.00')
        elif command == 'end':
            if self.board_version == 1:
                err, msg = self.send_command('E')
        elif custom_cmd:
            err, msg = self.send_command(custom_cmd)
        return err, msg

    def send_command(self, cmd_send):
        """ Send the command (if not None) and return the response """
        lock = LockFile(ATLAS_PH_LOCK_FILE)
        try:
            while not lock.i_am_locking():
                try:
                    lock.acquire(timeout=60)  # wait up to 60 seconds before breaking lock
                except Exception as e:
                    logger.error("{cls} 60 second timeout, {lock} lock broken: "
                                 "{err}".format(cls=type(self).__name__,
                                                lock=ATLAS_PH_LOCK_FILE,
                                                err=e))
                    lock.break_lock()
                    lock.acquire()
            return_value = "No message"
            if cmd_send is not None:
                if self.interface == 'UART':
                    self.ph_sensor_uart.send_cmd(cmd_send)
                    return_value = self.ph_sensor_uart.read_lines()
                elif self.interface == 'I2C':
                    return_value = self.ph_sensor_i2c.query(cmd_send)
                time.sleep(0.1)
            lock.release()
            return 0, return_value
        except Exception as err:
            logger.error("{cls} raised an exception when taking a reading: "
                         "{err}".format(cls=type(self).__name__, err=err))
            lock.release()
            return 1, err

