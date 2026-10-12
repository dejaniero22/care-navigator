import json, uuid
from datetime import date, datetime, timedelta
from statistics import median
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q, Sum
from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_protect
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from .models import *
from .adapters import DemoAI, requires_review

STATES = [
    "draft",
    "review needed",
    "sent",
    "accepted",
    "scheduling",
    "scheduled",
    "attended",
    "follow-up received",
    "closed",
]
DIMENSIONS = [
    "network participation",
    "accepting new patients",
    "benefit eligibility",
    "referral requirements",
    "prior authorization",
]


def member(user):
    m = Membership.objects.filter(user=user).first()
    if not m:
        raise PermissionDenied("No service membership.")
    return m


def staff(m):
    return m.role in ["navigator", "admin"]


def patients(user):
    m = member(user)
    q = Patient.objects.filter(organization=m.organization, enrollment__active=True)
    if staff(m):
        return q
    if m.role == "patient":
        return q.filter(user=user)
    return q.filter(
        caregivergrant__caregiver=user, caregivergrant__revoked_at__isnull=True
    )


def patient_for(user, pk, write=False):
    p = get_object_or_404(patients(user), pk=pk)
    m = member(user)
    if (
        write
        and m.role == "caregiver"
        and not CaregiverGrant.objects.filter(
            patient=p, caregiver=user, revoked_at__isnull=True, can_message=True
        ).exists()
    ):
        raise PermissionDenied("Communication permission is required.")
    if not Enrollment.objects.filter(patient=p, active=True).exists():
        raise PermissionDenied("Service enrollment is inactive.")
    return p


def audit(user, p, action, obj=""):
    AuditEvent.objects.create(
        actor=user,
        organization=p.organization,
        patient=p,
        action=action,
        object_id=str(obj),
    )


def need_staff(user):
    m = member(user)
    if not staff(m):
        raise PermissionDenied("Staff access required.")
    return m


def text(d, key, required=True, limit=4000):
    value = d.get(key, "")
    if (
        not isinstance(value, str)
        or len(value) > limit
        or (required and not value.strip())
    ):
        raise ValidationError({key: "Enter a valid value."})
    return value.strip()


def choice(d, key, allowed):
    value = text(d, key)
    if value not in allowed:
        raise ValidationError({key: "Unsupported option."})
    return value


def boolean(d, key):
    v = d.get(key)
    if not isinstance(v, bool):
        raise ValidationError({key: "Must be true or false."})
    return v


def integer(d, key):
    v = d.get(key)
    if isinstance(v, bool) or not isinstance(v, int) or v < 1:
        raise ValidationError({key: "Positive integer required."})
    return v


def due(d, key="due_date"):
    try:
        return date.fromisoformat(text(d, key))
    except ValueError:
        raise ValidationError({key: "Use YYYY-MM-DD."})


def owner_for(p, d):
    return get_object_or_404(
        User,
        pk=integer(d, "owner_id"),
        membership__organization=p.organization,
        membership__role__in=["navigator", "admin"],
    )


def items(q, fields):
    return list(q.values(*fields))


def payload(user, p):
    is_staff = staff(member(user))
    msgs = Message.objects.filter(patient=p)
    if not is_staff:
        msgs = msgs.filter(internal=False)
    refs = Referral.objects.filter(patient=p)
    evidence = []
    for v in (
        Verification.objects.filter(patient=p)
        .select_related("provider", "verifier")
        .order_by("-checked_at")
    ):
        evidence.append(
            {
                "id": v.id,
                "provider_id": v.provider_id,
                "provider": v.provider.name,
                "plan": v.plan,
                "location": v.location,
                "dimension": v.dimension,
                "status": v.status,
                "source": v.source,
                "verifier": v.verifier.username,
                "checked_at": v.checked_at,
                "stale": v.checked_at
                < timezone.now() - timedelta(days=settings.VERIFICATION_STALE_DAYS),
                "fictional": True,
            }
        )
    return {
        "patient": {
            "id": p.id,
            "name": p.name,
            "plan": p.plan,
            "communication": p.communication,
            "input_mode": p.input_mode,
            "spoken_output": p.spoken_output,
        },
        "enrollment": items(
            Enrollment.objects.filter(patient=p),
            ["service", "clinical_entity", "location", "active"],
        ),
        "consented": Consent.objects.filter(patient=p, version="demo-v1").exists(),
        "requests": items(
            Intake.objects.filter(patient=p).order_by("-created_at"),
            [
                "id",
                "key",
                "goal",
                "instructions",
                "providers",
                "coverage",
                "barriers",
                "communication_needs",
                "summary",
                "confirmed",
                "submitted_at",
                "human_review",
                "handoff",
                "unresolved_questions",
                "owner_id",
                "owner__username",
                "accepted_at",
            ],
        ),
        "referrals": items(
            refs,
            [
                "id",
                "specialty",
                "instructions",
                "state",
                "outcome",
                "evidence",
                "owner_id",
                "owner__username",
                "due_date",
            ],
        ),
        "transitions": items(
            ReferralTransition.objects.filter(referral__patient=p),
            [
                "referral_id",
                "previous",
                "current",
                "reason",
                "actor__username",
                "created_at",
            ],
        ),
        "tasks": items(
            Task.objects.filter(patient=p),
            [
                "id",
                "title",
                "owner_id",
                "owner__username",
                "due_date",
                "barrier",
                "done",
            ],
        ),
        "appointments": items(
            Appointment.objects.filter(referral__patient=p),
            ["id", "referral_id", "location", "starts_at", "status"],
        ),
        "messages": items(
            msgs.order_by("created_at"),
            ["id", "body", "internal", "author__username", "created_at"],
        ),
        "verifications": evidence,
        "providers": items(
            Provider.objects.filter(organization=p.organization),
            [
                "id",
                "name",
                "specialty",
                "location",
                "contact",
                "accessibility",
                "source",
            ],
        ),
        "staff": items(
            Membership.objects.filter(
                organization=p.organization, role__in=["navigator", "admin"]
            ),
            ["user_id", "user__username", "role"],
        )
        if is_staff
        else [],
        "grants": items(
            CaregiverGrant.objects.filter(patient=p),
            ["id", "caregiver__username", "can_message", "revoked_at"],
        )
        if p.user_id == user.id
        else [],
        "available_caregivers": items(
            Membership.objects.filter(organization=p.organization, role="caregiver"),
            ["user_id", "user__username"],
        )
        if p.user_id == user.id
        else [],
        "outbox": items(
            Notification.objects.filter(patient=p), ["id", "state", "description"]
        ),
    }


@ensure_csrf_cookie
@require_http_methods(["GET"])
def session(request):
    if not request.user.is_authenticated:
        return JsonResponse({"authenticated": False})
    m = Membership.objects.filter(user=request.user).first()
    return JsonResponse(
        {
            "authenticated": True,
            "username": request.user.username,
            "role": m.role if m else "unassigned",
            "organization": m.organization.name if m else None,
            "service_hours": m.organization.service_hours if m else None,
            "response_expectation": m.organization.response_expectation if m else None,
            "emergency_instructions": settings.EMERGENCY_INSTRUCTIONS,
        }
    )


@csrf_protect
@require_http_methods(["POST"])
def sign_in(request):
    try:
        d = json.loads(request.body)
        if not isinstance(d, dict):
            raise ValueError()
        u = authenticate(
            request, username=d.get("username"), password=d.get("password")
        )
    except (ValueError, TypeError):
        return JsonResponse({"detail": "Invalid sign-in data."}, status=400)
    if not u:
        return JsonResponse(
            {"detail": "Sign-in details were not recognized."}, status=401
        )
    login(request, u)
    return JsonResponse({"ok": True})


@api_view(["POST"])
def sign_out(request):
    logout(request)
    return Response({"ok": True})


@api_view(["GET"])
def dashboard(request):
    ps = patients(request.user)
    m = member(request.user)
    rows = []
    for p in ps:
        audit(request.user, p, "dashboard.read")
        rows.append(
            {
                "id": p.id,
                "name": p.name,
                "open_requests": Intake.objects.filter(
                    patient=p, submitted_at__isnull=False, owner__isnull=True
                ).count(),
                "overdue_tasks": Task.objects.filter(
                    patient=p, done=False, due_date__lt=timezone.localdate()
                ).count(),
                "assigned_to_me": Intake.objects.filter(
                    patient=p, owner=request.user
                ).exists()
                or Referral.objects.filter(patient=p, owner=request.user).exists(),
            }
        )
    return Response({"patients": rows, "role": m.role})


@api_view(["GET"])
def workspace(request, pk):
    p = patient_for(request.user, pk)
    audit(request.user, p, "workspace.read")
    return Response(payload(request.user, p))


@api_view(["POST"])
@transaction.atomic
def action(request, pk):
    p = patient_for(request.user, pk, write=True)
    # Serialize per-patient mutation to make retries and ownership race-safe.
    p = Patient.objects.select_for_update().get(pk=p.pk)
    d = request.data
    if not isinstance(d, dict):
        raise ValidationError("JSON object required.")
    a = text(d, "action", limit=40)
    m = member(request.user)
    is_staff = staff(m)
    if (
        a in ["consent", "grant", "revoke", "preferences"]
        and p.user_id != request.user.id
    ):
        raise PermissionDenied(
            "Only the patient may change their access and preferences."
        )
    if (
        a
        in [
            "accept",
            "referral",
            "transition",
            "outcome",
            "task",
            "task_done",
            "appointment",
            "appointment_status",
            "verify",
            "time",
            "notification_failure",
        ]
        and not is_staff
    ):
        raise PermissionDenied("Staff access required.")
    obj = ""
    if a == "consent":
        if not boolean(d, "accepted"):
            raise ValidationError("Review and accept the service scope to continue.")
        Consent.objects.get_or_create(
            patient=p, version="demo-v1", defaults={"actor": request.user}
        )
    elif a == "preferences":
        p.input_mode = choice(d, "input_mode", ["text", "voice"])
        p.spoken_output = boolean(d, "spoken_output")
        p.communication = choice(d, "communication", ["in-app text", "assisted text"])
        p.save()
    elif a == "grant":
        c = get_object_or_404(
            User,
            pk=integer(d, "caregiver_id"),
            membership__organization=p.organization,
            membership__role="caregiver",
        )
        obj, _ = CaregiverGrant.objects.update_or_create(
            patient=p,
            caregiver=c,
            defaults={"can_message": boolean(d, "can_message"), "revoked_at": None},
        )
        obj = obj.pk
    elif a == "revoke":
        g = get_object_or_404(CaregiverGrant, pk=integer(d, "id"), patient=p)
        g.revoked_at = timezone.now()
        g.save()
        obj = g.pk
    elif a in ["draft", "submit", "handoff"]:
        if not Consent.objects.filter(patient=p, version="demo-v1").exists():
            raise ValidationError("Patient service-scope consent is required.")
        try:
            key = uuid.UUID(text(d, "key"))
        except ValueError:
            raise ValidationError({"key": "A UUID submission key is required."})
        i, _ = Intake.objects.get_or_create(
            patient=p, key=key, defaults={"goal": text(d, "goal")}
        )
        if i.submitted_at:
            return Response({"ok": True, "duplicate": True, "id": i.id})
        for field in [
            "goal",
            "instructions",
            "providers",
            "coverage",
            "barriers",
            "communication_needs",
        ]:
            setattr(i, field, text(d, field, required=field == "goal"))
        i.human_review = requires_review(
            " ".join(getattr(i, f) for f in ["goal", "instructions", "barriers"])
        )
        if a == "draft":
            try:
                i.summary = DemoAI().summarize(d)
            except Exception:
                i.summary = "Assistant unavailable. Type and confirm your own summary; human assistance remains available."
        else:
            if not boolean(d, "confirmed"):
                raise ValidationError(
                    {"confirmed": "Confirm the corrected summary before submitting."}
                )
            i.summary = text(d, "summary")
            i.confirmed = True
            i.submitted_at = timezone.now()
            i.unresolved_questions = text(d, "unresolved_questions", False)
            i.handoff = a == "handoff" or i.human_review
            Notification.objects.create(patient=p)
        i.save()
        obj = i.pk
    elif a == "accept":
        i = get_object_or_404(
            Intake, pk=integer(d, "id"), patient=p, submitted_at__isnull=False
        )
        if i.owner_id and i.owner_id != request.user.id:
            raise ValidationError("Already assigned to another navigator.")
        i.owner = request.user
        i.accepted_at = i.accepted_at or timezone.now()
        i.save()
        obj = i.pk
    elif a == "referral":
        obj = Referral.objects.create(
            patient=p,
            specialty=text(d, "specialty", limit=100),
            instructions=text(d, "instructions"),
            due_date=due(d),
            owner=owner_for(p, d),
        ).pk
    elif a == "transition":
        r = get_object_or_404(Referral, pk=integer(d, "id"), patient=p)
        target = choice(d, "state", STATES)
        reason = text(d, "reason")
        outcome = choice(d, "outcome", ["none", "blocked", "declined", "canceled"])
        evidence = text(d, "evidence", False)
        alternative = (
            target == "closed" and outcome in ["declined", "canceled"] and evidence
        )
        sequential = STATES.index(target) == STATES.index(r.state) + 1
        if not (sequential or alternative):
            raise ValidationError("Invalid referral transition.")
        if target == "closed" and not (
            (r.state == "follow-up received" and evidence and outcome == "none")
            or alternative
        ):
            raise ValidationError(
                "Closure requires documented follow-through or an evidenced declined/canceled outcome."
            )
        if r.state == "closed":
            raise ValidationError("Closed referrals cannot advance.")
        ReferralTransition.objects.create(
            referral=r,
            actor=request.user,
            previous=r.state,
            current=target,
            reason=reason,
        )
        r.state = target
        r.outcome = "" if outcome == "none" else outcome
        r.evidence = evidence
        r.save()
        obj = r.pk
    elif a == "outcome":
        r = get_object_or_404(Referral, pk=integer(d, "id"), patient=p)
        if r.state == "closed":
            raise ValidationError("Closed referral outcomes cannot be overwritten.")
        outcome = choice(d, "outcome", ["none", "blocked", "declined", "canceled"])
        reason = text(d, "reason")
        ReferralTransition.objects.create(
            referral=r,
            actor=request.user,
            previous=r.state,
            current=r.state,
            reason=f"Outcome {outcome}: {reason}",
        )
        r.outcome = "" if outcome == "none" else outcome
        r.evidence = reason
        r.save()
        obj = r.pk
    elif a == "task":
        obj = Task.objects.create(
            patient=p,
            title=text(d, "title", limit=200),
            owner=owner_for(p, d),
            due_date=due(d),
            barrier=text(d, "barrier", False),
        ).pk
    elif a == "task_done":
        t = get_object_or_404(Task, pk=integer(d, "id"), patient=p)
        t.done = boolean(d, "done")
        t.save()
        obj = t.pk
    elif a == "appointment":
        r = get_object_or_404(Referral, pk=integer(d, "referral_id"), patient=p)
        starts = parse_datetime(text(d, "starts_at"))
        if starts is None or timezone.is_naive(starts):
            raise ValidationError("Use an ISO date/time with a timezone.")
        obj = Appointment.objects.create(
            referral=r, location=text(d, "location", limit=160), starts_at=starts
        ).pk
    elif a == "appointment_status":
        ap = get_object_or_404(Appointment, pk=integer(d, "id"), referral__patient=p)
        ap.status = choice(d, "status", ["planned", "attended", "missed", "canceled"])
        ap.save()
        obj = ap.pk
    elif a == "verify":
        pr = get_object_or_404(
            Provider, pk=integer(d, "provider_id"), organization=p.organization
        )
        checked = (
            parse_datetime(text(d, "checked_at"))
            if d.get("checked_at")
            else timezone.now()
        )
        if not checked or timezone.is_naive(checked) or checked > timezone.now():
            raise ValidationError(
                "Verification timestamp must be valid and not in the future."
            )
        obj = Verification.objects.create(
            patient=p,
            provider=pr,
            plan=p.plan,
            location=pr.location,
            dimension=choice(d, "dimension", DIMENSIONS),
            status=choice(
                d, "status", ["unknown", "pending", "verified", "conflicting"]
            ),
            source="Fictional demo evidence: " + text(d, "source", limit=170),
            verifier=request.user,
            checked_at=checked,
        ).pk
    elif a == "message":
        internal = boolean(d, "internal")
        if internal and not is_staff:
            raise PermissionDenied("Internal notes require staff permission.")
        obj = Message.objects.create(
            patient=p, author=request.user, body=text(d, "body"), internal=internal
        ).pk
    elif a == "time":
        minutes = integer(d, "minutes")
        if minutes > 1440:
            raise ValidationError("Minutes must be at most 1440.")
        obj = TimeEntry.objects.create(
            patient=p, staff=request.user, minutes=minutes
        ).pk
    elif a == "notification_failure":
        n = get_object_or_404(Notification, pk=integer(d, "id"), patient=p)
        n.state = "failed demo"
        n.save()
        obj = n.pk
    else:
        raise ValidationError("Unknown action.")
    audit(request.user, p, a, obj)
    return Response(
        {
            "ok": True,
            "id": obj,
            **(
                {"summary": i.summary, "human_review": i.human_review}
                if a == "draft"
                else {}
            ),
        }
    )


@api_view(["GET"])
def export_patient(request, pk):
    p = patient_for(request.user, pk)
    m = member(request.user)
    if p.user_id != request.user.id and m.role != "admin":
        raise PermissionDenied(
            "Exports require patient or organization-admin authority."
        )
    audit(request.user, p, "patient.export")
    response = Response(payload(request.user, p))
    response["Content-Disposition"] = 'attachment; filename="synthetic-patient.json"'
    response["Cache-Control"] = "no-store"
    return response


@api_view(["GET", "POST"])
def organization(request):
    m = member(request.user)
    if m.role != "admin":
        raise PermissionDenied("Organization admin required.")
    if request.method == "POST":
        d = request.data
        if d.get("action") == "staff_role":
            membership = get_object_or_404(
                Membership,
                user_id=integer(d, "user_id"),
                organization=m.organization,
                role__in=["navigator", "admin"],
            )
            role = choice(d, "role", ["navigator", "admin"])
            if membership.user_id == request.user.id and role != "admin":
                raise ValidationError("Cannot remove your own admin role.")
            membership.role = role
            membership.save()
        else:
            m.organization.service_hours = text(d, "service_hours", limit=200)
            m.organization.response_expectation = text(
                d, "response_expectation", limit=200
            )
            m.organization.save()
        AuditEvent.objects.create(
            actor=request.user,
            organization=m.organization,
            action="organization.update",
        )
    return Response(
        {
            "name": m.organization.name,
            "service_hours": m.organization.service_hours,
            "response_expectation": m.organization.response_expectation,
            "staff": items(
                Membership.objects.filter(
                    organization=m.organization, role__in=["navigator", "admin"]
                ),
                ["user_id", "user__username", "role"],
            ),
        }
    )


@api_view(["GET"])
def reports(request):
    m = need_staff(request.user)
    try:
        start = date.fromisoformat(
            request.query_params.get("start", str(timezone.localdate().replace(day=1)))
        )
        end = date.fromisoformat(
            request.query_params.get(
                "end", str(timezone.localdate() + timedelta(days=30))
            )
        )
        if start > end:
            raise ValueError()
    except ValueError:
        raise ValidationError("Invalid reporting period.")
    q = Referral.objects.filter(
        patient__organization=m.organization, due_date__range=(start, end)
    )
    excluded = q.filter(outcome__in=["declined", "canceled"]).count()
    completed = q.filter(state="closed", outcome="").count()
    eligible = q.count() - excluded
    intakes = Intake.objects.filter(
        patient__organization=m.organization, created_at__date__range=(start, end)
    )
    accepted = intakes.filter(accepted_at__isnull=False, submitted_at__isnull=False)
    times = [(x.accepted_at - x.submitted_at).total_seconds() / 3600 for x in accepted]
    AuditEvent.objects.create(
        actor=request.user, organization=m.organization, action="reports.read"
    )
    return Response(
        {
            "synthetic": True,
            "start": start,
            "end": end,
            "referrals_completed": completed,
            "referrals_due": eligible,
            "referrals_due_all": q.count(),
            "alternative_outcomes_excluded": excluded,
            "blocked_included": q.filter(outcome="blocked").count(),
            "completion_ratio": completed / eligible if eligible else None,
            "all_due_completion_ratio": completed / q.count() if q.exists() else None,
            "intakes_started": intakes.count(),
            "intakes_submitted": intakes.filter(submitted_at__isnull=False).count(),
            "median_acceptance_hours": median(times) if times else None,
            "overdue_tasks": Task.objects.filter(
                patient__organization=m.organization,
                done=False,
                due_date__lt=timezone.localdate(),
            ).count(),
            "staff_minutes": TimeEntry.objects.filter(
                patient__organization=m.organization,
                created_at__date__range=(start, end),
            ).aggregate(total=Sum("minutes"))["total"]
            or 0,
            "definitions": "Completed = closed with follow-through evidence. Due = due dates in selected inclusive period; declined/canceled reported separately. Blocked remain in denominator. Intake = submitted/started in period. Minutes are operational, not billable.",
        }
    )


@api_view(["GET"])
def audit_history(request):
    m = member(request.user)
    if m.role != "admin":
        raise PermissionDenied("Organization admin required.")
    AuditEvent.objects.create(
        actor=request.user, organization=m.organization, action="audit.read"
    )
    return Response(
        items(
            AuditEvent.objects.filter(organization=m.organization).order_by(
                "-created_at"
            )[:200],
            [
                "id",
                "action",
                "patient_id",
                "object_id",
                "actor__username",
                "created_at",
            ],
        )
    )


@api_view(["POST"])
@transaction.atomic
def directory_import(request):
    m = member(request.user)
    if m.role != "admin":
        raise PermissionDenied("Organization admin required.")
    if not isinstance(request.data, dict):
        raise ValidationError("JSON object required.")
    rows = request.data.get("providers")
    if not isinstance(rows, list) or not 1 <= len(rows) <= 50:
        raise ValidationError("Import 1–50 fictional provider rows.")
    # The organization comes exclusively from authenticated membership. All rows validate before writing.
    validated = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValidationError("Each row must be an object.")
        validated.append(
            {
                k: text(row, k, limit=limit)
                for k, limit in [
                    ("name", 160),
                    ("specialty", 100),
                    ("location", 160),
                    ("contact", 160),
                    ("accessibility", 200),
                ]
            }
        )
    created = [
        Provider.objects.create(
            organization=m.organization, source="Fictional local admin import", **row
        ).pk
        for row in validated
    ]
    AuditEvent.objects.create(
        actor=request.user,
        organization=m.organization,
        action="directory.import",
        object_id=str(len(created)),
    )
    return Response({"created": len(created), "ids": created})
