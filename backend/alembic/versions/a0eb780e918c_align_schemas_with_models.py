"""align audit_logs / banners / notifications with the SQLAlchemy models

Revision ID: a0eb780e918c
Revises: f7c3a9d2e4b6
Create Date: 2026-10-22 19:22:08.927381

Three independent model/schema drifts are fixed here. All three caused live
HTTP 500s because the runtime SELECT/INSERT referenced columns the database
never had (or required columns the models never supplied).

1. `audit_logs` — two model classes (`app/models/audit.py` and
   `app/models/audit_log.py`) were mapped to the same `__tablename__`. With
   `extend_existing=True` SQLAlchemy merged their column sets into one Table,
   so the runtime SELECT referenced `actor_id` / `actor_email` / `entity` /
   `details` / `user_agent`, none of which the migration had ever created
   (GET /api/admin/audit-logs -> 500). The duplicate model has been deleted;
   `app/models/audit.py` is now the single canonical mapping and gains the
   denormalized actor/entity columns the audit repository actually writes.
   `entity_type` becomes nullable because the repository never populates it.

2. `banners` — the migration created `image_url VARCHAR(1000) NOT NULL`,
   `subtitle` and `sort_order NOT NULL`, but the model only knows `image_url`
   (Text, nullable) and has no `subtitle` / `sort_order` columns. Every
   INSERT therefore violated the NOT NULL constraints (POST /api/banners ->
   500). `subtitle` and `sort_order` are unused by both the backend schemas and
   the frontend, so they are dropped; `image_url` is widened to Text and made
   nullable to match `BannerCreate.image_url`, which is optional.

3. `notifications` — the migration made `type` NOT NULL while the model and
   `NotificationResponse` treat it as optional, and left `body` nullable while
   the model requires it. `link` was never in the model. `body` is tightened
   to NOT NULL (no rows are affected — the table is empty at migration time).

The `ix_notifications_user_unread` index is kept: it is now declared on the
model, since it backs the unread-count query.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a0eb780e918c'
down_revision: Union[str, None] = 'f7c3a9d2e4b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- audit_logs: add the columns the audit repository writes -------------
    op.add_column('audit_logs', sa.Column('actor_id', sa.String(), nullable=True))
    op.add_column('audit_logs', sa.Column('actor_email', sa.String(length=255), nullable=True))
    op.add_column('audit_logs', sa.Column('entity', sa.String(length=100), nullable=True))
    op.add_column('audit_logs', sa.Column('details', sa.Text(), nullable=True))
    op.add_column('audit_logs', sa.Column('user_agent', sa.Text(), nullable=True))
    op.alter_column('audit_logs', 'entity_type',
                    existing_type=sa.VARCHAR(length=100),
                    nullable=True)

    # --- banners: match the model (optional image_url, no subtitle/order) ---
    op.alter_column('banners', 'image_url',
                    existing_type=sa.VARCHAR(length=1000),
                    type_=sa.Text(),
                    existing_nullable=False,
                    nullable=True)
    op.alter_column('banners', 'link_url',
                    existing_type=sa.VARCHAR(length=1000),
                    type_=sa.Text(),
                    existing_nullable=True,
                    nullable=True)
    op.drop_column('banners', 'subtitle')
    op.drop_column('banners', 'sort_order')

    # --- notifications: `type` optional, `body` required, no `link` ---------
    op.alter_column('notifications', 'body',
                    existing_type=sa.TEXT(),
                    nullable=False)
    op.alter_column('notifications', 'type',
                    existing_type=sa.VARCHAR(length=50),
                    nullable=True)
    op.drop_column('notifications', 'link')


def downgrade() -> None:
    # --- notifications: restore the previous shape --------------------------
    op.add_column('notifications', sa.Column('link', sa.VARCHAR(length=1000), autoincrement=False, nullable=True))
    op.alter_column('notifications', 'type',
                    existing_type=sa.VARCHAR(length=50),
                    nullable=False)
    op.alter_column('notifications', 'body',
                    existing_type=sa.TEXT(),
                    nullable=True)

    # --- banners: restore the previous shape --------------------------------
    op.add_column('banners', sa.Column('sort_order', sa.Integer(), autoincrement=False, nullable=False))
    op.add_column('banners', sa.Column('subtitle', sa.VARCHAR(length=500), autoincrement=False, nullable=True))
    op.alter_column('banners', 'link_url',
                    existing_type=sa.Text(),
                    type_=sa.VARCHAR(length=1000),
                    existing_nullable=True,
                    nullable=True)
    op.alter_column('banners', 'image_url',
                    existing_type=sa.Text(),
                    type_=sa.VARCHAR(length=1000),
                    existing_nullable=True,
                    nullable=False)

    # --- audit_logs: remove the added columns -------------------------------
    op.alter_column('audit_logs', 'entity_type',
                    existing_type=sa.VARCHAR(length=100),
                    nullable=False)
    op.drop_column('audit_logs', 'user_agent')
    op.drop_column('audit_logs', 'details')
    op.drop_column('audit_logs', 'entity')
    op.drop_column('audit_logs', 'actor_email')
    op.drop_column('audit_logs', 'actor_id')
