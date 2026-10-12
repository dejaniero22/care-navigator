import { afterEach, expect, test, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Intake } from "./Intake";
import type { SpeechAdapter } from "./speech";
afterEach(cleanup);
function fakeSpeech(available = true): SpeechAdapter {
  return {
    available,
    start: vi.fn(),
    stop: vi.fn(),
    speak: vi.fn(),
    cancel: vi.fn(),
  };
}

test("input and output modes are independent and preserve draft and confirmation", async () => {
  const user = userEvent.setup();
  const speech = fakeSpeech();
  const send = vi
    .fn()
    .mockResolvedValue({ summary: "Confirmed transport need" });
  render(<Intake send={send} speech={speech} />);
  await user.type(screen.getByLabelText("Your goal"), "Arrange transport");
  await user.click(
    screen.getByRole("button", { name: "Save and draft summary" }),
  );
  await user.click(
    screen.getByLabelText("I reviewed and confirmed this summary"),
  );
  await user.selectOptions(screen.getByLabelText("Input mode"), "voice");
  await user.click(screen.getByLabelText("Spoken responses"));
  expect(
    (screen.getByLabelText("Your goal") as HTMLTextAreaElement).value,
  ).toBe("Arrange transport");
  expect(
    (
      screen.getByLabelText(
        "I reviewed and confirmed this summary",
      ) as HTMLInputElement
    ).checked,
  ).toBe(true);
  await user.selectOptions(screen.getByLabelText("Input mode"), "text");
  expect(
    (screen.getByLabelText("Spoken responses") as HTMLInputElement).checked,
  ).toBe(true);
  expect(
    (screen.getByLabelText("Editable summary") as HTMLTextAreaElement).value,
  ).toBe("Confirmed transport need");
  await user.click(screen.getByRole("button", { name: "Submit request" }));
  expect(send.mock.calls[1][0]).toMatchObject({
    action: "submit",
    goal: "Arrange transport",
    summary: "Confirmed transport need",
    confirmed: true,
  });
});
test("speech requires permission, visible listening and failures keep typing available", async () => {
  const user = userEvent.setup();
  const speech = fakeSpeech();
  render(<Intake send={vi.fn()} speech={speech} />);
  await user.type(screen.getByLabelText("Your goal"), "Keep this draft");
  await user.selectOptions(screen.getByLabelText("Input mode"), "voice");
  expect(
    (
      screen.getByRole("button", {
        name: "Start listening",
      }) as HTMLButtonElement
    ).disabled,
  ).toBe(true);
  await user.click(
    screen.getByLabelText(
      "I allow browser speech for this synthetic demonstration",
    ),
  );
  speech.start = vi.fn((_result, error) =>
    error("Speech failed. Continue typing."),
  );
  await user.click(screen.getByRole("button", { name: "Start listening" }));
  expect(screen.getByText("Speech failed. Continue typing.")).toBeTruthy();
  expect(
    (screen.getByLabelText("Your goal") as HTMLTextAreaElement).value,
  ).toBe("Keep this draft");
  await user.type(screen.getByLabelText("Your goal"), " safely");
  expect(
    (screen.getByLabelText("Your goal") as HTMLTextAreaElement).value,
  ).toBe("Keep this draft safely");
});
test("assistant failure permits corrected text submission and human handoff", async () => {
  const user = userEvent.setup();
  const send = vi
    .fn()
    .mockRejectedValueOnce(new Error("offline"))
    .mockResolvedValue({ ok: true });
  render(<Intake send={send} speech={fakeSpeech(false)} />);
  await user.type(screen.getByLabelText("Your goal"), "Help with referral");
  await user.click(
    screen.getByRole("button", { name: "Save and draft summary" }),
  );
  expect(screen.getByText(/Assistant or saving unavailable/)).toBeTruthy();
  await user.type(
    screen.getByLabelText("Editable summary"),
    "My reviewed referral request",
  );
  await user.click(
    screen.getByLabelText("I reviewed and confirmed this summary"),
  );
  await user.click(screen.getByRole("button", { name: "Ask a navigator" }));
  expect(send.mock.calls[1][0]).toMatchObject({
    action: "handoff",
    summary: "My reviewed referral request",
    confirmed: true,
  });
});
test("editing after confirmation requires fresh confirmation", async () => {
  const user = userEvent.setup();
  render(<Intake send={vi.fn()} speech={fakeSpeech()} />);
  await user.type(screen.getByLabelText("Editable summary"), "Initial summary");
  await user.click(
    screen.getByLabelText("I reviewed and confirmed this summary"),
  );
  await user.type(screen.getByLabelText("Your goal"), "Updated goal");
  expect(
    (
      screen.getByLabelText(
        "I reviewed and confirmed this summary",
      ) as HTMLInputElement
    ).checked,
  ).toBe(false);
  expect(
    (
      screen.getByRole("button", {
        name: "Submit request",
      }) as HTMLButtonElement
    ).disabled,
  ).toBe(true);
});
