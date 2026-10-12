# Care Navigator

A runnable **synthetic-data MVP** for patient, caregiver, navigator, and organization-admin coordination. React/TypeScript, Django REST API, PostgreSQL. Administrative navigation of existing referrals; no clinical care or external integrations.

## Start in this cloud workspace

Node 24, Python 3.12, `uv`, and Chromium are available. PostgreSQL 17 is installed in a private user-owned runtime outside this checkout.

```bash
cd /workspace/care-navigator
./scripts/setup.sh
./scripts/start.sh
```

`setup.sh` installs exact locked dependencies, starts PostgreSQL if using the cloud default, applies migrations, seeds two fictional organizations without resetting existing work, and builds the frontend. `start.sh` starts Django on port 8000 and Vite on port 5173 and checks the API through the frontend proxy. Use the frontend through a locally supported browser workflow; this cloud onboarding UI does not provide localhost previews.

To stop or restart only these application services:

```bash
.venv/bin/python scripts/stop.py
./scripts/start.sh
```

PostgreSQL remains running. Service logs and process IDs are under `/workspace/care-navigator-runtime`. Live processes must be restarted in future tasks; use the existing isolated checkout rather than creating a worktree. Backend code changes require a restart (startup disables autoreload); Vite handles frontend edits.

## Run on another machine

Use Python 3.12+, Node 24, `uv`, and an existing PostgreSQL 17 database. The user-owned bootstrap script is specific to Debian 13 cloud workspaces. On other machines create the database using your platform's PostgreSQL tools, then export `PGHOST`, `PGUSER`, `PGDATABASE`, `PGPORT`, and (if needed) a private `PGPASSWORD`. Your development database role needs migration privileges and `CREATEDB` to run Django tests. No external API keys are required.

```bash
uv venv .venv
uv pip install --python .venv/bin/python -r backend/requirements.lock
npm ci --prefix frontend
# Export your private PostgreSQL settings first.
.venv/bin/python backend/manage.py migrate
.venv/bin/python backend/manage.py seed_demo
.venv/bin/python backend/manage.py runserver 127.0.0.1:8000
# In another terminal:
npm run dev --prefix frontend -- --host 127.0.0.1
```

`.env.example` lists supported settings. Copy to an ignored `.env` if desired, edit privately, and run `set -a; source .env; set +a` in each shell before starting commands. It is not automatically loaded. Never commit real secrets or real health information. Debug defaults and demo passwords are for local synthetic use only.

## Demo accounts and walkthrough

All seeded accounts use password **`DemoOnly-2026!`**. The `river` and `oak` organizations are isolated.

| Role | River City username | Oak Valley username |
|---|---|---|
| Patient | `river.patient` | `oak.patient` |
| Caregiver | `river.caregiver` | `oak.caregiver` |
| Navigator | `river.navigator` | `oak.navigator` |
| Organization admin | `river.admin` | `oak.admin` |

1. Sign in as `river.patient`. Review and accept service scope demo-v1. Seeded invitations are pre-provisioned; no invitation email is sent.
2. Open Intake. Enter an administrative goal, existing referral instructions, providers, coverage, barriers and communication needs. Save the deterministic demo summary, correct it, confirm it, and submit or Ask a navigator.
3. Speak/Type and Spoken responses are independent. Speech requires explicit permission and compatible browser support; external browser processing is disclosed. Typing works throughout. Say “Ask a navigator” to select a handoff, then confirm. Raw audio is not retained.
4. Sign in as `river.navigator`. Accept the request, create a task with owner/due date/barrier, and record separate exact-plan checks in Directory. Unknown, pending, verified, conflicting, and stale evidence are visible; all evidence is fictional.
5. Record a manual appointment and attendance. Advance each referral through review needed → sent → accepted → scheduling → scheduled → attended → follow-up received → closed. Closure requires evidence; booking alone cannot complete a referral. Record blocked/declined/canceled outcomes independently.
6. Sign in as patient to review progress, shared messages and tasks. Grant or revoke the separate caregiver's read/communication permissions in Access. Internal staff notes remain hidden.
7. Organization admins can manage seeded staff roles and service hours, import a fictional provider JSON array from `docs/directory-import.example.json`, and view organization-only audit metadata. Staff Reports computes synthetic operational measures from actual database records. In-app outbox items are unsent; failure simulation does not lose the request.

## Verification

Start services before browser checks. End-to-end tests add fictional records to the demo database; they use fresh keys/referrals and preserve existing records. Django tests use a separate disposable PostgreSQL test database.

```bash
.venv/bin/python backend/manage.py test navigation
npm test --prefix frontend
npm run build --prefix frontend
npm run test:e2e --prefix frontend
.venv/bin/python scripts/verify_restore.py
```

Playwright uses `/usr/bin/chromium` by default; set `CHROMIUM_PATH` for another installed Chromium. Screenshots and failure traces go to ignored `frontend/test-results`. See [validation](docs/VALIDATION.md) for executed checks, including accessibility limits.

## Scope and next steps

See [implementation plan, assumptions, permissions and backlog](docs/IMPLEMENTATION_PLAN.md), [architecture and limitations](docs/ARCHITECTURE.md), [backup/restore](docs/BACKUP.md), and the supplied [development brief](docs/DEVELOPMENT_BRIEF.md). The software development and integrated founding DOCX plans are context; this prototype deliberately defers commercial tiers, billing and care centers.

**Not for live patients.** Staff MFA, real invitation/recovery, rate limiting, secure hosting, clinical escalation review, vendor/privacy agreements, operational coverage, document handling, retention/deletion procedures, and independent accessibility testing remain launch prerequisites. No HIPAA-compliance, clinical-benefit, or cost-savings claim. No application has been deployed or published.
