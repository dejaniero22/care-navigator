# Validation evidence

Executed against this cloud instance using PostgreSQL 17.11, Python 3.12.14, Node 24.19.0 and system Chromium 154. Synthetic data only. The supplied DOCX documents were used as product/business context; the development brief defined the local build scope.

| Check | Actual result |
|---|---|
| `python backend/manage.py test navigation` through `.venv` | 21 tests executed, passed; separate disposable PostgreSQL test database |
| `npm test --prefix frontend` | 4 frontend tests executed, passed |
| `npm run build --prefix frontend` | TypeScript check and Vite production build passed |
| `npm run test:e2e --prefix frontend` | 4 tests executed, passed: two journeys each at 1440×1000 and 390×844 |
| `python scripts/verify_restore.py` through `.venv` | Backup restored to fresh disposable database; all 26 tables and 613 rows matched consistent source snapshot in final run |
| `python backend/manage.py makemigrations --check --dry-run` through `.venv` | No missing migrations |
| `./scripts/setup.sh` repeat run | Locked installs, migrations, non-destructive seed and build succeeded; existing records preserved |
| `python scripts/stop.py` then `./scripts/start.sh` through `.venv` | Project services stopped/restarted; JSON session endpoint responds through Vite proxy |
| `npm audit --prefix frontend --audit-level=high` | Zero reported vulnerabilities, including development dependencies |
| `pip-audit --disable-pip --no-deps -r backend/requirements.lock` | All exact frozen dependencies audited; no known vulnerabilities after Django/DRF updates |

Backend checks exercise organization and same-organization patient isolation, guessed IDs/nested resources/provider IDs/staff assignment/export, platform-superuser non-access, revoked caregiver access on subsequent requests, read-only caregiver restrictions, hidden internal notes, CSRF and session authentication, consent/confirmation requirements, duplicate submission, authorized handoff context, clinical concern routing, deterministic AI failure fallback, invalid transitions/premature closure, evidenced alternative closure, separate blocked outcomes, stale/conflicting evidence, failed outbox simulation, complete assignment/task/appointment/time reporting, organization/admin audit permissions, inactive enrollment, invalid input, and organization-scoped atomic directory imports.

Frontend unit tests exercise independent input/output mode choices while preserving draft/confirmation, explicit speech permission and failure fallback, AI failure followed by typed handoff, and invalidating confirmation after editing. Speech is tested with a replaceable fake adapter; these tests do not establish real microphone/provider performance.

Browser checks sign in, confirm consent when needed, draft/edit/confirm intake, switch modes without losing progress, request human handoff, accept navigator ownership, create tasks and a fresh referral, manually record appointment and attendance, advance through follow-up and evidence-based closure, view patient progress and shared messages, revoke an already-authenticated caregiver then verify subsequent access is blocked, restore the grant through the patient, use keyboard-only sign-in, inspect organization/audit views, and verify mobile reflow at 200% root text size. The browser runs add fictional demonstration records rather than clearing user work. Screenshots of patient and navigator journeys were captured; patient desktop/mobile screenshots were visually inspected.

Axe checks using WCAG 2/2.1/2.2 A/AA tags reported zero violations on the scanned patient home/intake, staff referral/report, organization-admin and audit screens in both viewport sizes. A discovered unfocusable horizontal audit-table scroll region was corrected, as was mobile heading overflow at 200% text size. Initial Vite-to-Django CSRF origin failure was corrected with local development-only trusted origins; CSRF protection remains enabled. Backend and frontend tests were rerun after dependency updates.

## Limits of verification

- Automated scans and a keyboard journey are not comprehensive WCAG conformance or assistive-technology/user validation. Screen readers, real users, all browser engines, high-contrast modes, and broader authentication/error flows require further testing.
- Real microphone transcription/read-aloud quality and browser speech vendor behavior were not exercised in headless Chromium. Text and adapter-failure paths were tested.
- Local synthetic invitations are seeded. Real invitation delivery, staff MFA, account recovery, abuse/rate controls and production authentication are not implemented.
- No live patient, external EHR/payer/booking/notification/claims/model behavior was exercised or represented as implemented. Outbox delivery is unsent or simulated failure.
- Directory import and authenticated JSON export are implemented; patient-document upload and bulk patient import remain unavailable.
- The backup check demonstrates current local database integrity and restoration; production offsite recovery, encryption, retention and recovery ownership remain unvalidated.
- Production hosting, security/clinical/legal/vendor review, staffed support and real enrollment are not ready. No application deployment/publication occurred.
- Future-task restoration from a published cloud snapshot has not been independently verified. Saved setup instructions and current-instance verification are separate from publication.
