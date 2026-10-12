import { test, expect, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
async function signIn(page: Page, role: string) {
  await page.goto("/");
  await page.getByLabel("Username", { exact: true }).fill(`river.${role}`);
  await page.getByLabel("Password", { exact: true }).fill("DemoOnly-2026!");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("button", { name: "Sign out" })).toBeVisible();
}
async function tab(page: Page, name: string) {
  await page
    .getByRole("navigation")
    .getByRole("button", { name, exact: true })
    .click();
}
async function accessibility(page: Page) {
  const result = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
    .analyze();
  expect(result.violations).toEqual([]);
}

test("patient intake to navigator acceptance, referral follow-through and patient-visible progress", async ({
  page,
  context,
}, testInfo) => {
  await signIn(page, "patient");
  if (
    await page
      .getByRole("button", { name: "Accept service scope", exact: true })
      .count()
  ) {
    await page
      .getByLabel("I understand and accept the synthetic demo service scope")
      .check();
    await page
      .getByRole("button", { name: "Accept service scope", exact: true })
      .click();
    await expect(
      page.getByRole("heading", { name: "Review your service scope" }),
    ).toHaveCount(0);
  }
  await accessibility(page);
  await tab(page, "Intake");
  const goal = `Arrange fictional neurology transport ${testInfo.project.name} ${Date.now()}`;
  await page
    .getByRole("textbox", { name: "Your goal", exact: true })
    .fill(goal);
  await page
    .getByRole("textbox", {
      name: "Existing referral instructions (supplied, not verified)",
      exact: true,
    })
    .fill("Existing demo clinician referral");
  await page
    .getByRole("textbox", { name: "Coverage you have stated", exact: true })
    .fill("Fictional Silver Sacramento PPO");
  await page.getByRole("button", { name: "Save and draft summary" }).click();
  await expect(
    page.getByRole("textbox", { name: "Editable summary", exact: true }),
  ).toHaveValue(new RegExp(goal));
  await page.getByLabel("I reviewed and confirmed this summary").check();
  await page.getByLabel("Input mode").selectOption("voice");
  await expect(
    page.getByRole("button", { name: "Start listening" }),
  ).toBeDisabled();
  await page.getByLabel("Spoken responses").check();
  await page.getByLabel("Input mode").selectOption("text");
  await expect(
    page.getByRole("textbox", { name: "Your goal", exact: true }),
  ).toHaveValue(goal);
  await expect(
    page.getByLabel("I reviewed and confirmed this summary"),
  ).toBeChecked();
  await accessibility(page);
  await page
    .getByRole("button", { name: "Ask a navigator", exact: true })
    .click();
  await expect(
    page.getByText(/Request submitted to the organization queue/),
  ).toBeVisible();
  await tab(page, "Home");
  await expect(
    page.getByRole("heading", { name: goal, exact: true }),
  ).toBeVisible();
  await page.screenshot({
    path: `test-results/${testInfo.project.name}-patient.png`,
    fullPage: true,
  });
  await page.getByRole("button", { name: "Sign out" }).click();
  await signIn(page, "navigator");
  await expect(
    page.getByRole("heading", { name: "Navigator queue" }),
  ).toBeVisible();
  const card = page
    .getByRole("article")
    .filter({ has: page.getByRole("heading", { name: goal, exact: true }) });
  await card.getByRole("button", { name: "Accept responsibility" }).click();
  await expect(
    card.getByText("Navigator assigned", { exact: true }),
  ).toBeVisible();
  await tab(page, "Tasks");
  const taskForm = page
    .locator("form")
    .filter({
      has: page.getByRole("heading", { name: "Create task", exact: true }),
    });
  await taskForm
    .getByLabel("Actionable next step")
    .fill("Confirm fictional transport");
  await taskForm
    .getByLabel("Due date")
    .fill(new Date().toISOString().slice(0, 10));
  await taskForm
    .getByRole("button", { name: "Create task", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Confirm fictional transport" }).first(),
  ).toBeVisible();
  await tab(page, "Referrals");
  // Create a fresh referral so the journey is repeatable without resetting prior demo work.
  const specialty = `Demo specialty ${testInfo.project.name} ${Date.now()}`;
  const create = page
    .locator("form")
    .filter({
      has: page.getByRole("heading", { name: "Add referral", exact: true }),
    });
  await create
    .getByLabel("Specialty from existing instructions")
    .fill(specialty);
  await create
    .getByLabel("Supplied clinician instructions")
    .fill("Fictional existing referral");
  await create
    .getByLabel("Due date")
    .fill(new Date().toISOString().slice(0, 10));
  await create
    .getByRole("button", { name: "Add referral", exact: true })
    .click();
  const referral = page
    .getByRole("article")
    .filter({
      has: page.getByRole("heading", { name: specialty, exact: true }),
    });
  const progress = referral
    .locator("form")
    .filter({
      has: page.getByRole("heading", {
        name: "Record referral progress",
        exact: true,
      }),
    });
  const appointment = page
    .locator("form")
    .filter({
      has: page.getByRole("heading", {
        name: "Record manual appointment",
        exact: true,
      }),
    });
  await appointment
    .getByRole("combobox", { name: "Referral", exact: true })
    .selectOption({ label: specialty });
  await appointment
    .getByLabel("Appointment location")
    .fill("Fictional Sacramento office");
  await appointment
    .getByLabel("Appointment date and time")
    .fill("2026-12-01T10:00");
  const appointmentResponse = page.waitForResponse(
    (r) =>
      r.url().endsWith("/actions/") &&
      r.request().postDataJSON()?.action === "appointment",
  );
  await appointment
    .getByRole("button", { name: "Record manual appointment", exact: true })
    .click();
  const appointmentId = (await (await appointmentResponse).json()).id;
  await expect(appointment.getByRole("status")).toHaveText("Saved.");
  for (const state of [
    "review needed",
    "sent",
    "accepted",
    "scheduling",
    "scheduled",
    "attended",
    "follow-up received",
    "closed",
  ]) {
    if (state === "attended") {
      const update = page
        .locator("form")
        .filter({
          has: page.getByRole("heading", {
            name: `Update appointment #${appointmentId}`,
            exact: true,
          }),
        });
      await update.getByLabel("Appointment status").selectOption("attended");
      await update
        .getByRole("button", {
          name: `Update appointment #${appointmentId}`,
          exact: true,
        })
        .click();
      await expect(update.getByRole("status")).toHaveText("Saved.");
    }
    await progress.getByLabel("Next referral state").selectOption(state);
    await progress
      .getByLabel("Reason", { exact: true })
      .fill("Fictional manual progress");
    if (state === "closed")
      await progress
        .getByLabel("Follow-through or alternative-outcome evidence")
        .fill("Fictional attendance and authorized follow-up documented");
    await progress
      .getByRole("button", { name: "Record referral progress", exact: true })
      .click();
    await expect(referral.locator(".badge")).toHaveText(state);
  }
  await accessibility(page);
  await page.screenshot({
    path: `test-results/${testInfo.project.name}-navigator.png`,
    fullPage: true,
  });
  await tab(page, "Reports");
  await expect(
    page.getByRole("heading", { name: "Synthetic operational measures" }),
  ).toBeVisible();
  await accessibility(page);
  await page.getByRole("button", { name: "Sign out" }).click();
  await signIn(page, "patient");
  await tab(page, "Referrals");
  const visible = page
    .getByRole("article")
    .filter({
      has: page.getByRole("heading", { name: specialty, exact: true }),
    });
  await expect(visible.locator(".badge")).toHaveText("closed");
  await tab(page, "Messages");
  await expect(
    page.getByText(
      "Internal demo workload note; never shared with patient or caregiver.",
    ),
  ).toHaveCount(0);
});

test("caregiver revocation blocks already-authenticated account; keyboard and admin paths", async ({
  page,
  browser,
}) => {
  await signIn(page, "patient");
  await tab(page, "Access");
  const grant = page
    .locator("form")
    .filter({
      has: page.getByRole("heading", {
        name: "Grant caregiver access",
        exact: true,
      }),
    });
  await grant
    .getByLabel("Allow intake and shared messages as well as reading")
    .check();
  await grant
    .getByRole("button", { name: "Grant caregiver access", exact: true })
    .click();
  await expect(grant.getByRole("status")).toHaveText("Saved.");
  const caregiverContext = await browser.newContext({
    baseURL: "http://127.0.0.1:5173",
  });
  const caregiver = await caregiverContext.newPage();
  await signIn(caregiver, "caregiver");
  await expect(
    caregiver.getByRole("heading", { name: /Welcome/ }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Revoke access", exact: true })
    .click();
  await expect(page.getByText("Revoked", { exact: true })).toBeVisible();
  await caregiver.getByRole("button", { name: "Refresh records" }).click();
  await expect(
    caregiver.getByText(/No authorized patient access/),
  ).toBeVisible();
  await caregiverContext.close();
  // Restore the demo grant via the patient, without resetting records.
  await grant
    .getByRole("button", { name: "Grant caregiver access", exact: true })
    .click();
  await expect(grant.getByRole("status")).toHaveText("Saved.");
  await page.getByRole("button", { name: "Sign out" }).click();
  await page.goto("/");
  await expect(page.getByLabel("Username", { exact: true })).toBeVisible();
  await page.keyboard.press("Tab");
  await expect(page.getByLabel("Username", { exact: true })).toBeFocused();
  await page.keyboard.type("river.admin");
  await page.keyboard.press("Tab");
  await page.keyboard.type("DemoOnly-2026!");
  await page.keyboard.press("Tab");
  await page.keyboard.press("Enter");
  await expect(page.getByRole("button", { name: "Sign out" })).toBeVisible();
  await tab(page, "Organization");
  await expect(
    page.getByRole("heading", { name: "River City Navigation (fictional)" }),
  ).toBeVisible();
  await accessibility(page);
  await tab(page, "Audit");
  await expect(page.getByRole("table")).toBeVisible();
  await accessibility(page);
  await page.evaluate(() => (document.documentElement.style.fontSize = "200%"));
  await expect(
    page.getByRole("heading", { name: "Audit", exact: true }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
});
