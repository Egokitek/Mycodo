# coding=utf-8
""" Tests for the AtlasPT1000 sensor class """
import mock
import pytest
from testfixtures import LogCapture

from collections import Iterator
from mycodo.sensors.atlas_pt1000 import AtlasPT1000Sensor
from mycodo.sensors.am2315 import AM2315Sensor
# from mycodo.sensors.bme280 import BME280Sensor
from mycodo.sensors.bmp import BMPSensor
# from mycodo.sensors.dht11 import DHT11Sensor
# from mycodo.sensors.dht22 import DHT22Sensor
from mycodo.sensors.ds18b20 import DS18B20Sensor
from mycodo.sensors.htu21d import HTU21DSensor
# from mycodo.sensors.k30 import K30Sensor
from mycodo.sensors.raspi import (RaspberryPiCPUTemp,
                                  RaspberryPiGPUTemp)
from mycodo.sensors.raspi_cpuload import RaspberryPiCPULoad
from mycodo.sensors.tmp006 import TMP006Sensor
from mycodo.sensors.tsl2561 import TSL2561Sensor
from mycodo.sensors.sht1x_7x import SHT1x7xSensor
from mycodo.sensors.sht2x import SHT2xSensor

sensor_classes = [
    AtlasPT1000Sensor(0x00, 1),
    AM2315Sensor(1),
    # BME280Sensor(0x00, 1),
    # BMPSensor(1),
    # DHT11Sensor(pigpio.pi(), 1),
    # DHT22Sensor(pigpio.pi(), 1),
    # DS18B20Sensor('1'),
    # HTU21DSensor(1),
    # K30Sensor(),
    # RaspberryPiCPUTemp(),
    # RaspberryPiGPUTemp(),
    # RaspberryPiCPULoad(),
    # TMP006Sensor(0x00, 1),
    # TSL2561Sensor(0x00, 1),
    # SHT1x7xSensor(1, 2, '5.0'),
    # SHT2xSensor(0x00, 1)
]


# ----------------------------
#   Sensor tests
# ----------------------------
def test_sensor_class_iterates_using_in():
    """ Verify that a class object can use the 'in' operator """
    for each_class in sensor_classes:
        with mock.patch('{mod}.{name}.get_measurement'.format(mod=each_class.__module__, name=each_class.__class__.__name__)) as mock_measure:
            sensor_conditions = each_class.info()

            # Create mock_measure.side_effect
            list_cond = []
            number = 20
            number_mod = 5
            for _ in range(4):
                tuple_conditions = []
                for _ in sensor_conditions:
                    tuple_conditions.append(number)
                    number += number_mod
                if len(tuple_conditions) > 1:
                    tuple_conditions = tuple(tuple_conditions)
                else:
                    tuple_conditions = tuple_conditions[0]
                list_cond.append(tuple_conditions)
            mock_measure.side_effect = list_cond

            # Build expected results list
            expected_result_list = []
            for index in range(4):
                dict_build = {}
                index_cond = 0
                if len(sensor_conditions) == 1:
                    if sensor_conditions[0][2] == 'float':
                        dict_build[sensor_conditions[0][1]] = float(list_cond[index])
                    else:
                        dict_build[sensor_conditions[0][1]] = list_cond[index]
                else:
                    for each_cond in sensor_conditions:
                        if each_cond[2] == 'float':
                            dict_build[each_cond[1]] = float(list_cond[index][index_cond])
                        else:
                            dict_build[each_cond[1]] = list_cond[index][index_cond]
                        index_cond += 1
                expected_result_list.append(dict_build)

            assert expected_result_list == [cond for cond in each_class]

#
# def test_sensor_class__iter__returns_iterator():
#     """ The iter methods must return an iterator in order to work properly """
#     with mock.patch('mycodo.sensors.sensor_class.AtlasPT1000Sensor.get_measurement') as mock_measure:
#         # create our object
#         mock_measure.side_effect = [67, 52]  # first reading, second reading
#         sensor_class = AtlasPT1000Sensor(0x99, 1)
#         # check __iter__ method return
#         assert isinstance(sensor_class.__iter__(), Iterator)
#
#
# def test_sensor_class_read_updates_temp():
#     """  Verify that AtlasPT1000Sensor(0x99, 1).read() gets the average temp """
#     with mock.patch('mycodo.sensors.sensor_class.AtlasPT1000Sensor.get_measurement') as mock_measure:
#         # create our object
#         mock_measure.side_effect = [67, 52]  # first reading, second reading
#         sensor_class = AtlasPT1000Sensor(0x99, 1)
#         # test our read() function
#         assert sensor_class._temperature == 0  # init value
#         assert not sensor_class.read()  # updating the value using our mock_measure side effect has no error
#         assert sensor_class._temperature == 67.0  # first value
#         assert not sensor_class.read()  # updating the value using our mock_measure side effect has no error
#         assert sensor_class._temperature == 52.0  # second value
#
#
# def test_sensor_class_next_returns_dict():
#     """ next returns dict(temperature=float) """
#     with mock.patch('mycodo.sensors.sensor_class.AtlasPT1000Sensor.get_measurement') as mock_measure:
#         # create our object
#         mock_measure.side_effect = [67, 52]  # first reading, second reading
#         sensor_class = AtlasPT1000Sensor(0x99, 1)
#         assert sensor_class.next() == dict(temperature=67.00)
#
#
# def test_sensor_class_condition_properties():
#     """ verify temperature property """
#     with mock.patch('mycodo.sensors.sensor_class.AtlasPT1000Sensor.get_measurement') as mock_measure:
#         # create our object
#         mock_measure.side_effect = [67, 52]  # first reading, second reading
#         sensor_class = AtlasPT1000Sensor(0x99, 1)
#         assert sensor_class._temperature == 0  # initial value
#         assert sensor_class.temperature == 67.00  # first reading with auto update
#         assert sensor_class.temperature == 67.00  # same first reading, not updated yet
#         assert not sensor_class.read()  # update (no errors)
#         assert sensor_class.temperature == 52.00  # next reading
#
#
# def test_sensor_class_special_method_str():
#     """ expect a __str__ format """
#     assert "Temperature: 0.00" in str(AtlasPT1000Sensor(0x99, 1))
#
#
# def test_sensor_class_special_method_repr():
#     """ expect a __repr__ format """
#     assert "<AtlasPT1000Sensor(temperature=0.00)>" in repr(AtlasPT1000Sensor(0x99, 1))
#
#
# def test_sensor_class_raises_exception():
#     """ stops iteration on read() error """
#     with mock.patch('mycodo.sensors.sensor_class.AtlasPT1000Sensor.get_measurement', side_effect=IOError):
#         with pytest.raises(StopIteration):
#             AtlasPT1000Sensor(0x99, 1).next()
#
#
# def test_sensor_class_read_returns_1_on_exception():
#     """ Verify the read() method returns true on error """
#     with mock.patch('mycodo.sensors.sensor_class.AtlasPT1000Sensor.get_measurement', side_effect=Exception):
#         assert AtlasPT1000Sensor(0x99, 1).read()
#
#
# def test_sensor_class_get_measurement_divs_by_1k():
#     """ verify the return value of get_measurement """
#     mocked_open = mock.mock_open(read_data='45780')  # value read from sys temperature file
#     with mock.patch('mycodo.sensors.sensor_class.open', mocked_open, create=True):
#         assert AtlasPT1000Sensor.get_measurement() == 45.78  # value read / 1000
#
# def test_sensor_class_read_logs_unknown_errors():
#     """ verify that IOErrors are logged """
#     with LogCapture() as log_cap:
#         # force an Exception to be raised when get_measurement is called
#         with mock.patch('mycodo.sensors.sensor_class.AtlasPT1000Sensor.get_measurement', side_effect=Exception('msg')):
#             AtlasPT1000Sensor(0x99, 1).read()
#     expected_logs = ('mycodo.sensors.sensor_class', 'ERROR', 'AtlasPT1000Sensor raised an exception when taking a reading: msg')
#     assert expected_logs in log_cap.actual()
