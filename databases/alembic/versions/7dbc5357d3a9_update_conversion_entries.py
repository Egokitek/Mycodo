"""update conversion entries

Revision ID: 7dbc5357d3a9
Revises: f05ca91a4c65
Create Date: 2018-07-20 10:19:24.691605

"""

from alembic import op
import sqlalchemy as sa

import sys

import os

sys.path.append(os.path.abspath(os.path.join(__file__, "../../../..")))

from mycodo.databases.models import Input
from mycodo.databases.models import LCDData
from mycodo.databases.models import Math
from mycodo.databases.utils import session_scope
from mycodo.config import MATH_INFO
from mycodo.config_devices_units import MEASUREMENT_UNITS
from mycodo.config import SQL_DATABASE_MYCODO

MYCODO_DB_PATH = 'sqlite:///' + SQL_DATABASE_MYCODO

# revision identifiers, used by Alembic.
revision = '7dbc5357d3a9'
down_revision = 'f05ca91a4c65'
branch_labels = None
depends_on = None


def upgrade():
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

    # There has been a chance to how the measurement/unit selection for inputs is handled
    # There is a new naming convention for units, old unit names need to be renamed
    with session_scope(MYCODO_DB_PATH) as new_session:
        # Update LCD Data
        mod_lcd_data = new_session.query(LCDData).all()
        for each_lcd_data in mod_lcd_data:
            # Update names
            each_lcd_data.line_1_measurement = each_lcd_data.line_1_measurement.replace('duration_sec', 'duration_time')
            each_lcd_data.line_2_measurement = each_lcd_data.line_2_measurement.replace('duration_sec', 'duration_time')
            each_lcd_data.line_3_measurement = each_lcd_data.line_3_measurement.replace('duration_sec', 'duration_time')
            each_lcd_data.line_4_measurement = each_lcd_data.line_4_measurement.replace('duration_sec', 'duration_time')

        # Update Maths
        mod_math = new_session.query(Math).all()
        for each_math in mod_math:
            list_units = []
            if each_math.math_type == 'humidity':
                # Set the default measurement values
                for each_measurement in MATH_INFO[each_math.math_type]['measure']:
                    if each_measurement in MEASUREMENT_UNITS:
                        entry = '{measure},{unit}'.format(
                            measure=each_measurement,
                            unit=MEASUREMENT_UNITS[each_measurement]['units'][0])
                        list_units.append(entry)
                each_math.measure_units = ";".join(list_units)
            else:
                entry = '{measure},{unit}'.format(
                    measure=each_math.measure,
                    unit=each_math.measure_units)
                list_units.append(entry)
                each_math.measure_units = ";".join(list_units)

        # Update Inputs
        mod_input = new_session.query(Input).all()
        for each_input in mod_input:
            # Update names
            each_input.measurements = each_input.measurements.replace('duration_sec', 'duration_time')
            each_input.measurements = each_input.measurements.replace('lux', 'light')

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
                string_measure_units = string_measure_units.replace('sec', 'second')
                string_measure_units = string_measure_units.replace('celsius', 'C')
                string_measure_units = string_measure_units.replace('fahrenheit', 'F')
                string_measure_units = string_measure_units.replace('kelvin', 'K')
                string_measure_units = string_measure_units.replace('feet', 'ft')
                string_measure_units = string_measure_units.replace('kilopascals', 'kPa')
                string_measure_units = string_measure_units.replace('pascals', 'Pa')
                string_measure_units = string_measure_units.replace('meters', 'm')

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

        new_session.commit()


def downgrade():
    pass
