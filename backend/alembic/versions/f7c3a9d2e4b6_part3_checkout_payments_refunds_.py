"""part3_checkout_payments_refunds_returns_reviews

Revision ID: f7c3a9d2e4b6
Revises: e6118c11ebbc
Create Date: 2026-10-08 09:15:00.000000

Part 3 backend schema: expanded order totals + lifecycle, DEMO payment
fundamentals (currency, provider, refund bookkeeping), coupon restrictions and
per-user limits, review moderation + verified flag, and the extended return
state machine.

NOTE: alembic autogenerate does not compare CHECK constraints — the check
constraints here are written by hand to match the SQLAlchemy models.
"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'f7c3a9d2e4b6'
down_revision: Union[str, None] = 'e6118c11ebbc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # Orders — backend-authoritative totals + immutable address snapshot.
    # ------------------------------------------------------------------
    op.add_column(
        'orders', sa.Column('subtotal', sa.Numeric(precision=10, scale=2),
                            nullable=False, server_default='0.00'))
    op.add_column(
        'orders', sa.Column('tax_amount', sa.Numeric(precision=10, scale=2),
                            nullable=False, server_default='0.00'))
    op.add_column(
        'orders', sa.Column('shipping_cost', sa.Numeric(precision=10, scale=2),
                            nullable=False, server_default='0.00'))
    op.add_column(
        'orders', sa.Column('shipping_method', sa.String(length=50),
                            nullable=False, server_default='standard'))
    op.add_column(
        'orders', sa.Column('shipping_address_snapshot', sa.Text(), nullable=True))
    op.add_column(
        'orders', sa.Column('tracking_number', sa.String(length=100), nullable=True))
    op.add_column(
        'orders', sa.Column('shipment_status', sa.String(length=20),
                            nullable=False, server_default='not_shipped'))
    op.alter_column('orders', 'subtotal', server_default=None)
    op.alter_column('orders', 'tax_amount', server_default=None)
    op.alter_column('orders', 'shipping_cost', server_default=None)

    # ------------------------------------------------------------------
    # DEMO payments — currency on the attempt, provider on the transaction.
    # ------------------------------------------------------------------
    op.add_column(
        'payments', sa.Column('currency', sa.String(length=3),
                              nullable=False, server_default='INR'))
    op.add_column(
        'payment_transactions', sa.Column('provider', sa.String(length=20),
                                          nullable=False, server_default='DEMO'))

    # ------------------------------------------------------------------
    # Refunds — idempotency key + demo provider reference.
    # ------------------------------------------------------------------
    op.add_column('refunds', sa.Column('idempotency_key', sa.String(length=100), nullable=True))
    op.add_column('refunds', sa.Column('provider_reference', sa.String(length=100), nullable=True))
    op.create_index(op.f('ix_refunds_idempotency_key'), 'refunds', ['idempotency_key'], unique=True)
    op.create_index(op.f('ix_refunds_provider_reference'), 'refunds', ['provider_reference'], unique=True)

    # ------------------------------------------------------------------
    # Coupons — caps, per-user limit, product/category restrictions.
    # ------------------------------------------------------------------
    op.add_column('coupons', sa.Column('max_discount_amount', sa.Numeric(precision=10, scale=2), nullable=True))
    op.add_column('coupons', sa.Column('per_user_limit', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('coupons', sa.Column('applies_to_product_ids', sa.Text(), nullable=True))
    op.add_column('coupons', sa.Column('applies_to_category_ids', sa.Text(), nullable=True))
    op.alter_column('coupons', 'per_user_limit', server_default=None)
    op.create_check_constraint(
        'ck_coupon_per_user_limit_positive', 'coupons', 'per_user_limit > 0'
    )

    # Per-user limit is enforced with a row lock at checkout, so the old
    # "one use per user" uniqueness constraint is dropped (it would cap every
    # coupon at 1 use/user regardless of per_user_limit).
    op.drop_constraint('uq_coupon_usage_per_user', 'coupon_usages', type_='unique')
    op.create_index('ix_coupon_usages_coupon_user', 'coupon_usages', ['coupon_id', 'user_id'], unique=False)

    # ------------------------------------------------------------------
    # Reviews — verified purchase flag + moderation gate.
    # ------------------------------------------------------------------
    op.add_column(
        'reviews', sa.Column('is_verified', sa.Boolean(),
                             nullable=False, server_default=sa.false()))
    op.add_column(
        'reviews', sa.Column('moderation_status', sa.String(length=20),
                             nullable=False, server_default='pending'))
    op.create_check_constraint(
        'ck_review_moderation_status', 'reviews',
        "moderation_status IN ('pending', 'approved', 'rejected')"
    )

    # ------------------------------------------------------------------
    # Returns — extended controlled state machine (add received/cancelled).
    # ------------------------------------------------------------------
    op.drop_constraint('ck_return_status', 'returns', type_='check')
    op.create_check_constraint(
        'ck_return_status', 'returns',
        "status IN ('requested', 'approved', 'rejected', 'received', "
        "'completed', 'cancelled')"
    )


def downgrade() -> None:
    op.drop_constraint('ck_return_status', 'returns', type_='check')
    op.create_check_constraint(
        'ck_return_status', 'returns',
        "status IN ('requested', 'approved', 'rejected', 'completed')"
    )

    op.drop_constraint('ck_review_moderation_status', 'reviews', type_='check')
    op.drop_column('reviews', 'moderation_status')
    op.drop_column('reviews', 'is_verified')

    op.drop_index('ix_coupon_usages_coupon_user', table_name='coupon_usages')
    op.create_unique_constraint('uq_coupon_usage_per_user', 'coupon_usages', ['coupon_id', 'user_id'])
    op.drop_constraint('ck_coupon_per_user_limit_positive', 'coupons', type_='check')
    op.drop_column('coupons', 'applies_to_category_ids')
    op.drop_column('coupons', 'applies_to_product_ids')
    op.drop_column('coupons', 'per_user_limit')
    op.drop_column('coupons', 'max_discount_amount')

    op.drop_index(op.f('ix_refunds_provider_reference'), table_name='refunds')
    op.drop_index(op.f('ix_refunds_idempotency_key'), table_name='refunds')
    op.drop_column('refunds', 'provider_reference')
    op.drop_column('refunds', 'idempotency_key')

    op.drop_column('payment_transactions', 'provider')
    op.drop_column('payments', 'currency')

    op.drop_column('orders', 'shipment_status')
    op.drop_column('orders', 'tracking_number')
    op.drop_column('orders', 'shipping_address_snapshot')
    op.drop_column('orders', 'shipping_method')
    op.drop_column('orders', 'shipping_cost')
    op.drop_column('orders', 'tax_amount')
    op.drop_column('orders', 'subtotal')
