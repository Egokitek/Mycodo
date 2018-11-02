# coding=utf-8
import logging

from flask_babel import lazy_gettext

from mycodo.databases.models import InputMeasurements
from mycodo.inputs.base_input import AbstractInput
from mycodo.utils.database import db_retrieve_table_daemon

# Channels
channels = {}
for each_channel in range(8):
    channels[each_channel] = {}

# Measurements
measurements = {
    'electrical_potential': {
        'V': channels
    }
}

# Input information
INPUT_INFORMATION = {
    'input_name_unique': 'ADS1256',
    'input_manufacturer': 'Texas Instruments',
    'input_name': 'ADS1256',
    'measurements_name': 'Voltage (Waveshare, Analog-to-Digital Converter)',
    'measurements_dict': measurements,
    'measurements_convert_enabled': True,
    'measurements_rescale': True,
    'scale_from_min': 0.0,
    'scale_from_max': 5.0,

    'options_enabled': [
        'measurements_select',
        'measurements_convert',
        'adc_gain',
        'adc_sample_speed',
        'custom_options',
        'period',
        'pre_output'
    ],
    'options_disabled': ['interface'],

    'dependencies_module': [
        ('pip-pypi', 'wiringpi', 'wiringpi'),
        ('pip-git', 'pipyadc_py3', 'git://github.com/kizniche/PiPyADC-py3.git#egg=pipyadc_py3')  # PiPyADC ported to Python3
    ],
    'interfaces': ['UART'],

    'adc_gain': [
        (1, '1'),
        (2, '2'),
        (4, '4'),
        (8, '8'),
        (16, '16'),
        (32, '32'),
        (64, '64')
    ],
    'adc_sample_speed': [
        ('30000', '30,000'),
        ('15000', '15,000'),
        ('7500', '7,500'),
        ('3750', '3,750'),
        ('2000', '2,000'),
        ('1000', '1,000'),
        ('500', '500'),
        ('100', '100'),
        ('60', '60'),
        ('50', '50'),
        ('30', '30'),
        ('25', '25'),
        ('15', '15'),
        ('10', '10'),
        ('5', '5'),
        ('2d5', '2.5')
    ],

    'custom_options': [
        {
            'id': 'adc_calibration',
            'type': 'select',
            'default_value': '',
            'options_select': [
                ('', 'No Calibration'),
                ('SELFOCAL', 'Self Offset'),
                ('SELFGCAL', 'Self Gain)'),
                ('SELFCAL', 'Self Offset + Self Gain'),
                ('SYSOCAL', 'System Offset'),
                ('SYSGCAL', 'System Gain')
            ],
            'name': lazy_gettext('Calibration'),
            'phrase': lazy_gettext('Set the calibration method to perform during Input activation')
        }
    ],
}


class InputModule(AbstractInput):
    """ ADC Read """
    def __init__(self, input_dev, testing=False):
        super(InputModule, self).__init__()
        self.logger = logging.getLogger('mycodo.ads1256')
        self._measurements = None

        if not testing:
            from ADS1256_definitions import POS_AIN0
            from ADS1256_definitions import POS_AIN1
            from ADS1256_definitions import POS_AIN2
            from ADS1256_definitions import POS_AIN3
            from ADS1256_definitions import POS_AIN4
            from ADS1256_definitions import POS_AIN5
            from ADS1256_definitions import POS_AIN6
            from ADS1256_definitions import POS_AIN7
            from ADS1256_definitions import NEG_AINCOM
            from pipyadc_py3 import ADS1256
            import glob

            # Input pin for the potentiometer on the Waveshare Precision ADC board
            POTI = POS_AIN0 | NEG_AINCOM
            # Light dependant resistor
            LDR = POS_AIN1 | NEG_AINCOM
            EXT2, EXT3, EXT4 = POS_AIN2 | NEG_AINCOM, POS_AIN3 | NEG_AINCOM, POS_AIN4 | NEG_AINCOM
            EXT5, EXT6, EXT7 = POS_AIN5 | NEG_AINCOM, POS_AIN6 | NEG_AINCOM, POS_AIN7 | NEG_AINCOM
            self.CH_SEQUENCE = (POTI, LDR, EXT2, EXT3, EXT4, EXT5, EXT6, EXT7)

            self.logger = logging.getLogger(
                'mycodo.ads1256_{id}'.format(id=input_dev.unique_id.split('-')[0]))

            self.adc_calibration = None

            self.input_measurements = db_retrieve_table_daemon(
                InputMeasurements).filter(
                    InputMeasurements.input_id == input_dev.unique_id).all()

            self.adc_gain = input_dev.adc_gain
            self.adc_sample_speed = input_dev.adc_sample_speed

            if input_dev.custom_options:
                for each_option in input_dev.custom_options.split(';'):
                    option = each_option.split(',')[0]
                    value = each_option.split(',')[1]
                    if option == 'adc_calibration':
                        self.adc_calibration = value

            if glob.glob('/dev/spi*'):
                self.ads = ADS1256()

                # Perform selected calibration
                if self.adc_calibration == 'SELFOCAL':
                    self.ads.cal_self_offset()
                elif self.adc_calibration == 'SELFGCAL':
                    self.ads.cal_self_gain()
                elif self.adc_calibration == 'SELFCAL':
                    self.ads.cal_self()
                elif self.adc_calibration == 'SYSOCAL':
                    self.ads.cal_system_offset()
                elif self.adc_calibration == 'SYSGCAL':
                    self.ads.cal_system_gain()

                self.running = True
            else:
                raise Exception(
                    "SPI device /dev/spi* not found. Ensure SPI is enabled "
                    "and the device is recognized/setup by linux.")

    def get_measurement(self):
        self._measurements = {}
        voltages_list = []
        voltages_dict = {}
        count = 0

        return_dict = {
            'electrical_potential': {
                'V': {}
            }
        }

        # 2 attempts to get valid measurement
        while (self.running and count < 2 and
               (not any(voltages_dict.values()) or 0 in voltages_dict.values())):
            raw_channels = self.ads.read_sequence(self.CH_SEQUENCE)
            voltages_list = [i * self.ads.v_per_digit for i in raw_channels]
            count += 1

        if not voltages_list or 0 in voltages_list:
            self.logger.error(
                "ADC returned measurement of 0 (indicating "
                "something is wrong).")
            return

        for each_measure in self.input_measurements:
            if each_measure.is_enabled:
                return_dict['electrical_potential']['V'][each_measure.channel] = voltages_list[each_measure.channel]

        if return_dict['electrical_potential']['V']:
            return return_dict


if __name__ == "__main__":
    from types import SimpleNamespace

    input_dev_ = SimpleNamespace()
    input_dev_.id = 1
    input_dev_.unique_id = '1234-5678'
    input_dev_.adc_gain = '1'
    input_dev_.adc_sample_speed = '10'
    input_dev_.channels = 8

    ads = InputModule(input_dev_)
    print("Channel 0: {}".format(ads.next()))
