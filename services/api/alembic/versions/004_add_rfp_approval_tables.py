"""add rfp approval tables

Revision ID: 004_rfp_approval
Revises: 003
Create Date: 2026-11-17

Tablas para Parte 3 del sistema RFP:
- department_approvals: Aprobaciones departamentales con HITL
- conflict_records: Registro de conflictos entre departamentos
- final_documents: Documentos finales consolidados
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, ENUM


# revision identifiers, used by Alembic.
revision = '004_rfp_approval'
down_revision = '003'  # Ajustar según última migración real
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Crear ENUMs
    approval_status_enum = ENUM(
        'pending', 'approved', 'rejected', 'changes_requested',
        name='approvalstatus',
        create_type=False
    )
    approval_status_enum.create(op.get_bind(), checkfirst=True)

    conflict_severity_enum = ENUM(
        'low', 'medium', 'high', 'critical',
        name='conflictseverity',
        create_type=False
    )
    conflict_severity_enum.create(op.get_bind(), checkfirst=True)

    human_decision_enum = ENUM(
        'aprobar', 'rechazar', 'solicitar_cambios',
        name='humanapprovaldecision',
        create_type=False
    )
    human_decision_enum.create(op.get_bind(), checkfirst=True)

    arbitration_decision_enum = ENUM(
        'aprobar_version_a', 'aprobar_version_b', 'merge_both',
        'request_rewrite', 'escalate_to_ceo',
        name='arbitrationdecision',
        create_type=False
    )
    arbitration_decision_enum.create(op.get_bind(), checkfirst=True)

    # TABLA 1: department_approvals
    op.create_table(
        'department_approvals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticket_id', sa.Integer(), nullable=False),
        sa.Column('department', sa.String(), nullable=False),
        sa.Column('draft_section_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='pending'),
        sa.Column('reviewer_name', sa.String(), nullable=False),
        sa.Column('reviewer_role', sa.String(), nullable=False),
        sa.Column('checkpoint_thread_id', sa.String(), nullable=False),
        sa.Column('interrupted_at', sa.DateTime(), nullable=True),
        sa.Column('resumed_at', sa.DateTime(), nullable=True),
        sa.Column('human_decision', sa.String(), nullable=True),
        sa.Column('human_feedback', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['ticket_id'], ['rfp_tickets.id'], ),
        sa.ForeignKeyConstraint(['draft_section_id'], ['draft_sections.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_department_approvals_ticket_id'), 'department_approvals', ['ticket_id'], unique=False)
    op.create_index(op.f('ix_department_approvals_department'), 'department_approvals', ['department'], unique=False)

    # TABLA 2: conflict_records
    op.create_table(
        'conflict_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticket_id', sa.Integer(), nullable=False),
        sa.Column('department_a', sa.String(), nullable=False),
        sa.Column('department_b', sa.String(), nullable=False),
        sa.Column('conflict_type', sa.String(), nullable=False),
        sa.Column('severity', sa.String(), nullable=False),
        sa.Column('conflict_description', sa.String(), nullable=False),
        sa.Column('department_a_position', sa.String(), nullable=False),
        sa.Column('department_b_position', sa.String(), nullable=False),
        sa.Column('requires_arbitration', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('arbitrator_name', sa.String(), nullable=True),
        sa.Column('arbitration_decision', sa.String(), nullable=True),
        sa.Column('arbitration_rationale', sa.String(), nullable=True),
        sa.Column('is_resolved', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['ticket_id'], ['rfp_tickets.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_conflict_records_ticket_id'), 'conflict_records', ['ticket_id'], unique=False)

    # TABLA 3: final_documents
    op.create_table(
        'final_documents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticket_id', sa.Integer(), nullable=False),
        sa.Column('executive_summary', sa.String(), nullable=False),
        sa.Column('full_proposal_markdown', sa.String(), nullable=False),
        sa.Column('full_proposal_html', sa.String(), nullable=True),
        sa.Column('approved_sections', JSONB, nullable=False, server_default='{}'),
        sa.Column('total_estimated_cost_usd', sa.Float(), nullable=True),
        sa.Column('total_person_days', sa.Integer(), nullable=True),
        sa.Column('estimated_delivery_date', sa.String(), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('is_latest', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('exported_to_pdf', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('pdf_path', sa.String(), nullable=True),
        sa.Column('exported_to_word', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('word_path', sa.String(), nullable=True),
        sa.Column('generated_by_agent', sa.String(), nullable=False, server_default='Ultimate Document Synthesizer'),
        sa.Column('generated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('signed_by', sa.String(), nullable=True),
        sa.Column('signed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['ticket_id'], ['rfp_tickets.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_final_documents_ticket_id'), 'final_documents', ['ticket_id'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_final_documents_ticket_id'), table_name='final_documents')
    op.drop_table('final_documents')

    op.drop_index(op.f('ix_conflict_records_ticket_id'), table_name='conflict_records')
    op.drop_table('conflict_records')

    op.drop_index(op.f('ix_department_approvals_department'), table_name='department_approvals')
    op.drop_index(op.f('ix_department_approvals_ticket_id'), table_name='department_approvals')
    op.drop_table('department_approvals')

    # Drop ENUMs
    sa.Enum(name='arbitrationdecision').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='humanapprovaldecision').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='conflictseverity').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='approvalstatus').drop(op.get_bind(), checkfirst=True)
