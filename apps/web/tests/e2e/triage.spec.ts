import { expect, test } from "@playwright/test";

// Recruiter flow: landing → demo login → triage queue (every route) → run your own claim.
test("claims triage shows every route and runs a visitor claim", async ({ page }) => {
  await page.goto("/login");
  await page.getByRole("button", { name: /Explore the live demo/ }).click();
  await page.waitForURL(/dashboard/);
  await page.goto("/triage");

  const routes: [string, RegExp][] = [
    ["TRI-1001", /Auto-approved/],
    ["TRI-1003", /Fraud flag/],
    ["TRI-1004", /Not covered/],
    ["TRI-1005", /Low confidence/],
  ];
  for (const [num, label] of routes) {
    const sample = page.getByTestId(`triage-sample-${num}`);
    await expect(sample).toContainText(label);
    await sample.click();
    await expect(page.getByTestId("triage-result")).toContainText(label);
  }

  await page.getByLabel("Vehicle use").selectOption("rideshare");
  await page.getByRole("button", { name: /Run triage/ }).click();
  await expect(page.getByTestId("triage-own-result")).toContainText("Not covered");
});
