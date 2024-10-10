"""Added username

Revision ID: 19432b8f3f06
Revises: 47d2f117c44e
Create Date: 2024-10-09 10:58:32.302578

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '19432b8f3f06'
down_revision = '47d2f117c44e'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('username', sa.String(length=100), nullable=False))
        batch_op.create_unique_constraint(None, ['username'])

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='unique')
        batch_op.drop_column('username')

    # ### end Alembic commands ###
