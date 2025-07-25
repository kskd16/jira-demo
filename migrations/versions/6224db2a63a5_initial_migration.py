"""Initial migration

Revision ID: 6224db2a63a5
Revises: 
Create Date: 2025-07-21 04:04:07.329438

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6224db2a63a5'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('team',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=50), nullable=False),
    sa.Column('manager_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['manager_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_table('user',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('email', sa.String(length=120), nullable=False),
    sa.Column('password', sa.String(length=200), nullable=False),
    sa.Column('role', sa.String(length=20), nullable=False),
    sa.Column('team_id', sa.Integer(), nullable=True),
    sa.Column('approved', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['team_id'], ['team.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email')
    )
    op.create_table('project',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('team_lead_id', sa.Integer(), nullable=True),
    sa.Column('start_date', sa.Date(), nullable=True),
    sa.Column('deadline', sa.Date(), nullable=True),
    sa.Column('status', sa.String(length=50), nullable=True),
    sa.ForeignKeyConstraint(['team_lead_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_table('ticket',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('type', sa.String(length=50), nullable=False),
    sa.Column('priority', sa.String(length=50), nullable=False),
    sa.Column('assignee', sa.String(length=100), nullable=False),
    sa.Column('status', sa.String(length=50), nullable=True),
    sa.Column('public', sa.Boolean(), nullable=False),
    sa.Column('project_id', sa.Integer(), nullable=True),
    sa.Column('start_date', sa.Date(), nullable=True),
    sa.Column('end_date', sa.Date(), nullable=True),
    sa.ForeignKeyConstraint(['project_id'], ['project.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('ticket')
    op.drop_table('project')
    op.drop_table('user')
    op.drop_table('team')
    # ### end Alembic commands ###
