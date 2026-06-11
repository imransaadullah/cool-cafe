"""Initial migration

Revision ID: 001
Revises: 
Create Date: 2026-06-05

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create branches table
    op.create_table(
        'branches',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('config', sa.JSON(), nullable=True),
        sa.Column('global_id', sa.Integer(), nullable=True),
        sa.Column('last_sync_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('global_id')
    )

    # Create admins table
    op.create_table(
        'admins',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('role', sa.String(length=50), nullable=False),
        sa.Column('branch_id', sa.Integer(), nullable=True),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('last_login_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['branch_id'], ['branches.id']),
        sa.ForeignKeyConstraint(['created_by_id'], ['admins.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username')
    )

    # Create sessions table
    op.create_table(
        'sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('pc_id', sa.Integer(), nullable=False),
        sa.Column('branch_id', sa.Integer(), nullable=False),
        sa.Column('code_id', sa.Integer(), nullable=True),
        sa.Column('start_time', sa.DateTime(), nullable=False),
        sa.Column('end_time', sa.DateTime(), nullable=True),
        sa.Column('paused_at', sa.DateTime(), nullable=True),
        sa.Column('total_paused_minutes', sa.Float(), nullable=True),
        sa.Column('duration_minutes', sa.Float(), nullable=False),
        sa.Column('remaining_minutes', sa.Float(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('amount_charged', sa.Float(), nullable=True),
        sa.Column('local_id', sa.String(length=100), nullable=True),
        sa.Column('synced', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('local_id')
    )

    # Create pcs table
    op.create_table(
        'pcs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('pc_number', sa.Integer(), nullable=False),
        sa.Column('branch_id', sa.Integer(), nullable=False),
        sa.Column('ip_address', sa.String(length=50), nullable=True),
        sa.Column('mac_address', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('last_heartbeat_at', sa.DateTime(), nullable=True),
        sa.Column('current_session_id', sa.Integer(), nullable=True),
        sa.Column('config', sa.String(length=500), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['branch_id'], ['branches.id']),
        sa.ForeignKeyConstraint(['current_session_id'], ['sessions.id']),
        sa.PrimaryKeyConstraint('id')
    )

    # Create code_batches table
    op.create_table(
        'code_batches',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('branch_id', sa.Integer(), nullable=False),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('batch_name', sa.String(length=100), nullable=True),
        sa.Column('count', sa.Integer(), nullable=False),
        sa.Column('duration_minutes', sa.Float(), nullable=False),
        sa.Column('value_per_code', sa.Float(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('printed', sa.Boolean(), nullable=True),
        sa.Column('printed_at', sa.DateTime(), nullable=True),
        sa.Column('local_id', sa.String(length=100), nullable=True),
        sa.Column('synced', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['branch_id'], ['branches.id']),
        sa.ForeignKeyConstraint(['created_by_id'], ['admins.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('local_id')
    )

    # Create codes table
    op.create_table(
        'codes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=20), nullable=False),
        sa.Column('duration_minutes', sa.Float(), nullable=False),
        sa.Column('batch_id', sa.Integer(), nullable=True),
        sa.Column('branch_id', sa.Integer(), nullable=False),
        sa.Column('is_used', sa.Boolean(), nullable=True),
        sa.Column('used_at', sa.DateTime(), nullable=True),
        sa.Column('used_by_session_id', sa.Integer(), nullable=True),
        sa.Column('value', sa.Float(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['batch_id'], ['code_batches.id']),
        sa.ForeignKeyConstraint(['branch_id'], ['branches.id']),
        sa.ForeignKeyConstraint(['used_by_session_id'], ['sessions.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )

    # Create payments table
    op.create_table(
        'payments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=True),
        sa.Column('branch_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(length=10), nullable=True),
        sa.Column('method', sa.String(length=50), nullable=False),
        sa.Column('reference', sa.String(length=255), nullable=True),
        sa.Column('payment_reference', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('local_id', sa.String(length=100), nullable=True),
        sa.Column('synced', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['branch_id'], ['branches.id']),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('local_id')
    )

    # Create revenue_reports table
    op.create_table(
        'revenue_reports',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('branch_id', sa.Integer(), nullable=False),
        sa.Column('report_date', sa.Date(), nullable=False),
        sa.Column('report_type', sa.String(length=20), nullable=True),
        sa.Column('total_revenue', sa.Float(), nullable=True),
        sa.Column('total_sessions', sa.Integer(), nullable=True),
        sa.Column('total_codes_used', sa.Integer(), nullable=True),
        sa.Column('total_paused_sessions', sa.Integer(), nullable=True),
        sa.Column('average_session_duration', sa.Float(), nullable=True),
        sa.Column('peak_hour_start', sa.Integer(), nullable=True),
        sa.Column('peak_hour_end', sa.Integer(), nullable=True),
        sa.Column('local_id', sa.String(length=100), nullable=True),
        sa.Column('synced', sa.Boolean(), nullable=True),
        sa.Column('generated_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['branch_id'], ['branches.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('local_id')
    )

    # Create filter_rules table
    op.create_table(
        'filter_rules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('branch_id', sa.Integer(), nullable=True),
        sa.Column('rule_type', sa.String(length=20), nullable=False),
        sa.Column('pattern', sa.String(length=500), nullable=False),
        sa.Column('action', sa.String(length=20), nullable=True),
        sa.Column('priority', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('local_id', sa.String(length=100), nullable=True),
        sa.Column('synced', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['branch_id'], ['branches.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('local_id')
    )

    # Create offline_queue table
    op.create_table(
        'offline_queue',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('action_type', sa.String(length=20), nullable=False),
        sa.Column('table_name', sa.String(length=100), nullable=False),
        sa.Column('record_id', sa.String(length=100), nullable=False),
        sa.Column('payload', sa.Text(), nullable=False),
        sa.Column('synced', sa.Boolean(), nullable=True),
        sa.Column('synced_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index(op.f('ix_admins_username'), 'admins', ['username'], unique=True)
    op.create_index(op.f('ix_codes_code'), 'codes', ['code'], unique=True)
    op.create_index(op.f('ix_pcs_branch_id'), 'pcs', ['branch_id'])
    op.create_index(op.f('ix_sessions_branch_id'), 'sessions', ['branch_id'])
    op.create_index(op.f('ix_sessions_pc_id'), 'sessions', ['pc_id'])


def downgrade() -> None:
    op.drop_table('offline_queue')
    op.drop_table('filter_rules')
    op.drop_table('revenue_reports')
    op.drop_table('payments')
    op.drop_table('codes')
    op.drop_table('code_batches')
    op.drop_table('pcs')
    op.drop_table('sessions')
    op.drop_table('admins')
    op.drop_table('branches')
