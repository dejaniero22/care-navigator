from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Organization(models.Model):
    name = models.CharField(max_length=160)
    service_hours = models.CharField(
        max_length=200, default="Weekdays 9 am–5 pm Pacific"
    )
    response_expectation = models.CharField(
        max_length=200,
        default="Next business day; monitored fallback queue during service hours (demo)",
    )


class Membership(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    role = models.CharField(
        max_length=20,
        choices=[(x, x) for x in ["patient", "caregiver", "navigator", "admin"]],
    )


class Patient(models.Model):
    user = models.OneToOneField(User, on_delete=models.PROTECT)
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT)
    name = models.CharField(max_length=160)
    plan = models.CharField(max_length=160)
    communication = models.CharField(max_length=30, default="in-app text")
    input_mode = models.CharField(max_length=10, default="text")
    spoken_output = models.BooleanField(default=False)


class Enrollment(models.Model):
    patient = models.OneToOneField(Patient, on_delete=models.CASCADE)
    service = models.CharField(
        max_length=160, default="Administrative referral navigation"
    )
    clinical_entity = models.CharField(
        max_length=160,
        default="Fictional partner practice; EHR remains system of record",
    )
    location = models.CharField(max_length=160, default="Sacramento / remote")
    active = models.BooleanField(default=True)


class Consent(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    actor = models.ForeignKey(User, on_delete=models.PROTECT)
    version = models.CharField(max_length=20, default="demo-v1")
    created_at = models.DateTimeField(auto_now_add=True)


class CaregiverGrant(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    caregiver = models.ForeignKey(User, on_delete=models.PROTECT)
    can_message = models.BooleanField(default=False)
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["patient", "caregiver"], name="one_caregiver_grant"
            )
        ]


class Intake(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    key = models.UUIDField()
    goal = models.TextField()
    instructions = models.TextField(blank=True)
    providers = models.TextField(blank=True)
    coverage = models.TextField(blank=True)
    barriers = models.TextField(blank=True)
    communication_needs = models.TextField(blank=True)
    summary = models.TextField(blank=True)
    confirmed = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(null=True)
    human_review = models.BooleanField(default=False)
    handoff = models.BooleanField(default=False)
    unresolved_questions = models.TextField(blank=True)
    owner = models.ForeignKey(User, null=True, on_delete=models.PROTECT)
    accepted_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["patient", "key"], name="intake_idempotency"
            )
        ]


class Referral(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    specialty = models.CharField(max_length=100)
    instructions = models.TextField()
    state = models.CharField(max_length=30, default="draft")
    outcome = models.CharField(max_length=20, blank=True)
    evidence = models.TextField(blank=True)
    owner = models.ForeignKey(User, null=True, on_delete=models.PROTECT)
    due_date = models.DateField()


class ReferralTransition(models.Model):
    referral = models.ForeignKey(Referral, on_delete=models.CASCADE)
    actor = models.ForeignKey(User, on_delete=models.PROTECT)
    previous = models.CharField(max_length=30)
    current = models.CharField(max_length=30)
    reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


class Provider(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    name = models.CharField(max_length=160)
    specialty = models.CharField(max_length=100)
    location = models.CharField(max_length=160)
    contact = models.CharField(max_length=160)
    accessibility = models.CharField(max_length=200)
    source = models.CharField(max_length=200, default="Fictional demo directory")


class Verification(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    provider = models.ForeignKey(Provider, on_delete=models.PROTECT)
    plan = models.CharField(max_length=160)
    location = models.CharField(max_length=160)
    dimension = models.CharField(max_length=40)
    status = models.CharField(max_length=20)
    source = models.CharField(max_length=200)
    verifier = models.ForeignKey(User, on_delete=models.PROTECT)
    checked_at = models.DateTimeField(default=timezone.now)


class Task(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    owner = models.ForeignKey(User, on_delete=models.PROTECT)
    due_date = models.DateField()
    barrier = models.TextField(blank=True)
    done = models.BooleanField(default=False)


class Appointment(models.Model):
    referral = models.ForeignKey(Referral, on_delete=models.CASCADE)
    location = models.CharField(max_length=160)
    starts_at = models.DateTimeField()
    status = models.CharField(max_length=20, default="planned")


class Message(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    author = models.ForeignKey(User, on_delete=models.PROTECT)
    body = models.TextField()
    internal = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


class TimeEntry(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    staff = models.ForeignKey(User, on_delete=models.PROTECT)
    minutes = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)


class Notification(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    state = models.CharField(max_length=20, default="unsent")
    description = models.CharField(
        max_length=160, default="Demo update available — no external notification sent"
    )


class AuditEvent(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT)
    patient = models.ForeignKey(Patient, null=True, on_delete=models.PROTECT)
    actor = models.ForeignKey(User, on_delete=models.PROTECT)
    action = models.CharField(max_length=80)
    object_id = models.CharField(max_length=80, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
