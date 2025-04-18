"""Added fields for pubchem

Revision ID: e646fea38815
Revises: e8080ef33c02
Create Date: 2024-10-11 14:27:51.996545

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e646fea38815'
down_revision = 'e8080ef33c02'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('molecule', schema=None) as batch_op:
        batch_op.add_column(sa.Column('pubchem_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('molecular_weight', sa.Float(), nullable=False))
        batch_op.add_column(sa.Column('iupac_name', sa.String(length=150), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('molecule', schema=None) as batch_op:
        batch_op.drop_column('iupac_name')
        batch_op.drop_column('molecular_weight')
        batch_op.drop_column('pubchem_id')

    # ### end Alembic commands ###
