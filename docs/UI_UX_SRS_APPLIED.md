# Production Backend UI/UX SRS (excerpt applied)

Source follow-up requirements incorporated into the React ops consoles:

- Financial-first ops shell (top bar + grouped Operations / Configuration / Finance nav)
- Progressive disclosure on transaction detail (summary → fee/commission → timeline)
- `tenant_id` / geographic resolution handled by session + backend (not free-form form fields)
- Access + refresh token session with silent refresh
- Argon2 password hashing on backend
- Mobile-friendly ops and public layouts
- Tests under `backend/tests/{regression,uat}` and `frontend/tests/{regression,uat}`
