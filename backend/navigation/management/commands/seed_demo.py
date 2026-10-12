from datetime import timedelta
import uuid
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone
from navigation.models import *


class Command(BaseCommand):
    help = "Create fictional demo records without resetting existing work."

    @transaction.atomic
    def handle(self, *args, **kwargs):
        if Organization.objects.exists():
            self.stdout.write("Seed already present; existing records preserved.")
            return
        for prefix, name in [
            ("river", "River City Navigation (fictional)"),
            ("oak", "Oak Valley Navigation (fictional)"),
        ]:
            org = Organization.objects.create(name=name)
            accounts = {}
            for role in ["patient", "caregiver", "navigator", "admin"]:
                u = User.objects.create_user(
                    f"{prefix}.{role}", password="DemoOnly-2026!"
                )
                Membership.objects.create(user=u, organization=org, role=role)
                accounts[role] = u
            p = Patient.objects.create(
                user=accounts["patient"],
                organization=org,
                name="Alex Rivera (fictional)"
                if prefix == "river"
                else "Jordan Chen (fictional)",
                plan="Fictional Silver Sacramento PPO",
            )
            Enrollment.objects.create(patient=p)
            CaregiverGrant.objects.create(
                patient=p, caregiver=accounts["caregiver"], can_message=True
            )
            # Consent intentionally absent: invited patient must review the scope.
            for specialty in ["Neurology", "Pain management"]:
                pr = Provider.objects.create(
                    organization=org,
                    name=f"Demo {specialty} Practice",
                    specialty=specialty,
                    location="Fictional office, Sacramento",
                    contact="555-0100 (fictional)",
                    accessibility="Step-free entry; interpreter needs require confirmation",
                )
                r = Referral.objects.create(
                    patient=p,
                    specialty=specialty,
                    instructions="Fictional existing clinician referral; coordinate administrative next steps only.",
                    state="review needed",
                    owner=accounts["navigator"],
                    due_date=timezone.localdate() + timedelta(days=14),
                )
                ReferralTransition.objects.create(
                    referral=r,
                    actor=accounts["navigator"],
                    previous="draft",
                    current="review needed",
                    reason="Fictional clinician instructions supplied",
                )
                Verification.objects.create(
                    patient=p,
                    provider=pr,
                    plan=p.plan,
                    location=pr.location,
                    dimension="network participation",
                    status="pending",
                    source="Fictional demo evidence; manual plan check needed",
                    verifier=accounts["navigator"],
                )
                Verification.objects.create(
                    patient=p,
                    provider=pr,
                    plan=p.plan,
                    location=pr.location,
                    dimension="benefit eligibility",
                    status="verified",
                    source="Fictional historical check — must recheck",
                    verifier=accounts["navigator"],
                    checked_at=timezone.now() - timedelta(days=45),
                )
            Task.objects.create(
                patient=p,
                title="Confirm exact-plan participation and transportation",
                owner=accounts["navigator"],
                due_date=timezone.localdate() - timedelta(days=1),
                barrier="Patient would like accessible transportation",
            )
            Message.objects.create(
                patient=p,
                author=accounts["navigator"],
                body="We can help with your existing referrals. Please review the service scope, then tell us your next goal.",
            )
            Message.objects.create(
                patient=p,
                author=accounts["navigator"],
                body="Internal demo workload note; never shared with patient or caregiver.",
                internal=True,
            )
            TimeEntry.objects.create(patient=p, staff=accounts["navigator"], minutes=12)
        self.stdout.write(
            self.style.SUCCESS(
                "Two fictional organizations created. Demo password: DemoOnly-2026!"
            )
        )
