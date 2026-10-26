# Security

- Server-side authorization on admin/seller routes; IDOR prevention; no trust of frontend.
- Brute-force protection via existing middlewares; security headers applied.
- Audit logging for important admin actions (no passwords/tokens/secrets).
- Input validation with Pydantic; safe file upload constraints.
- Money totals computed server-side only.
