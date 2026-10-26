# Payments (DEMO ONLY)

- DEMO/MOCK PAYMENT ONLY. No real money, no Stripe, no Razorpay, no real payment credentials, no real transactions.
- Two-phase: create pending transaction; client completes as success/failure/cancel; server re-validates.
- Idempotent webhook handling (demo). Refunds bound to captured amounts.
