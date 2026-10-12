# Architecture and implemented boundaries

## Components and data flow

One modular Django application serves a same-origin session/CSRF-protected REST API. React uses Vite's local proxy, not credential-bearing cross-origin requests. PostgreSQL persists all coordination records. Server-side authorization resolves membership and patient access on every request and nested lookup. Client organization IDs have no authority. Platform superuser status alone grants no patient access.

`navigation/models.py` contains distinct organizations, memberships, patient profiles, service enrollments (clinical entity and location remain distinct), versioned consents, caregiver grants, intake drafts/submissions, referrals and transition history, tasks, appointments, directory providers, plan/provider/location-specific evidence, shared/internal messages, staff time, unsent notifications and content-minimizing audit metadata. Schema changes use checked-in Django migrations.

`navigation/views.py` exposes authenticated API workflows and authorization checks. Per-patient transactional locking protects duplicate submissions and assignment races. Request keys are patient-scoped UUIDs with a database uniqueness constraint. Dates, timestamps, enumerations, input lengths, positive numbers, resource relationships and staff roles are validated server-side. Secrets are process configuration, not source. Sessions use HttpOnly/SameSite cookies, CSRF protection and finite lifetimes; secure cookies apply outside local debug configuration. Real production hosting is not configured.

The default PostgreSQL server accepts only a Unix socket in a user-owned mode-700 directory. It has no TCP listener; local trust is for this isolated synthetic workspace only. Network-accessible production authentication would require separate review/configuration. Dependencies and lockfiles are pinned from official package registries; local PostgreSQL bootstrap uses signed Debian metadata and verified downloads. No verification bypasses.

## API contract

| Endpoint | Purpose |
|---|---|
| GET `/api/session/` | Current identity/scope and CSRF cookie; anonymous allowed |
| POST `/api/login/`, `/api/logout/` | Session authentication; CSRF required |
| GET `/api/dashboard/` | Authorized queue/caseload counts only |
| GET `/api/patients/{id}/` | Authorized structured workspace; internal notes staff only |
| POST `/api/patients/{id}/actions/` | Validated workflow actions; nested IDs resolve within patient/organization |
| GET `/api/patients/{id}/export/` | Patient-own or organization-admin JSON export; no public URL |
| GET/POST `/api/organization/` | Organization-admin staff-role/service-hours management |
| GET `/api/reports/?start=YYYY-MM-DD&end=YYYY-MM-DD` | Organization staff aggregate measures |
| POST `/api/directory-import/` | Organization-admin-only bounded fictional directory JSON import |
| GET `/api/audit/` | Organization-admin-only most recent 200 audit events |

Supported actions: consent, preferences, grant, revoke, draft, submit, handoff, accept, referral, transition, outcome, task, task_done, appointment, appointment_status, verify, message, time, notification_failure. Mutations record actor/action/object metadata, not duplicate sensitive content. Important reads and exports are audited. Authorization is checked anew after caregiver revocation.

The JSON export requires an authenticated session and carries no internal notes for patient accounts. No file-upload/document endpoints are exposed; no public patient-document URLs exist. Organization admins can import 1–50 validated fictional directory rows through the API or Organization screen; client organization IDs are ignored, the whole import is atomic, and the event is audited. `docs/directory-import.example.json` supplies a local sample. Patient bulk import/document storage are backlog items. Administrators can update roles of existing organization staff, but cannot turn a patient/caregiver identity into staff. Staff invitations are seeded rather than delivered. Assignment is same-organization and request acceptance records owner/timestamp.

## AI and speech

`DemoAI` simply formats user-entered administrative facts into a clearly labeled draft. It sends no external API requests and performs no privileged operations. Confirmation persists the patient's corrected summary. Clinical keywords request human review; this convenience rule is **not triage**, does not detect every clinical concern, and does not certify safety. Every intake can request a human. Handoff consists only of the confirmed summary, patient-entered context and unresolved questions; internal notes are excluded. Emergency wording is configurable and always labeled as awaiting clinical review.

The replaceable browser speech adapter is optional, permission-gated, bounded to one utterance, and exposes listening/stop/cancel/correction. Browser providers may process audio externally; consent explains this and limits use to fictional information. No raw audio is stored. Text intake remains functional through speech/AI failure. Real microphone transcription and speech-provider privacy/quality were not validated in this headless environment.

## Provider evidence and metrics

No paid ranking: directory follows insertion order with no commercial scoring. Each evidence row records one dimension (network participation, new-patient acceptance, benefit eligibility, referral requirement or prior authorization), exact plan/provider/location, fictional source, verifier and timestamp. Rows are retained as history. Unknown, pending, verified and explicitly conflicting states remain separate. No evidence implies availability or payment guarantees. Staleness threshold is `VERIFICATION_STALE_DAYS` (default 30); directory newest-first views flag age. A navigator must assess conflicting sources; automatic evidence reconciliation is deferred.

Reports select inclusive referral due dates and intake start dates. Completion numerator is closed referrals with follow-through (no declined/canceled outcome); denominator excludes explicitly declined/canceled referrals and reports exclusions separately. All-due completion is also provided; blocked cases remain included. Intake completion provides submitted and started counts; draft-only cases remain in denominator. Acceptance median uses recorded submission/acceptance times, with no value when no observations exist. Overdue tasks are open with due date before today. Staff minutes are summed in the selected period and are never called billable. All analytics are synthetic and imply no clinical benefit/cost reduction.

## Production prerequisites and future interfaces

No live EHR, payer, scheduling, claims, email/SMS or model connections exist. Manual tracking cannot send real referrals or book visits. Outbox states are unsent/failed-demo; no worker or delivery guarantee. A future notification adapter must accept generic authorized references, retry idempotently and retain failures. EHR/payer adapters need scoped authorization, source/version provenance, reconciliation and reviewed vendor contracts; future AI receives only server-authorized minimum context. Documents/messages remain untrusted content and cannot grant permissions or execute operations.

Live launch blockers: staff MFA via reviewed supported identity provider; invitation/recovery and rate limiting; TLS and production secret/host/session configuration; retention/deletion/termination procedures; patient document/import security; qualified clinical escalation and emergency wording; operational service coverage; privacy applicability/risk analysis and agreements; security assessment and independent accessibility/user testing. Legal/commercial ownership, payment structure and responsible clinical entities remain unresolved prototype assumptions. No production deployment is authorized by this work.
