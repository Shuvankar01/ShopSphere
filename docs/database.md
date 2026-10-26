# Database

PostgreSQL required. Tables via Alembic. Key entities: users, roles, addresses, categories, brands, products, variants, images, inventory, cart, orders, payments, refunds, coupons, returns, reviews, notifications, banners, audit_logs. Foreign keys enforced, UTC timestamps, Decimal for money. Indexes on FKs/statuses as needed.
