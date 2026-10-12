import uuid
from datetime import timedelta
from unittest.mock import patch
from django.test import TestCase, Client
from django.core.management import call_command
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APIClient
from .models import *


class CoordinationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", verbosity=0)
        cls.p = Patient.objects.get(user__username="river.patient")
        cls.other = Patient.objects.get(user__username="oak.patient")
        cls.nav = User.objects.get(username="river.navigator")
        cls.ref = Referral.objects.filter(patient=cls.p).first()

    def setUp(self):
        self.client = APIClient()

    def as_user(self, name):
        self.client.force_authenticate(User.objects.get(username=name))

    def act(self, action, **kw):
        return self.client.post(
            f"/api/patients/{self.p.id}/actions/",
            {"action": action, **kw},
            format="json",
        )

    def intake_data(self):
        return {
            "key": str(uuid.uuid4()),
            "goal": "Help arrange my existing neurology referral",
            "instructions": "Existing fictional clinician referral",
            "providers": "Demo neurology",
            "coverage": self.p.plan,
            "barriers": "Transport",
            "communication_needs": "Text",
            "summary": "Confirmed administrative help with existing neurology referral",
            "unresolved_questions": "Transport options?",
            "confirmed": True,
        }

    def consent(self):
        self.as_user("river.patient")
        self.assertEqual(self.act("consent", accepted=True).status_code, 200)

    def test_patient_and_organization_guessed_ids(self):
        for role in ["patient", "caregiver", "navigator", "admin"]:
            self.as_user("river." + role)
            for endpoint in ["", "export/"]:
                self.assertEqual(
                    self.client.get(
                        f"/api/patients/{self.other.id}/{endpoint}"
                    ).status_code,
                    404,
                )
            self.assertEqual(
                self.client.post(
                    f"/api/patients/{self.other.id}/actions/",
                    {"action": "message", "body": "x", "internal": False},
                    format="json",
                ).status_code,
                404,
            )
            dash = self.client.get("/api/dashboard/").json()
            self.assertEqual([x["id"] for x in dash["patients"]], [self.p.id])

    def test_same_org_patient_isolation(self):
        u = User.objects.create_user("river.second", password="test")
        Membership.objects.create(
            user=u, organization=self.p.organization, role="patient"
        )
        p = Patient.objects.create(
            user=u,
            organization=self.p.organization,
            name="Second fictional patient",
            plan="Demo",
        )
        Enrollment.objects.create(patient=p)
        self.as_user("river.patient")
        self.assertEqual(self.client.get(f"/api/patients/{p.id}/").status_code, 404)
        self.assertEqual(
            self.client.get(f"/api/patients/{p.id}/export/").status_code, 404
        )

    def test_nested_and_provider_id_isolation(self):
        self.as_user("river.navigator")
        otherref = Referral.objects.filter(patient=self.other).first()
        self.assertEqual(
            self.act(
                "transition",
                id=otherref.id,
                state="sent",
                outcome="none",
                reason="x",
                evidence="",
            ).status_code,
            404,
        )
        self.assertEqual(
            self.act(
                "appointment",
                referral_id=otherref.id,
                location="Demo",
                starts_at=timezone.now().isoformat(),
            ).status_code,
            404,
        )
        pr = Provider.objects.filter(organization=self.other.organization).first()
        self.assertEqual(
            self.act(
                "verify",
                provider_id=pr.id,
                dimension="network participation",
                status="verified",
                source="fake",
            ).status_code,
            404,
        )
        otherstaff = User.objects.get(username="oak.navigator")
        self.assertEqual(
            self.act(
                "task", owner_id=otherstaff.id, title="x", due_date="2026-12-01"
            ).status_code,
            404,
        )

    def test_platform_admin_has_no_automatic_access(self):
        u = User.objects.create_superuser(
            "platform", "platform@example.invalid", "test"
        )
        self.client.force_authenticate(u)
        self.assertEqual(
            self.client.get(f"/api/patients/{self.p.id}/").status_code, 403
        )
        self.assertEqual(self.client.get("/api/audit/").status_code, 403)

    def test_revocation_rechecked_and_patient_retained(self):
        self.as_user("river.caregiver")
        self.assertEqual(
            self.client.get(f"/api/patients/{self.p.id}/").status_code, 200
        )
        self.as_user("river.patient")
        grant = CaregiverGrant.objects.get(patient=self.p)
        self.assertEqual(self.act("revoke", id=grant.id).status_code, 200)
        self.as_user("river.caregiver")
        self.assertEqual(
            self.client.get(f"/api/patients/{self.p.id}/").status_code, 404
        )
        self.assertEqual(self.act("message", body="x", internal=False).status_code, 404)
        self.as_user("river.patient")
        self.assertEqual(
            self.client.get(f"/api/patients/{self.p.id}/").status_code, 200
        )

    def test_read_only_grant_and_hidden_internal_notes(self):
        CaregiverGrant.objects.filter(patient=self.p).update(can_message=False)
        self.as_user("river.caregiver")
        data = self.client.get(f"/api/patients/{self.p.id}/").json()
        self.assertFalse(any(x["internal"] for x in data["messages"]))
        self.assertEqual(self.act("message", body="x", internal=False).status_code, 403)
        self.assertEqual(
            self.client.get(f"/api/patients/{self.p.id}/export/").status_code, 403
        )
        self.as_user("river.patient")
        self.assertEqual(self.act("message", body="x", internal=True).status_code, 403)
        exported = self.client.get(f"/api/patients/{self.p.id}/export/").json()
        self.assertFalse(any(x["internal"] for x in exported["messages"]))

    def test_confirmation_duplicate_and_handoff_minimum_context(self):
        self.consent()
        d = self.intake_data()
        self.assertEqual(
            self.act("submit", **{**d, "confirmed": False}).status_code, 400
        )
        # Transaction rollback leaves no failed partial record.
        self.assertEqual(Intake.objects.count(), 0)
        self.assertEqual(
            self.act(
                "handoff",
                **d,
                internal_notes="must never be included",
                organization_id=self.other.organization_id,
            ).status_code,
            200,
        )
        retry = self.act("handoff", **d)
        self.assertTrue(retry.json()["duplicate"])
        self.assertEqual(Intake.objects.count(), 1)
        i = Intake.objects.get()
        self.assertEqual(i.summary, d["summary"])
        self.assertEqual(i.unresolved_questions, d["unresolved_questions"])
        self.assertTrue(i.confirmed and i.handoff)
        self.assertEqual(i.patient_id, self.p.id)
        self.assertNotIn("Internal", i.summary)
        self.assertEqual(Notification.objects.count(), 1)

    def test_intake_requires_consent(self):
        self.as_user("river.patient")
        self.assertEqual(self.act("submit", **self.intake_data()).status_code, 400)

    def test_unsafe_clinical_request_routes_human_review(self):
        self.consent()
        d = self.intake_data()
        d["goal"] = "Which specialist should diagnose my symptoms?"
        result = self.act("draft", **d)
        self.assertEqual(result.status_code, 200)
        self.assertTrue(result.json()["human_review"])
        self.assertEqual(self.act("submit", **d).status_code, 200)
        self.assertTrue(Intake.objects.get().human_review)
        self.assertTrue(Intake.objects.get().handoff)

    def test_ai_failure_preserves_text_path(self):
        self.consent()
        d = self.intake_data()
        with patch(
            "navigation.views.DemoAI.summarize", side_effect=RuntimeError("Unavailable")
        ):
            self.assertEqual(self.act("draft", **d).status_code, 200)
        self.assertEqual(Intake.objects.get().goal, d["goal"])
        self.assertEqual(self.act("handoff", **d).status_code, 200)

    def test_referral_transition_and_closure(self):
        self.as_user("river.navigator")

        def transition(state, outcome="none", evidence=""):
            return self.act(
                "transition",
                id=self.ref.id,
                state=state,
                outcome=outcome,
                reason="Manual demo follow-through",
                evidence=evidence,
            )

        self.assertEqual(transition("closed").status_code, 400)
        self.assertEqual(transition("scheduled").status_code, 400)
        for state in [
            "sent",
            "accepted",
            "scheduling",
            "scheduled",
            "attended",
            "follow-up received",
        ]:
            self.assertEqual(transition(state).status_code, 200)
            if state == "scheduled":
                self.assertEqual(transition("closed").status_code, 400)
        self.assertEqual(transition("closed").status_code, 400)
        self.assertEqual(
            transition(
                "closed", evidence="Attendance and authorized follow-up confirmed"
            ).status_code,
            200,
        )
        self.assertEqual(
            ReferralTransition.objects.filter(referral=self.ref).count(), 8
        )

    def test_documented_alternative_and_blocked_not_completed(self):
        self.as_user("river.navigator")
        self.assertEqual(
            self.act(
                "transition",
                id=self.ref.id,
                state="closed",
                outcome="blocked",
                reason="Capacity",
                evidence="No capacity",
            ).status_code,
            400,
        )
        self.assertEqual(
            self.act(
                "transition",
                id=self.ref.id,
                state="closed",
                outcome="declined",
                reason="Patient choice",
                evidence="Fictional patient chose to decline",
            ).status_code,
            200,
        )
        report = self.client.get("/api/reports/").json()
        self.assertEqual(report["referrals_completed"], 0)
        self.assertEqual(report["alternative_outcomes_excluded"], 1)

    def test_stale_conflicting_and_separate_dimensions(self):
        self.as_user("river.navigator")
        pr = Provider.objects.filter(organization=self.p.organization).first()
        for dim, status in [
            ("network participation", "conflicting"),
            ("benefit eligibility", "pending"),
        ]:
            self.assertEqual(
                self.act(
                    "verify",
                    provider_id=pr.id,
                    dimension=dim,
                    status=status,
                    source="Fictional inconsistent call",
                ).status_code,
                200,
            )
        values = self.client.get(f"/api/patients/{self.p.id}/").json()["verifications"]
        self.assertTrue(any(v["stale"] for v in values))
        self.assertTrue(any(v["status"] == "conflicting" for v in values))
        self.assertEqual(
            Verification.objects.filter(
                patient=self.p, provider=pr, dimension="benefit eligibility"
            ).count(),
            2,
        )

    def test_notification_failure_does_not_lose_request(self):
        self.consent()
        self.act("submit", **self.intake_data())
        n = Notification.objects.get()
        self.as_user("river.navigator")
        self.assertEqual(self.act("notification_failure", id=n.id).status_code, 200)
        self.assertEqual(Intake.objects.count(), 1)
        n.refresh_from_db()
        self.assertEqual(n.state, "failed demo")

    def test_complete_coordination_workflow_and_reporting(self):
        self.consent()
        self.act("submit", **self.intake_data())
        i = Intake.objects.get()
        self.as_user("river.navigator")
        self.assertEqual(self.act("accept", id=i.id).status_code, 200)
        self.assertEqual(
            self.act(
                "task",
                title="Check transport",
                owner_id=self.nav.id,
                due_date=str(timezone.localdate()),
                barrier="Transport",
            ).status_code,
            200,
        )
        self.assertEqual(
            self.act(
                "appointment",
                referral_id=self.ref.id,
                location="Fictional office",
                starts_at=timezone.now().isoformat(),
            ).status_code,
            200,
        )
        appointment = Appointment.objects.get()
        self.assertEqual(
            self.act(
                "appointment_status", id=appointment.id, status="attended"
            ).status_code,
            200,
        )
        self.assertEqual(self.act("time", minutes=10).status_code, 200)
        r = self.client.get("/api/reports/").json()
        self.assertEqual(r["staff_minutes"], 22)
        self.assertEqual(r["intakes_submitted"], 1)
        self.assertIsNotNone(r["median_acceptance_hours"])
        self.as_user("river.patient")
        payload = self.client.get(f"/api/patients/{self.p.id}/").json()
        self.assertEqual(payload["appointments"][0]["status"], "attended")
        self.assertEqual(payload["requests"][0]["owner_id"], self.nav.id)

    def test_organization_and_audit_permissions(self):
        for name in ["river.patient", "river.caregiver", "river.navigator"]:
            self.as_user(name)
            self.assertEqual(self.client.get("/api/audit/").status_code, 403)
            self.assertEqual(self.client.get("/api/organization/").status_code, 403)
        self.as_user("river.admin")
        self.client.get(f"/api/patients/{self.p.id}/")
        events = self.client.get("/api/audit/").json()
        self.assertTrue(any(x["action"] == "workspace.read" for x in events))
        self.assertFalse(any("body" in x or "summary" in x for x in events))
        other = User.objects.get(username="oak.navigator")
        self.assertEqual(
            self.client.post(
                "/api/organization/",
                {"action": "staff_role", "user_id": other.id, "role": "admin"},
                format="json",
            ).status_code,
            404,
        )

    def test_preferences_independent_and_draft_retained(self):
        self.consent()
        d = self.intake_data()
        self.act("draft", **d)
        for mode, output in [("voice", False), ("text", True), ("text", False)]:
            self.assertEqual(
                self.act(
                    "preferences",
                    input_mode=mode,
                    spoken_output=output,
                    communication="in-app text",
                ).status_code,
                200,
            )
            self.p.refresh_from_db()
            self.assertEqual(self.p.input_mode, mode)
            self.assertEqual(self.p.spoken_output, output)
            self.assertEqual(Intake.objects.get().goal, d["goal"])

    def test_authentication_and_login_csrf(self):
        c = Client(enforce_csrf_checks=True)
        self.assertEqual(c.get(f"/api/patients/{self.p.id}/").status_code, 403)
        self.assertEqual(
            c.post(
                "/api/login/",
                data={"username": "river.patient", "password": "DemoOnly-2026!"},
                content_type="application/json",
            ).status_code,
            403,
        )
        c.get("/api/session/")
        csrf = c.cookies["csrftoken"].value
        self.assertEqual(
            c.post(
                "/api/login/",
                data={"username": "river.patient", "password": "DemoOnly-2026!"},
                content_type="application/json",
                HTTP_X_CSRFTOKEN=csrf,
            ).status_code,
            200,
        )
        self.assertEqual(c.get(f"/api/patients/{self.p.id}/").status_code, 200)
        self.assertEqual(
            c.post(
                f"/api/patients/{self.p.id}/actions/",
                data={"action": "consent", "accepted": True},
                content_type="application/json",
            ).status_code,
            403,
        )

    def test_separate_blocked_outcome_and_inactive_enrollment(self):
        self.as_user("river.navigator")
        self.assertEqual(
            self.act(
                "outcome",
                id=self.ref.id,
                outcome="blocked",
                reason="Fictional office has no capacity",
            ).status_code,
            200,
        )
        self.ref.refresh_from_db()
        self.assertEqual(self.ref.state, "review needed")
        self.assertEqual(self.ref.outcome, "blocked")
        report = self.client.get("/api/reports/").json()
        self.assertEqual(report["blocked_included"], 1)
        self.assertEqual(report["referrals_completed"], 0)
        Enrollment.objects.filter(patient=self.p).update(active=False)
        self.assertEqual(
            self.client.get(f"/api/patients/{self.p.id}/").status_code, 404
        )
        self.assertEqual(self.client.get("/api/dashboard/").json()["patients"], [])

    def test_bad_payloads_and_unowned_nested_records_rejected(self):
        self.as_user("river.navigator")
        self.assertEqual(
            self.client.post(
                f"/api/patients/{self.p.id}/actions/", [], format="json"
            ).status_code,
            400,
        )
        self.assertEqual(self.act("time", minutes=-1).status_code, 400)
        self.assertEqual(
            self.act(
                "task", title="x", owner_id=self.nav.id, due_date="invalid"
            ).status_code,
            400,
        )
        othermessage = Message.objects.filter(patient=self.other).first()
        self.assertEqual(self.act("task_done", id=999999, done=True).status_code, 404)

    def test_protected_directory_import_ignores_client_organization(self):
        row = {
            "name": "Fictional new practice",
            "specialty": "Neurology",
            "location": "Demo location",
            "contact": "555-0101",
            "accessibility": "Step-free",
            "organization_id": self.other.organization_id,
        }
        for role in ["patient", "caregiver", "navigator"]:
            self.as_user("river." + role)
            self.assertEqual(
                self.client.post(
                    "/api/directory-import/", {"providers": [row]}, format="json"
                ).status_code,
                403,
            )
        self.as_user("river.admin")
        self.assertEqual(
            self.client.post(
                "/api/directory-import/", {"providers": [row]}, format="json"
            ).status_code,
            200,
        )
        imported = Provider.objects.get(name=row["name"])
        self.assertEqual(imported.organization_id, self.p.organization_id)
        count = Provider.objects.count()
        self.assertEqual(
            self.client.post(
                "/api/directory-import/",
                {"providers": [row, {"name": "invalid"}]},
                format="json",
            ).status_code,
            400,
        )
        self.assertEqual(Provider.objects.count(), count)
