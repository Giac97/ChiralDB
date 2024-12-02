"""Added group

Revision ID: 12c8a7ea1853
Revises: 5253ac588b85
Create Date: 2024-10-10 15:38:03.185313

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '12c8a7ea1853'
down_revision = '5253ac588b85'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('affiliation', sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column('resgroup', sa.Integer(), nullable=True))
        batch_op.drop_constraint('users_group_fkey', type_='foreignkey')
        batch_op.create_foreign_key(None, 'researchgroup', ['resgroup'], ['id'])
        batch_op.drop_column('group')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('group', sa.INTEGER(), autoincrement=False, nullable=True))
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.create_foreign_key('users_group_fkey', 'researchgroup', ['group'], ['id'])
        batch_op.drop_column('resgroup')
        batch_op.drop_column('affiliation')

    # ### end Alembic commands ###