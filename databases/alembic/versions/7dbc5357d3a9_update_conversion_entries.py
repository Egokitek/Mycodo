"""update conversion entries

Revision ID: 7dbc5357d3a9
Revises: f05ca91a4c65
Create Date: 2018-07-20 10:19:24.691605

"""

import sys

import os
import re
import sqlalchemy as sa
from alembic import op

sys.path.append(os.path.abspath(os.path.join(__file__, "../../../..")))

from mycodo.databases.models import Input
from mycodo.databases.models import LCDData
from mycodo.databases.models import Math
from mycodo.databases.models import Measurement
from mycodo.databases.models import Unit
from mycodo.databases.utils import session_scope
from mycodo.config import LIST_DEVICES_ADC
from mycodo.config import MATH_INFO
from mycodo.config_devices_units import UNITS
from mycodo.config_devices_units import MEASUREMENT_UNITS
from mycodo.config import SQL_DATABASE_MYCODO

MYCODO_DB_PATH = 'sqlite:///' + SQL_DATABASE_MYCODO

# revision identifiers, used by Alembic.
revision = '7dbc5357d3a9'
down_revision = 'f05ca91a4c65'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("pid") as batch_op:
        batch_op.add_column(sa.Column('autotune_activated', sa.Boolean))
        batch_op.add_column(sa.Column('autotune_noiseband', sa.Float))
        batch_op.add_column(sa.Column('autotune_outstep', sa.Float))

    op.execute(
        '''
        UPDATE pid
        SET autotune_activated=0
        '''
    )

    op.create_table(
        'measurements',
        sa.Column('id', sa.Integer, nullable=False, unique=True),
        sa.Column('unique_id', sa.String, nullable=False, unique=True),
        sa.Column('name_safe', sa.Text),
        sa.Column('name', sa.Text),
        sa.Column('units', sa.Text),
        sa.PrimaryKeyConstraint('id'),
        keep_existing=True)

    op.create_table(
        'units',
        sa.Column('id', sa.Integer, nullable=False, unique=True),
        sa.Column('unique_id', sa.String, nullable=False, unique=True),
        sa.Column('name_safe', sa.Text),
        sa.Column('name', sa.Text),
        sa.Column('unit', sa.Text),
        sa.PrimaryKeyConstraint('id'),
        keep_existing=True)

    op.create_table(
        'conversion',
        sa.Column('id', sa.Integer, nullable=False, unique=True),
        sa.Column('unique_id', sa.String, nullable=False, unique=True),
        sa.Column('convert_unit_from', sa.Text),
        sa.Column('convert_unit_to', sa.Text),
        sa.Column('equation', sa.Text),
        sa.PrimaryKeyConstraint('id'),
        keep_existing=True)

    # There has been a chance to how the measurement/unit selection for inputs
    # is handled. There is a new naming convention for units, old unit names
    # need to be renamed. Custom measurements/units from LinuxCommand Inputs
    # and Maths need to be transferred to the measurement/units tables.
    with session_scope(MYCODO_DB_PATH) as new_session:
        # Iterate through math and linux command inputs and add any unique
        # measurements/units to measurement/unit tables.
        # Also update measurement/unit names to be compatible with new naming
        # convention (alphanumeric and underscore only).

        # Measurement name changes
        measurement_replacements = {
            'duration_sec': 'duration_time',
            'ph': 'ion_concentration',
            'kilopascals': 'pressure',
            'lux': 'light',
            'rpm': 'revolutions'
        }

        # Unit name changes
        unit_replacements = {
            'sec': 'second',
            'celsius': 'C',
            'fahrenheit': 'F',
            'kelvin': 'K',
            'feet': 'ft',
            'kilopascals': 'kPa',
            'pascals': 'Pa',
            'meters': 'm'
        }

        # Update LCD Data
        mod_lcd_data = new_session.query(LCDData).all()
        for each_lcd_data in mod_lcd_data:
            # Update names
            for each_current, each_replacement in measurement_replacements.items():
                each_lcd_data.line_1_measurement = each_lcd_data.line_1_measurement.replace(each_current, each_replacement)
                each_lcd_data.line_2_measurement = each_lcd_data.line_2_measurement.replace(each_current, each_replacement)
                each_lcd_data.line_3_measurement = each_lcd_data.line_3_measurement.replace(each_current, each_replacement)
                each_lcd_data.line_4_measurement = each_lcd_data.line_4_measurement.replace(each_current, each_replacement)

        # Update Input entries and add custom measurement/units
        mod_input = new_session.query(Input).all()
        for each_input in mod_input:
            # Update names
            for each_current, each_replacement in measurement_replacements.items():
                each_input.measurements = each_input.measurements.replace(each_current, each_replacement)

            # If no unit entry, create entry with default units
            if each_input.convert_to_unit == '' or not each_input.convert_to_unit:
                list_measure_units = []
                for each_measure in each_input.measurements.split(','):
                    if each_measure in MEASUREMENT_UNITS:
                        entry = '{meas},{unit}'.format(
                            meas=each_measure,
                            unit=MEASUREMENT_UNITS[each_measure]['units'][0])
                        list_measure_units.append(entry)

                string_measure_units = ";".join(list_measure_units)
                each_input.convert_to_unit = string_measure_units

            # Rename units and add missing measurement/units
            else:
                # Replace old names with new
                string_measure_units = each_input.convert_to_unit
                for each_unit_current, each_unit_replacement in unit_replacements.items():
                    string_measure_units = string_measure_units.replace(each_unit_current, each_unit_replacement)

                list_current_measure_units = string_measure_units.split(';')
                for each_measure in each_input.measurements.split(','):
                    if any(each_measure in s for s in list_current_measure_units):
                        pass
                    elif each_measure in MEASUREMENT_UNITS:
                        entry = '{meas},{unit}'.format(
                            meas=each_measure,
                            unit=MEASUREMENT_UNITS[each_measure]['units'][0])
                        list_current_measure_units.append(entry)

                string_measure_units = ";".join(list_current_measure_units)
                each_input.convert_to_unit = string_measure_units

            # Add Linux Command Input measurement and unit to custom dictionary
            if (each_input.device == 'LinuxCommand' and
                    each_input.cmd_measurement != '' and
                    each_input.cmd_measurement_units != ''):
                measurement = re.sub('[^0-9a-zA-Z]+', '_', each_input.cmd_measurement).lower()
                unit = re.sub('[^0-9a-zA-Z]+', '_', each_input.cmd_measurement_units)
                if each_input.cmd_measurement not in MEASUREMENT_UNITS:
                    new_measurement = Measurement()
                    new_measurement.name_safe = measurement
                    new_measurement.name = measurement
                    new_measurement.units = unit
                    new_session.add(new_measurement)
                if each_input.cmd_measurement_units not in UNITS:
                    new_unit = Unit()
                    new_unit.name_safe = unit
                    new_unit.name = unit
                    new_unit.unit = unit
                    new_session.add(new_unit)
                each_input.measurements = measurement
                each_input.convert_to_unit = '{meas},{unit}'.format(
                    meas=measurement, unit=unit)

            # Add ADC Input measurement and unit to custom dictionary
            if (each_input.device in LIST_DEVICES_ADC and
                    each_input.adc_measure != '' and
                    each_input.adc_measure_units != ''):
                measurement = re.sub('[^0-9a-zA-Z]+', '_', each_input.adc_measure).lower()
                unit = re.sub('[^0-9a-zA-Z]+', '_', each_input.adc_measure_units)
                if each_input.cmd_measurement not in MEASUREMENT_UNITS:
                    new_measurement = Measurement()
                    new_measurement.name_safe = measurement
                    new_measurement.name = measurement
                    new_measurement.units = unit
                    new_session.add(new_measurement)
                    # new_measurement.flush()
                if each_input.cmd_measurement_units not in UNITS:
                    new_unit = Unit()
                    new_unit.name_safe = unit
                    new_unit.name = unit
                    new_unit.unit = unit
                    new_session.add(new_unit)
                    # new_unit.flush()
                each_input.measurements = measurement
                each_input.convert_to_unit = '{meas},{unit}'.format(
                    meas=measurement, unit=unit)

        # Update Math entries and add custom measurement/units
        def add_custom_entry_from_math(each_math, measurement, unit):
            if each_math.measure != '' and each_math.measure_units != '':
                measurement = re.sub('[^0-9a-zA-Z]+', '_', measurement).lower()
                unit = re.sub('[^0-9a-zA-Z]+', '_', unit)
                if measurement not in MEASUREMENT_UNITS:
                    new_measurement = Measurement()
                    new_measurement.name_safe = measurement
                    new_measurement.name = measurement
                    new_measurement.units = unit
                    new_session.add(new_measurement)
                if unit not in UNITS:
                    new_unit = Unit()
                    new_unit.name_safe = unit
                    new_unit.name = unit
                    new_unit.unit = unit
                    new_session.add(new_unit)

        math = new_session.query(Math).all()
        for each_math in math:
            # Update names
            for each_current, each_replacement in measurement_replacements.items():
                each_math.measure = each_math.measure.replace(each_current, each_replacement)

            for each_current, each_replacement in unit_replacements.items():
                each_math.measure_units = each_math.measure_units.replace(each_current, each_replacement)

            list_units = []
            if ',' in each_math.measure:
                # Set the default measurement values
                for each_measurement in MATH_INFO[each_math.math_type]['measure']:
                    if each_measurement in MEASUREMENT_UNITS:
                        add_custom_entry_from_math(
                            each_math,
                            each_measurement,
                            MEASUREMENT_UNITS[each_measurement]['units'][0])
                        entry = '{measure},{unit}'.format(
                            measure=each_measurement,
                            unit=MEASUREMENT_UNITS[each_measurement]['units'][0])
                        list_units.append(entry)
                each_math.measure_units = ";".join(list_units)
            else:
                add_custom_entry_from_math(
                    each_math,
                    each_math.measure,
                    each_math.measure_units)
                each_math.measure = each_math.measure
                each_math.measure_units = '{meas},{unit}'.format(
                    meas=each_math.measure, unit=each_math.measure_units)

        new_session.commit()


def downgrade():
    with op.batch_alter_table("pid") as batch_op:
        batch_op.drop_column('autotune_activated')
        batch_op.drop_column('autotune_noiseband')
        batch_op.drop_column('autotune_outstep')
