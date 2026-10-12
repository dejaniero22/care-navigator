import { useEffect, useMemo, useState } from "react";
import { browserSpeech, type SpeechAdapter } from "./speech";

type Draft = {
  key: string;
  goal: string;
  instructions: string;
  providers: string;
  coverage: string;
  barriers: string;
  communication_needs: string;
  summary: string;
  unresolved_questions: string;
};
const empty = (): Draft => ({
  key: crypto.randomUUID(),
  goal: "",
  instructions: "",
  providers: "",
  coverage: "",
  barriers: "",
  communication_needs: "",
  summary: "",
  unresolved_questions: "",
});
export function Intake({
  saved,
  send,
  speech: provided,
  inputMode = "text",
  spokenOutput = false,
}: {
  saved?: Partial<Draft>;
  send: (data: unknown) => Promise<any>;
  speech?: SpeechAdapter;
  inputMode?: string;
  spokenOutput?: boolean;
}) {
  const [draft, setDraft] = useState<Draft>(() => ({ ...empty(), ...saved }));
  const [input, setInput] = useState(inputMode);
  const [output, setOutput] = useState(spokenOutput);
  const [confirmed, setConfirmed] = useState(false);
  const [consent, setConsent] = useState(false);
  const [listening, setListening] = useState(false);
  const [handoff, setHandoff] = useState(false);
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const speech = useMemo(() => provided || browserSpeech(), [provided]);
  useEffect(() => () => speech.cancel(), [speech]);
  function edit(key: keyof Draft, value: string) {
    setDraft((x) => ({ ...x, [key]: value }));
    setConfirmed(false);
  }
  async function preview() {
    setBusy(true);
    setStatus("");
    try {
      const result = await send({ ...draft, action: "draft" });
      setDraft((x) => ({ ...x, summary: result.summary }));
      setConfirmed(false);
      setStatus(
        result.human_review
          ? "A navigator must review this concern. This service cannot provide clinical advice."
          : "Draft saved. Review and correct the summary below.",
      );
    } catch {
      setStatus(
        "Assistant or saving unavailable. Your text is preserved. Write a summary below and retry submission when service returns.",
      );
    } finally {
      setBusy(false);
    }
  }
  async function submit(toHuman: boolean) {
    if (!confirmed || !draft.summary.trim()) {
      setStatus("Review the summary and confirm it before submitting.");
      return;
    }
    setBusy(true);
    try {
      await send({
        ...draft,
        confirmed,
        action: toHuman || handoff ? "handoff" : "submit",
      });
      setSubmitted(true);
      setStatus(
        "Request submitted to the organization queue. A navigator can accept responsibility during service hours.",
      );
    } catch (e) {
      setStatus((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  function startVoice() {
    if (!consent) {
      setStatus("Review and allow browser speech first.");
      return;
    }
    setListening(true);
    speech.start(
      (value) => {
        if (/ask (a |my )?navigator/i.test(value)) {
          setHandoff(true);
          setStatus(
            "Navigator assistance selected. Confirm your summary to send the handoff.",
          );
        } else edit("goal", value);
        setListening(false);
      },
      (error) => {
        setStatus(error);
        setListening(false);
      },
    );
  }
  return (
    <section aria-labelledby="intake-title">
      <h2 id="intake-title">Tell us what you need</h2>
      <p>
        Administrative help with existing referrals. All information in this
        demonstration must be fictional.
      </p>
      <div className="mode-row">
        <label>
          Input mode
          <select
            value={input}
            onChange={(e) => {
              setInput(e.target.value);
              speech.stop();
              setListening(false);
            }}
          >
            <option value="text">Type</option>
            <option value="voice">Speak</option>
          </select>
        </label>
        <label className="check">
          <input
            type="checkbox"
            checked={output}
            onChange={(e) => setOutput(e.target.checked)}
          />{" "}
          Spoken responses
        </label>
      </div>
      {(input === "voice" || output) && (
        <div className="notice">
          <p>
            Browser speech may send audio to an external browser provider. Use
            fictional information only. This application does not retain raw
            audio. Speech availability depends on your browser. Say “Ask a
            navigator” to select human assistance, then review and confirm.
          </p>
          <label className="check">
            <input
              type="checkbox"
              checked={consent}
              onChange={(e) => {
                setConsent(e.target.checked);
                if (!e.target.checked) {
                  speech.cancel();
                  setListening(false);
                }
              }}
            />{" "}
            I allow browser speech for this synthetic demonstration
          </label>
          <button
            type="button"
            disabled={!consent || !speech.available || listening || submitted}
            onClick={startVoice}
          >
            Start listening
          </button>
          <button
            type="button"
            onClick={() => {
              speech.stop();
              setListening(false);
            }}
          >
            Stop listening
          </button>
          <button
            type="button"
            onClick={() => {
              speech.cancel();
              setListening(false);
            }}
          >
            Cancel speech
          </button>
          <p role="status">
            {listening
              ? "Listening — speak your administrative goal"
              : speech.available
                ? "Not listening"
                : "Speech unavailable — typing remains available"}
          </p>
        </div>
      )}
      {(
        [
          "goal",
          "instructions",
          "providers",
          "coverage",
          "barriers",
          "communication_needs",
        ] as const
      ).map((key) => (
        <label key={key}>
          {
            {
              goal: "Your goal",
              instructions:
                "Existing referral instructions (supplied, not verified)",
              providers: "Known providers",
              coverage: "Coverage you have stated",
              barriers: "Barriers or access needs",
              communication_needs: "Communication needs",
            }[key]
          }
          <textarea
            value={draft[key]}
            maxLength={4000}
            disabled={submitted}
            onChange={(e) => edit(key, e.target.value)}
          />
        </label>
      ))}
      <button
        disabled={busy || submitted || !draft.goal.trim()}
        onClick={preview}
      >
        Save and draft summary
      </button>
      <p className="caption">
        Deterministic demo draft. No external AI; no clinical advice.
      </p>
      <label>
        Editable summary
        <textarea
          value={draft.summary}
          maxLength={4000}
          disabled={submitted}
          onChange={(e) => edit("summary", e.target.value)}
        />
      </label>
      <label>
        Unresolved questions
        <textarea
          value={draft.unresolved_questions}
          maxLength={4000}
          disabled={submitted}
          onChange={(e) => edit("unresolved_questions", e.target.value)}
        />
      </label>
      {output && (
        <button
          onClick={() => {
            if (consent)
              speech.speak(
                draft.summary ||
                  "Type your goal, then review and confirm your summary.",
              );
            else
              setStatus(
                "Allow browser speech in Speak mode before using spoken responses.",
              );
          }}
        >
          Read summary aloud
        </button>
      )}
      <label className="check">
        <input
          type="checkbox"
          checked={confirmed}
          disabled={submitted}
          onChange={(e) => setConfirmed(e.target.checked)}
        />{" "}
        I reviewed and confirmed this summary
      </label>
      <div className="actions">
        <button
          className="primary"
          disabled={busy || submitted || !confirmed}
          onClick={() => submit(false)}
        >
          Submit request
        </button>
        <button
          disabled={busy || submitted}
          onClick={() => {
            setHandoff(true);
            if (confirmed) void submit(true);
            else
              setStatus(
                "Navigator assistance selected. Review and confirm your summary before sending.",
              );
          }}
        >
          Ask a navigator
        </button>
      </div>
      <p role="status">{status}</p>
      {submitted && (
        <button
          onClick={() => {
            setDraft(empty());
            setConfirmed(false);
            setSubmitted(false);
            setHandoff(false);
            setStatus("");
          }}
        >
          Start another request
        </button>
      )}
    </section>
  );
}
