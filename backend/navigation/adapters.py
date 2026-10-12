"""No external model calls; untrusted text is only reflected as a draft."""


class DemoAI:
    label = "Deterministic demo draft — not clinical advice"

    def summarize(self, data):
        return "\n".join(
            f"{label}: {data.get(key, 'Not supplied')}"
            for key, label in [
                ("goal", "Your goal"),
                ("instructions", "Supplied referral instructions"),
                ("providers", "Known providers"),
                ("coverage", "Your stated coverage"),
                ("barriers", "Barriers"),
                ("communication_needs", "Communication needs"),
            ]
        )


def requires_review(text):
    # A convenience routing rule, never a triage classifier. Every intake permits human handoff.
    return any(
        word in text.lower()
        for word in [
            "symptom",
            "diagnos",
            "medication",
            "dose",
            "chest pain",
            "emergency",
            "which specialist",
            "treatment",
        ]
    )
