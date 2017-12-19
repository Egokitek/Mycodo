"""Add Math controller

Revision ID: b9712d4ec64e
Revises: 234283cc67f4
Create Date: 2017-12-02 19:29:23.378279

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b9712d4ec64e'
down_revision = '234283cc67f4'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("displayorder") as batch_op:
        batch_op.add_column(sa.Column('math', sa.Text))

    with op.batch_alter_table("graph") as batch_op:
        batch_op.add_column(sa.Column('math_ids', sa.Text))

    op.execute(
        '''
        UPDATE graph
        SET math_ids=''
        WHERE math_ids IS NULL
        '''
    )

    op.create_table(
        'math',
        sa.Column('id', sa.Integer, nullable=False, unique=True),
        sa.Column('unique_id', sa.String, nullable=False, unique=True),
        sa.Column('name', sa.Text),
        sa.Column('math_type', sa.Text),
        sa.Column('is_activated', sa.Boolean),
        sa.Column('inputs', sa.Text),
        sa.Column('period', sa.Float),
        sa.Column('max_measure_age', sa.Integer),
        sa.Column('measure', sa.Text),
        sa.Column('measure_units', sa.Text),
        sa.PrimaryKeyConstraint('id'), keep_existing=True)


def downgrade():
    op.drop_table('math')

    with op.batch_alter_table("displayorder") as batch_op:
        batch_op.drop_column('math')

    with op.batch_alter_table("graph") as batch_op:
        batch_op.drop_column('math_ids')
