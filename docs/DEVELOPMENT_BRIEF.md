# Care Navigator Codex development prompt

Build the first working Care Navigator MVP in this repository. Use the attached Care_Navigator_Software_Development_Plan.docx as the product reference and Care_Navigation_Integrated_Founding_Plan.docx as business context. The requirements below make this prompt usable if those files are unavailable. Report missing references and proceed with this defined scope.

This request authorizes local development of a synthetic-data MVP. It does not authorize production deployment, real patient enrollment, real health information processing, external communications, paid services, or clinical care. Treat unresolved business and clinical decisions as documented prototype assumptions. Do not claim the application is HIPAA compliant, clinically validated, or ready for live patients.

## Outcome and working method

Deliver a runnable, database-backed application with patient, caregiver and navigator experiences. Complete an end-to-end workflow, not just a landing page, visual mockup, or plan.

Inspect the repository and applicable AGENTS.md instructions first. Preserve unrelated work. Before implementation, write a concise implementation plan, assumptions log, permissions matrix and prioritized backlog in the repository. Then build and verify the MVP. Make routine reversible choices independently; ask only when a missing answer blocks safe local implementation. Report actual limitations without fabricating integrations, AI output, verification results or completed tests.

Use the existing suitable repository stack if present. For a new repository, use React with TypeScript, Django with a REST API, and PostgreSQL. Favor a modular application over microservices. Select maintained dependencies using official documentation, pin dependencies, and provide migrations and reproducible setup. Do not introduce paid dependencies or require external API keys for the core demonstration.

## Prototype assumptions

An organization pays for the service and its staff supply navigation. The demonstration serves fictional Sacramento-region adults with existing specialist referrals. Include at least two fictional organizations to exercise isolation. Care Navigator coordinates administrative work; the partner EHR remains the clinical system of record. Keep organizations, service enrollments, responsible clinical entities and locations distinct. Do not build billing, care-center management or all future commercial tiers.

## Product experience

Create an accessible, calm, responsive interface with plain language, readable typography, clear status labels, and prominent next steps. Target WCAG 2.2 AA; report what was tested and what needs further review. Support keyboard navigation, visible focus, screen-reader labels, text resizing, adequate contrast, labeled errors and alternatives to speech. Avoid a chat-only interface: referrals, appointments and tasks need persistent structured views.

Implement these screens:

- Sign-in and invited-account onboarding with service scope and consent review.
- Patient home showing open requests, referrals, appointments and next steps.
- Text and voice intake, editable summary, confirmation and submission.
- Request and referral detail with progress, responsible owner and secure messages.
- Caregiver access management and communication preferences.
- Navigator queue, assigned caseload, patient coordination workspace and overdue tasks.
- Provider directory and plan-specific verification history.
- Organization administration for staff membership, assignment and service hours.
- Operational reporting and appropriately restricted audit history.

## Text speech and human assistance

Every essential patient workflow must work through text. Include bounded speech input and optional spoken responses. Input and output preferences are independent: users can speak and read, or type and listen. Switching modes must preserve the same draft, confirmed answers and progress without restarting.

Voice use requires explicit permission, a visible listening state, stop/cancel controls and correction before confirmation. Do not persist raw audio by default. Use a replaceable speech adapter. Implement actual speech only where the environment and provider permit it; clearly identify unavailable or demo functionality. If browser speech may send audio externally, disclose this before activation and restrict it to synthetic demonstrations. Do not silently activate a third-party processor.

Provide a visible Ask a navigator action and its spoken equivalent. A handoff creates a tracked request containing the confirmed summary, unresolved questions and authorized context. Show service hours, response expectations and a monitored fallback queue when no navigator is assigned. Do not imply continuous clinical or emergency monitoring.

## Coordination workflow and records

Intake captures the patient goal, existing referral instructions, known providers, coverage, communication needs and barriers. Distinguish patient statements, supplied instructions, AI drafts and human-approved information. Let users correct and confirm summaries before submission.

Submission enters an organization-scoped queue. A navigator accepts ownership and creates tasks with owners, due dates and barriers. Patient-facing views show actionable next steps; internal staff notes remain separate.

Model referrals with these states: draft, review needed, sent, accepted, scheduling, scheduled, attended, follow-up received and closed. Record blocked, declined and canceled outcomes separately. Enforce authorized transitions server-side and retain actor, timestamp and reason. Scheduling alone cannot mark a referral complete; closure requires documented follow-through or a valid alternative outcome. Appointments are tracked manually in this MVP; status changes do not send real referrals or book external appointments.

Provider records include specialty, location, contact details, accessibility information and source. Keep network participation, accepting new patients, benefit eligibility, referral requirements and prior authorization separate. Verification evidence is specific to patient plan, provider and location, with source, timestamp and verifier. Support unknown, pending, verified and conflicting states and flag stale evidence using a documented configurable policy. Never infer coverage from an identifier or display a payment guarantee. All seeded verification evidence must be visibly fictional. Preserve patient choice and exclude paid ranking.

Store consent versions, caregiver grants, service enrollment, tasks, referrals, appointments, messages, time entries and audit events. Time capture is operational and must not imply billability. Do not merge patients across organizations automatically.

## Authorization and privacy foundations

Use separate authenticated identities for patients, caregivers and staff. Caregiver access must be explicitly scoped and revocable; family relationships alone grant no access. Enforce organization membership and patient permissions on the server for every endpoint, nested resource, file and export. Do not trust client-supplied organization IDs. Platform administration must not automatically expose all patient records.

Use secure authentication, CSRF protection where applicable, input validation, safe session handling, secrets outside source control, restricted uploads and sanitized logs. Implement staff MFA through an appropriate supported approach, or identify its absence as a live-launch blocker. Recheck authorization when accessing files; avoid public patient-document URLs. Audit important reads, changes, grants, revocations, exports and status transitions without unnecessarily duplicating sensitive content. Use synthetic data only and separate development configuration from future production requirements.

## AI boundaries and integrations

Provide an AI adapter with a deterministic, clearly labeled demo implementation. The default app must run without an external model. AI may draft intake summaries, ask bounded administrative questions and explain recorded next steps. It cannot diagnose, choose a specialist from symptoms, give medication advice, invent availability, verify coverage, approve care plans or autonomously act.

Requests requiring clinical judgment create a human-review item and display service limits. Emergency instructions must be configurable and labeled as awaiting clinical review; do not market the prototype as triage. Treat documents and messages as untrusted input. AI must not override authorization or execute privileged operations. Any future model must receive only server-authorized minimum context. Preserve text and assisted workflows when AI or speech fails.

Use manual provider checks and protected local import/export. Do not connect live EHR, payer, scheduling, claims, email or SMS systems. Generic notifications may be demonstrated in an in-app outbox; label them unsent. Document future integration interfaces without pretending they exist.

## Acceptance and verification

Seed two organizations, patient and caregiver accounts, navigators, and a fictional patient with two specialist referrals. Demonstrate intake, confirmation, assignment, separate coverage checks, appointments, follow-through and patient-visible progress.

Add meaningful automated tests for:

- Organization and patient isolation, including guessed IDs, nested objects and exports.
- Caregiver revocation blocking subsequent access without removing the patient's access.
- Mode switching and independent input/output settings preserving draft state.
- Human handoff carrying confirmed information and excluding unauthorized/internal notes.
- Invalid referral transitions and premature closure being rejected.
- Duplicate submissions, stale/conflicting verification and failed notification handling.
- AI/speech failures preserving text access and unsafe clinical requests reaching human review.

Run appropriate backend, frontend and end-to-end checks. Inspect the main patient and navigator journeys at mobile and desktop sizes. Verify keyboard use and run available accessibility checks. Test a database backup and restoration when the runtime permits; otherwise document the precise blocker. Do not describe unchecked behavior as verified.

Show referral completion as completed referrals divided by referrals due in the selected period, with documented definitions and exclusions. Show intake completion, request-to-acceptance time, overdue tasks and recorded staff time using actual seeded records. Identify demonstration analytics as synthetic; make no claims of clinical benefit or cost savings.

## Deliverables

Deliver source code, migrations, synthetic seed data, automated tests, an example environment file, startup instructions, demo account instructions, and documentation covering architecture, permissions, assumptions, implemented scope, known gaps and live-launch prerequisites. Separate mocked services from implemented functionality. Include backup/restore guidance and a backlog for future clinical, security, vendor and integration reviews.

Finish with the exact commands to run the app, what works, tests actually executed, unresolved blockers, and the next development priorities. Do not deploy or publish. Continue until the defined local MVP is runnable and verified, or report a concrete environmental blocker with completed work preserved.
