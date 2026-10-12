import { useEffect, useState, type FormEvent } from "react";
import { api } from "./api";
import { Intake } from "./Intake";
type Row = Record<string, any>;
type Field = {
  name: string;
  label: string;
  type?: string;
  options?: [string, string][];
  optional?: boolean;
  value?: string;
  checked?: boolean;
};
const label = (value: string) => value.replaceAll("_", " ");
const when = (value: string) => new Date(value).toLocaleString();
const states = [
  "draft",
  "review needed",
  "sent",
  "accepted",
  "scheduling",
  "scheduled",
  "attended",
  "follow-up received",
  "closed",
];
const dimensions = [
  "network participation",
  "accepting new patients",
  "benefit eligibility",
  "referral requirements",
  "prior authorization",
];

function ActionForm({
  title,
  fields,
  submit,
}: {
  title: string;
  fields: Field[];
  submit: (d: Row) => Promise<unknown>;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  async function handle(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const data: Row = {};
    const entries = new FormData(form);
    for (const field of fields) {
      const value = entries.get(field.name);
      data[field.name] =
        field.type === "number"
          ? Number(value)
          : field.type === "checkbox"
            ? value === "on"
            : field.type === "datetime-local" && value
              ? new Date(String(value)).toISOString()
              : value || "";
    }
    setBusy(true);
    setError("");
    setSuccess("");
    try {
      await submit(data);
      form.reset();
      setSuccess("Saved.");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <form className="card form-card" onSubmit={handle}>
      <h3>{title}</h3>
      {fields.map((f) => (
        <label key={f.name} className={f.type === "checkbox" ? "check" : ""}>
          {f.type === "checkbox" && (
            <input type="checkbox" name={f.name} defaultChecked={f.checked} />
          )}
          <span>{f.label}</span>
          {f.options ? (
            <select name={f.name} required={!f.optional} defaultValue={f.value}>
              {f.options.map(([value, name]) => (
                <option key={value} value={value}>
                  {name}
                </option>
              ))}
            </select>
          ) : f.type === "textarea" ? (
            <textarea name={f.name} maxLength={4000} required={!f.optional} />
          ) : (
            f.type !== "checkbox" && (
              <input
                name={f.name}
                type={f.type || "text"}
                defaultValue={f.value}
                maxLength={200}
                min={f.type === "number" ? 1 : undefined}
                max={f.type === "number" ? 1440 : undefined}
                required={!f.optional}
              />
            )
          )}
        </label>
      ))}
      <button className="primary" disabled={busy}>
        {busy ? "Saving…" : title}
      </button>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      <p role="status">{success}</p>
    </form>
  );
}

export function App() {
  const [session, setSession] = useState<Row>();
  const [people, setPeople] = useState<Row[]>([]);
  const [selected, setSelected] = useState<number>();
  const [data, setData] = useState<Row>();
  const [tab, setTab] = useState("Home");
  const [error, setError] = useState("");
  const [extra, setExtra] = useState<Row | Row[]>();
  async function init() {
    try {
      const s = await api("/session/");
      setSession(s);
      if (s.authenticated) {
        const d = await api("/dashboard/");
        setPeople(d.patients);
        setSelected((x) =>
          x && d.patients.some((p: Row) => p.id === x) ? x : d.patients[0]?.id,
        );
      }
    } catch (e) {
      setError((e as Error).message);
    }
  }
  async function load() {
    if (!selected) return;
    try {
      setData(await api(`/patients/${selected}/`));
      setError("");
    } catch (e) {
      setData(undefined);
      setError((e as Error).message);
    }
  }
  useEffect(() => {
    void init();
  }, []);
  useEffect(() => {
    setData(undefined);
    void load();
  }, [selected]);
  useEffect(() => {
    setExtra(undefined);
    if (tab === "Reports" || tab === "Organization" || tab === "Audit") {
      api(
        tab === "Reports"
          ? "/reports/"
          : tab === "Organization"
            ? "/organization/"
            : "/audit/",
      )
        .then(setExtra)
        .catch((e) => setError(e.message));
    }
  }, [tab]);
  async function send(d: Row) {
    const result = await api(`/patients/${selected}/actions/`, d);
    await load();
    return result;
  }
  async function doAction(d: Row) {
    try {
      await send(d);
    } catch (e) {
      setError((e as Error).message);
    }
  }
  if (!session)
    return (
      <main>
        <h1>Care Navigator</h1>
        <p role="status">Loading…</p>
        {error && <p role="alert">{error}</p>}
      </main>
    );
  if (!session.authenticated)
    return (
      <main className="signin">
        <p className="eyebrow">CARE NAVIGATOR / SYNTHETIC DEMO</p>
        <h1>A clearer path to your next step.</h1>
        <p>
          Keep existing referrals, questions, and next steps together. A
          navigator can help you follow through.
        </p>
        <ActionForm
          title="Sign in"
          fields={[
            { name: "username", label: "Username" },
            { name: "password", label: "Password", type: "password" },
          ]}
          submit={async (d) => {
            await api("/login/", d);
            await init();
          }}
        />
        <aside className="notice">
          <h2>Invited demo accounts</h2>
          <p>
            Use <strong>river.patient</strong>, <strong>river.caregiver</strong>
            , <strong>river.navigator</strong>, or <strong>river.admin</strong>.
            Password: <code>DemoOnly-2026!</code>
          </p>
          <p>
            Use the <code>oak.</code> prefix to explore the second organization.
            These pre-provisioned invitations require patient service-scope
            review after sign-in.
          </p>
          <p>
            Fictional data only. No clinical care, external scheduling,
            messages, or real patient enrollment.
          </p>
        </aside>
      </main>
    );
  const isStaff = ["navigator", "admin"].includes(session.role);
  const isPatient = session.role === "patient";
  const tabs = [
    "Home",
    ...(isPatient || session.role === "caregiver" ? ["Intake"] : []),
    "Referrals",
    "Messages",
    "Directory",
    ...(isPatient ? ["Access"] : []),
    ...(isStaff ? ["Tasks", "Reports"] : []),
    ...(session.role === "admin" ? ["Organization", "Audit"] : []),
  ];
  const owners: [string, string][] = (data?.staff || []).map((s: Row) => [
    String(s.user_id),
    s.user__username,
  ]);
  const refs: [string, string][] = (data?.referrals || []).map((r: Row) => [
    String(r.id),
    r.specialty,
  ]);
  const providers: [string, string][] = (data?.providers || []).map(
    (r: Row) => [String(r.id), `${r.name} — ${r.location}`],
  );
  return (
    <>
      <a href="#main" className="skip">
        Skip to main content
      </a>
      <header>
        <div className="brand">
          <span aria-hidden="true" className="brand-mark">
            ✳
          </span>
          <span>
            Care Navigator<small>Synthetic demonstration</small>
          </span>
        </div>
        <div>
          <span>
            {session.username} · {session.role}
          </span>
          <button
            onClick={async () => {
              await api("/logout/", {});
              setData(undefined);
              setPeople([]);
              setSelected(undefined);
              setTab("Home");
              await init();
            }}
          >
            Sign out
          </button>
        </div>
      </header>
      <div className="app-shell">
        <aside className="sidebar">
          <p className="eyebrow">{session.organization}</p>
          <label>
            {isStaff ? "Patient coordination workspace" : "Your workspace"}
            <select
              value={selected || ""}
              onChange={(e) => setSelected(Number(e.target.value))}
            >
              {people.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </label>
          <nav aria-label="Main navigation">
            {tabs.map((t) => (
              <button
                key={t}
                aria-current={tab === t ? "page" : undefined}
                onClick={() => {
                  setTab(t);
                  setError("");
                }}
              >
                {t}
              </button>
            ))}
          </nav>
          <div className="hours">
            <strong>Ask a navigator</strong>
            <p>{session.service_hours}</p>
            <p>{session.response_expectation}</p>
            <p>Demo queue only. No emergency monitoring.</p>
          </div>
        </aside>
        <main id="main" tabIndex={-1}>
          <div className="page-heading">
            <div>
              <p className="eyebrow">
                {isStaff ? "COORDINATION WORKSPACE" : "YOUR NEXT STEPS"}
              </p>
              <h1>
                {tab === "Home"
                  ? isStaff
                    ? "Navigator queue"
                    : "Welcome, " + (data?.patient.name.split(" ")[0] || "")
                  : tab}
              </h1>
            </div>
            <button
              onClick={() => {
                void load();
                void init();
              }}
            >
              Refresh records
            </button>
          </div>
          {error && (
            <p role="alert" className="error">
              {error}
            </p>
          )}
          <div className="scope-banner">
            Fictional records · Manual coordination · No coverage or payment
            guarantee
          </div>
          <details>
            <summary>Service limits and urgent concerns</summary>
            <p>
              Administrative coordination only. Human review is available for
              any request; automated keyword routing does not determine medical
              urgency.
            </p>
            <p>
              Prototype emergency wording awaiting clinical review:{" "}
              {session.emergency_instructions}
            </p>
          </details>
          {!data && (
            <p role="status">
              {people.length
                ? "Loading authorized records…"
                : "No authorized patient access. A patient must grant caregiver access."}
            </p>
          )}
          {data && (
            <>
              {!data.consented && (
                <section className="notice">
                  <h2>Review your service scope</h2>
                  <p>
                    Administrative help with existing referrals, coverage
                    questions, and next steps. This demo provides no diagnosis,
                    treatment, real bookings, or emergency monitoring. All
                    records must be fictional. Consent version: demo-v1.
                  </p>
                  <p>{session.emergency_instructions}</p>
                  {isPatient ? (
                    <ActionForm
                      title="Accept service scope"
                      fields={[
                        {
                          name: "accepted",
                          label:
                            "I understand and accept the synthetic demo service scope",
                          type: "checkbox",
                        },
                      ]}
                      submit={(d) => send({ ...d, action: "consent" })}
                    />
                  ) : (
                    <p>
                      The patient must sign in and accept before intake can be
                      submitted.
                    </p>
                  )}
                </section>
              )}
              {tab === "Home" && (
                <>
                  <section className="stats">
                    <div>
                      <strong>
                        {
                          data.requests.filter(
                            (r: Row) => r.submitted_at && !r.owner_id,
                          ).length
                        }
                      </strong>
                      <span>Requests awaiting a navigator</span>
                    </div>
                    <div>
                      <strong>
                        {
                          data.referrals.filter(
                            (r: Row) => r.state !== "closed",
                          ).length
                        }
                      </strong>
                      <span>Referrals in progress</span>
                    </div>
                    <div>
                      <strong>
                        {data.tasks.filter((t: Row) => !t.done).length}
                      </strong>
                      <span>Next steps to follow</span>
                    </div>
                  </section>
                  {isStaff && (
                    <section>
                      <h2>Queue and caseload</h2>
                      {people.map((p) => (
                        <button
                          className="queue-row"
                          key={p.id}
                          onClick={() => setSelected(p.id)}
                        >
                          <strong>{p.name}</strong>
                          <span>
                            {p.open_requests} awaiting ownership ·{" "}
                            {p.overdue_tasks} overdue ·{" "}
                            {p.assigned_to_me
                              ? "Assigned to you"
                              : "Organization queue"}
                          </span>
                        </button>
                      ))}
                    </section>
                  )}
                  <section>
                    <h2>Open requests</h2>
                    {data.requests
                      .filter((r: Row) => r.submitted_at)
                      .map((r: Row) => (
                        <article className="card" key={r.id}>
                          <h3>{r.goal}</h3>
                          <span className="badge">
                            {r.owner_id
                              ? "Navigator assigned"
                              : "Fallback queue — awaiting navigator"}
                          </span>
                          {r.human_review && (
                            <p className="notice">
                              Human review required. No clinical recommendation
                              has been made.
                            </p>
                          )}
                          <p>
                            Responsible navigator:{" "}
                            {r.owner__username || "Organization fallback queue"}
                          </p>
                          <p className="pre">{r.summary}</p>
                          <p>
                            Patient-confirmed summary · {when(r.submitted_at)}
                          </p>
                          <p>
                            Unresolved questions:{" "}
                            {r.unresolved_questions || "None stated"}
                          </p>
                          {isStaff && !r.owner_id && (
                            <button
                              onClick={() =>
                                doAction({ action: "accept", id: r.id })
                              }
                            >
                              Accept responsibility
                            </button>
                          )}
                        </article>
                      ))}
                    {!data.requests.some((r: Row) => r.submitted_at) && (
                      <p>No submitted requests yet.</p>
                    )}
                    {!isStaff && (
                      <button
                        className="primary"
                        onClick={() => setTab("Intake")}
                      >
                        Ask a navigator or start a request
                      </button>
                    )}
                  </section>
                  <section>
                    <h2>Your next steps</h2>
                    {data.tasks.map((t: Row) => (
                      <article className="card" key={t.id}>
                        <h3>{t.title}</h3>
                        <p>
                          {t.done ? "Complete" : "Open"} · Due {t.due_date} ·
                          Owner {t.owner__username}
                        </p>
                        {!t.done &&
                          t.due_date <
                            new Date().toISOString().slice(0, 10) && (
                            <span className="badge warning">Overdue</span>
                          )}
                        <p>{t.barrier}</p>
                      </article>
                    ))}
                  </section>
                  <section>
                    <h2>Appointments</h2>
                    {data.appointments.length === 0 ? (
                      <p>No manually recorded appointments.</p>
                    ) : (
                      data.appointments.map((a: Row) => (
                        <article className="card" key={a.id}>
                          <h3>
                            {
                              data.referrals.find(
                                (r: Row) => r.id === a.referral_id,
                              )?.specialty
                            }
                          </h3>
                          <p>
                            {when(a.starts_at)} · {a.location}
                          </p>
                          <span className="badge">{a.status}</span>
                          <p>
                            Manually tracked; no external booking performed.
                          </p>
                        </article>
                      ))
                    )}
                  </section>
                  <section>
                    <h2>Service enrollment</h2>
                    {data.enrollment.map((e: Row, i: number) => (
                      <p key={i}>
                        {e.service} · {e.clinical_entity} · {e.location}
                      </p>
                    ))}
                  </section>
                </>
              )}
              {tab === "Intake" && (
                <Intake
                  key={selected}
                  saved={data.requests.find((r: Row) => !r.submitted_at)}
                  send={(d) => send(d as Row)}
                  inputMode={data.patient.input_mode}
                  spokenOutput={data.patient.spoken_output}
                />
              )}
              {tab === "Referrals" && (
                <>
                  <p>
                    Scheduling is a step toward completion. Closure requires
                    documented follow-through or an evidenced alternative
                    outcome.
                  </p>
                  {data.referrals.map((r: Row) => (
                    <article className="card" key={r.id}>
                      <h2>{r.specialty}</h2>
                      <span className="badge">{r.state}</span>
                      <p>
                        Due {r.due_date} · {r.owner__username || "Unassigned"}
                      </p>
                      <p>Supplied instructions: {r.instructions}</p>
                      {r.outcome && <p>Outcome: {r.outcome}</p>}
                      {r.evidence && <p>Documented evidence: {r.evidence}</p>}
                      <details>
                        <summary>Progress history</summary>
                        {data.transitions
                          .filter((t: Row) => t.referral_id === r.id)
                          .map((t: Row, i: number) => (
                            <p key={i}>
                              {t.previous} → {t.current} · {t.reason} ·{" "}
                              {t.actor__username} · {when(t.created_at)}
                            </p>
                          ))}
                      </details>
                      {isStaff && r.state !== "closed" && (
                        <ActionForm
                          title="Record referral progress"
                          fields={[
                            {
                              name: "state",
                              label: "Next referral state",
                              options: states.map((s) => [s, s]),
                              value: states[states.indexOf(r.state) + 1],
                            },
                            {
                              name: "outcome",
                              label: "Separate outcome",
                              options: [
                                "none",
                                "blocked",
                                "declined",
                                "canceled",
                              ].map((s) => [s, s]),
                            },
                            {
                              name: "reason",
                              label: "Reason",
                              type: "textarea",
                            },
                            {
                              name: "evidence",
                              label:
                                "Follow-through or alternative-outcome evidence",
                              type: "textarea",
                              optional: true,
                            },
                          ]}
                          submit={(d) =>
                            send({ ...d, action: "transition", id: r.id })
                          }
                        />
                      )}{" "}
                      {isStaff && r.state !== "closed" && (
                        <ActionForm
                          title="Record separate outcome"
                          fields={[
                            {
                              name: "outcome",
                              label: "Outcome without changing progress",
                              options: [
                                "none",
                                "blocked",
                                "declined",
                                "canceled",
                              ].map((x) => [x, x]),
                            },
                            {
                              name: "reason",
                              label: "Outcome reason and evidence",
                              type: "textarea",
                            },
                          ]}
                          submit={(d) =>
                            send({ ...d, action: "outcome", id: r.id })
                          }
                        />
                      )}
                    </article>
                  ))}
                  {isStaff && (
                    <div className="form-grid">
                      <ActionForm
                        title="Add referral"
                        fields={[
                          {
                            name: "specialty",
                            label: "Specialty from existing instructions",
                          },
                          {
                            name: "instructions",
                            label: "Supplied clinician instructions",
                            type: "textarea",
                          },
                          { name: "due_date", label: "Due date", type: "date" },
                          {
                            name: "owner_id",
                            label: "Responsible staff",
                            options: owners,
                          },
                        ]}
                        submit={(d) =>
                          send({
                            ...d,
                            action: "referral",
                            owner_id: Number(d.owner_id),
                          })
                        }
                      />
                      <ActionForm
                        title="Record manual appointment"
                        fields={[
                          {
                            name: "referral_id",
                            label: "Referral",
                            options: refs,
                          },
                          { name: "location", label: "Appointment location" },
                          {
                            name: "starts_at",
                            label: "Appointment date and time",
                            type: "datetime-local",
                          },
                        ]}
                        submit={(d) =>
                          send({
                            ...d,
                            action: "appointment",
                            referral_id: Number(d.referral_id),
                          })
                        }
                      />
                      {data.appointments.map((a: Row) => (
                        <ActionForm
                          key={a.id}
                          title={`Update appointment #${a.id}`}
                          fields={[
                            {
                              name: "status",
                              label: "Appointment status",
                              options: [
                                "planned",
                                "attended",
                                "missed",
                                "canceled",
                              ].map((x) => [x, x]),
                            },
                          ]}
                          submit={(d) =>
                            send({
                              ...d,
                              action: "appointment_status",
                              id: a.id,
                            })
                          }
                        />
                      ))}
                    </div>
                  )}
                </>
              )}
              {tab === "Messages" && (
                <>
                  <p>
                    Shared messages remain in this application. No email or SMS
                    is sent.
                  </p>
                  {data.messages.map((m: Row) => (
                    <article
                      key={m.id}
                      className={"card " + (m.internal ? "internal" : "")}
                    >
                      <h3>
                        {m.internal ? "Internal staff note" : "Shared message"}
                      </h3>
                      <p className="pre">{m.body}</p>
                      <p className="caption">
                        {m.author__username} · {when(m.created_at)}
                      </p>
                    </article>
                  ))}
                  <ActionForm
                    title="Save message"
                    fields={[
                      { name: "body", label: "Message", type: "textarea" },
                      ...(isStaff
                        ? [
                            {
                              name: "internal",
                              label:
                                "Internal staff note (hidden from patients and caregivers)",
                              type: "checkbox",
                            },
                          ]
                        : []),
                    ]}
                    submit={(d) =>
                      send({
                        ...d,
                        internal: d.internal || false,
                        action: "message",
                      })
                    }
                  />
                  <h2>In-app demonstration outbox</h2>
                  {data.outbox.map((n: Row) => (
                    <div key={n.id} className="card">
                      <p>
                        {n.description} · {n.state}
                      </p>
                      {isStaff && (
                        <button
                          onClick={() =>
                            doAction({
                              action: "notification_failure",
                              id: n.id,
                            })
                          }
                        >
                          Simulate notification failure
                        </button>
                      )}
                    </div>
                  ))}
                </>
              )}
              {tab === "Directory" && (
                <>
                  <p>
                    Independent fictional directory. No paid ranking. Your
                    choice of provider remains yours. Plan: {data.patient.plan}.
                    Each dimension needs separate evidence; stale after 30 days.
                  </p>
                  {data.providers.map((pr: Row) => (
                    <article key={pr.id} className="card">
                      <h2>{pr.name}</h2>
                      <p>
                        {pr.specialty} · {pr.location}
                      </p>
                      <p>
                        {pr.contact} · {pr.accessibility}
                      </p>
                      <p className="caption">Source: {pr.source}</p>
                      {dimensions.map((dim) => {
                        const checks = data.verifications.filter(
                          (v: Row) =>
                            v.provider_id === pr.id && v.dimension === dim,
                        );
                        return (
                          <details key={dim}>
                            <summary>
                              {dim}: {checks[0]?.status || "unknown"}
                              {checks[0]?.stale
                                ? " — stale, recheck required"
                                : ""}
                            </summary>
                            {checks.length ? (
                              checks.map((v: Row) => (
                                <p key={v.id}>
                                  FICTIONAL · {v.status} · {v.source} · {v.plan}{" "}
                                  · {v.location} · {when(v.checked_at)} ·{" "}
                                  {v.verifier}
                                  {v.stale ? " · STALE" : ""}
                                </p>
                              ))
                            ) : (
                              <p>No evidence recorded.</p>
                            )}
                          </details>
                        );
                      })}
                    </article>
                  ))}
                  {isStaff && (
                    <ActionForm
                      title="Record separate plan check"
                      fields={[
                        {
                          name: "provider_id",
                          label: "Provider and location",
                          options: providers,
                        },
                        {
                          name: "dimension",
                          label: "Verification dimension",
                          options: dimensions.map((x) => [x, x]),
                        },
                        {
                          name: "status",
                          label: "Evidence status",
                          options: [
                            "unknown",
                            "pending",
                            "verified",
                            "conflicting",
                          ].map((x) => [x, x]),
                        },
                        { name: "source", label: "Fictional evidence source" },
                      ]}
                      submit={(d) =>
                        send({
                          ...d,
                          action: "verify",
                          provider_id: Number(d.provider_id),
                        })
                      }
                    />
                  )}
                </>
              )}
              {tab === "Access" && (
                <>
                  <h2>Caregiver access</h2>
                  <p>
                    A separate account and explicit grant are required.
                    Revocation blocks future access without removing your
                    account.
                  </p>
                  {data.grants.map((g: Row) => (
                    <article className="card" key={g.id}>
                      <h3>{g.caregiver__username}</h3>
                      <p>
                        {g.revoked_at
                          ? "Revoked"
                          : g.can_message
                            ? "Read and communicate"
                            : "Read only"}
                      </p>
                      {!g.revoked_at && (
                        <button
                          onClick={() =>
                            doAction({ action: "revoke", id: g.id })
                          }
                        >
                          Revoke access
                        </button>
                      )}
                    </article>
                  ))}
                  <ActionForm
                    title="Grant caregiver access"
                    fields={[
                      {
                        name: "caregiver_id",
                        label: "Caregiver account",
                        options: data.available_caregivers.map((c: Row) => [
                          String(c.user_id),
                          c.user__username,
                        ]),
                      },
                      {
                        name: "can_message",
                        label:
                          "Allow intake and shared messages as well as reading",
                        type: "checkbox",
                      },
                    ]}
                    submit={(d) =>
                      send({
                        ...d,
                        action: "grant",
                        caregiver_id: Number(d.caregiver_id),
                      })
                    }
                  />
                  <ActionForm
                    title="Save communication preferences"
                    fields={[
                      {
                        name: "input_mode",
                        label: "Preferred input mode",
                        options: [
                          ["text", "Text"],
                          ["voice", "Voice"],
                        ],
                        value: data.patient.input_mode,
                      },
                      {
                        name: "spoken_output",
                        label: "Prefer spoken output (independent of input)",
                        type: "checkbox",
                        checked: data.patient.spoken_output,
                      },
                      {
                        name: "communication",
                        label: "Communication preference",
                        options: [
                          ["in-app text", "In-app text"],
                          ["assisted text", "Navigator-assisted text"],
                        ],
                      },
                    ]}
                    submit={(d) => send({ ...d, action: "preferences" })}
                  />
                  <button
                    onClick={async () => {
                      try {
                        const result = await api(
                          `/patients/${selected}/export/`,
                        );
                        const blob = new Blob(
                          [JSON.stringify(result, null, 2)],
                          { type: "application/json" },
                        );
                        const url = URL.createObjectURL(blob);
                        const link = document.createElement("a");
                        link.href = url;
                        link.download = "synthetic-patient.json";
                        link.click();
                        URL.revokeObjectURL(url);
                      } catch (e) {
                        setError((e as Error).message);
                      }
                    }}
                  >
                    Export my authorized demo records
                  </button>
                </>
              )}
              {tab === "Tasks" && (
                <>
                  <h2>Tasks and barriers</h2>
                  {data.tasks.map((t: Row) => (
                    <article className="card" key={t.id}>
                      <h3>{t.title}</h3>
                      <p>
                        Due {t.due_date} · {t.owner__username} ·{" "}
                        {t.done ? "Complete" : "Open"}
                      </p>
                      <p>{t.barrier}</p>
                      <button
                        onClick={() =>
                          doAction({
                            action: "task_done",
                            id: t.id,
                            done: !t.done,
                          })
                        }
                      >
                        {t.done ? "Reopen task" : "Mark task done"}
                      </button>
                    </article>
                  ))}
                  <div className="form-grid">
                    <ActionForm
                      title="Create task"
                      fields={[
                        { name: "title", label: "Actionable next step" },
                        {
                          name: "owner_id",
                          label: "Responsible staff",
                          options: owners,
                        },
                        { name: "due_date", label: "Due date", type: "date" },
                        {
                          name: "barrier",
                          label: "Barrier",
                          type: "textarea",
                          optional: true,
                        },
                      ]}
                      submit={(d) =>
                        send({
                          ...d,
                          action: "task",
                          owner_id: Number(d.owner_id),
                        })
                      }
                    />
                    <ActionForm
                      title="Record staff time"
                      fields={[
                        {
                          name: "minutes",
                          label: "Minutes (operational, not billable)",
                          type: "number",
                        },
                      ]}
                      submit={(d) => send({ ...d, action: "time" })}
                    />
                  </div>
                </>
              )}
            </>
          )}
          {tab === "Reports" && extra && !Array.isArray(extra) && (
            <>
              <ActionForm
                title="Select reporting period"
                fields={[
                  { name: "start", label: "Start date", type: "date" },
                  { name: "end", label: "End date", type: "date" },
                ]}
                submit={async (d) => {
                  setExtra(
                    await api(`/reports/?start=${d.start}&end=${d.end}`),
                  );
                }}
              />
              <h2>Synthetic operational measures</h2>
              <p>{extra.definitions}</p>
              <dl className="metrics">
                {Object.entries(extra)
                  .filter(([k]) => !["definitions", "synthetic"].includes(k))
                  .map(([k, v]) => (
                    <div key={k}>
                      <dt>{label(k)}</dt>
                      <dd>{v === null ? "No observations" : String(v)}</dd>
                    </div>
                  ))}
              </dl>
              <p>No clinical benefit or cost savings are inferred.</p>
            </>
          )}
          {tab === "Organization" && extra && !Array.isArray(extra) && (
            <>
              <h2>{extra.name}</h2>
              <ActionForm
                title="Save service hours"
                fields={[
                  {
                    name: "service_hours",
                    label: "Service hours",
                    value: extra.service_hours,
                  },
                  {
                    name: "response_expectation",
                    label: "Response expectation and fallback",
                    value: extra.response_expectation,
                  },
                ]}
                submit={async (d) => {
                  setExtra(await api("/organization/", d));
                  await init();
                }}
              />
              <ActionForm
                title="Import fictional directory rows"
                fields={[
                  {
                    name: "providers",
                    label: "Fictional provider JSON array (1–50 rows)",
                    type: "textarea",
                  },
                ]}
                submit={async (d) => {
                  const result = await api("/directory-import/", {
                    providers: JSON.parse(d.providers),
                  });
                  await load();
                  return result;
                }}
              />
              <h2>Staff membership</h2>
              {extra.staff.map((s: Row) => (
                <ActionForm
                  key={s.user_id}
                  title={`Update role for ${s.user__username}`}
                  fields={[
                    {
                      name: "role",
                      label: "Staff role",
                      options: [
                        ["navigator", "Navigator"],
                        ["admin", "Organization admin"],
                      ],
                      value: s.role,
                    },
                  ]}
                  submit={async (d) => {
                    setExtra(
                      await api("/organization/", {
                        ...d,
                        action: "staff_role",
                        user_id: s.user_id,
                      }),
                    );
                  }}
                />
              ))}
              <p>
                Invitations are seeded locally. Secure invitation delivery and
                staff MFA remain live-launch prerequisites.
              </p>
            </>
          )}
          {tab === "Audit" && Array.isArray(extra) && (
            <>
              <p>
                Organization-only history. Event metadata excludes message and
                intake content. Most recent 200 events.
              </p>
              <div
                className="table-scroll"
                tabIndex={0}
                role="region"
                aria-label="Scrollable audit history"
              >
                <table>
                  <caption>Access and changes</caption>
                  <thead>
                    <tr>
                      <th>Action</th>
                      <th>Actor</th>
                      <th>Patient ID</th>
                      <th>Time</th>
                    </tr>
                  </thead>
                  <tbody>
                    {extra.map((a: Row) => (
                      <tr key={a.id}>
                        <td>{a.action}</td>
                        <td>{a.actor__username}</td>
                        <td>{a.patient_id || "—"}</td>
                        <td>{when(a.created_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </main>
      </div>
      <footer>
        Synthetic prototype · Administrative coordination only · Clinical and
        security reviews required before live use.
      </footer>
    </>
  );
}
