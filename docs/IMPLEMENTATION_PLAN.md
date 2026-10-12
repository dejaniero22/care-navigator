# Implementation plan

Build a local synthetic-data MVP, following the supplied Codex prompt. The software plan is product context and the founding plan is business context; neither authorizes live services. The user's build request authorizes source changes and version control.

1. Prepare Django/REST/PostgreSQL and React/TypeScript with pinned dependencies.
2. Implement organization-scoped identity, enrollment, consent, grants, intake, navigator ownership, tasks, referrals, appointments, verification evidence, messages, time and audits.
3. Provide persistent patient/caregiver/staff screens with deterministic AI assistance and optional browser speech.
4. Exercise isolation, revocation, workflow rules, duplicates, failure paths, UI journeys and backup restoration.
5. Document runnable commands, actual test results and launch prerequisites; commit a reviewable increment.

## Assumptions

- Organization-funded administrative navigation by partner staff; two fictional Sacramento organizations.
- Existing specialist instructions only. EHR remains clinical system of record.
- Demo invitations are pre-provisioned accounts; users review a versioned service scope before intake.
- Service hours: weekdays 9–5 Pacific; response expectation: next business day. These are prototype assumptions, not staffed service promises.
- Verification stale after 30 days (configurable). Evidence is fictional; no payment guarantee.
- Manual appointments and status tracking; no live messages, payer, EHR, scheduling or AI APIs.
- Deterministic assistant cannot establish clinical safety. All requests can reach a human; clinical keywords add human review, never a diagnosis.
- Staff MFA absent: blocker for live use. Synthetic demo only; no compliance or clinical claims.

## Permissions matrix

| Capability | Patient | Caregiver | Navigator | Organization admin | Platform superuser |
|---|---|---|---|---|---|
| Patient records | Own | Active explicit read grant | Own organization | Own organization | No automatic access |
| Intake/messages | Own after consent | Explicit communication grant | Own organization | Own organization | No automatic access |
| Caregiver grant/revoke | Own | No | No | No | No |
| Referrals/tasks/verification/time | Read own | Read grant | Organization write | Organization write | No automatic access |
| Internal notes | No | No | Organization | Organization | No automatic access |
| Staff membership/service hours | No | No | No | Organization | No automatic access |
| Aggregate reports/audit | No | No | Reports only | Organization audit/report | No automatic access |
| Protected export | Own | No | No | Organization | No automatic access |

Patient and organization IDs supplied by clients are never authorization. Every nested lookup resolves through server-authorized patient access; no document uploads in this increment.

## Prioritized backlog

P0: usable end-to-end workflow; tenant isolation; scoped caregiver revocation; confirmed intake; human handoff; enforced transitions; audit; meaningful tests.
P1: responsive UI; manual directory checks; overdue tasks; operational metrics; backup/restore; accessible text alternatives.
Before live launch: staff MFA, invitation delivery/recovery, rate limiting, secure hosting, threat modeling, clinical escalation review, service staffing, vendor/privacy agreements, retention/deletion policy and independent accessibility/user testing.
Later: protected patient document ingestion/bulk patient import with validation; reviewed notification worker; integration contracts and reconciliation; external AI only after review. Billing, care centers and clinical services are out of scope.
