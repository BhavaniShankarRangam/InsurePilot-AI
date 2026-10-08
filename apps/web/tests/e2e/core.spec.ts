import { expect, test, type Page } from "@playwright/test";

async function demoLogin(page: Page) {
  await page.goto("/login");
  await page.getByRole("button", { name: /Explore the live demo/ }).click();
  await page.waitForURL(/dashboard/);
}

test("landing page loads with primary CTA", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("finally works");
  await expect(page.getByRole("link", { name: /Try InsurePilot/ }).first()).toBeVisible();
});

test("protected routes redirect to login", async ({ page }) => {
  await page.context().clearCookies();
  await page.goto("/dashboard");
  await expect(page).toHaveURL(/login\?next=%2Fdashboard/);
});

test("dashboard shows score, priorities and actions", async ({ page }) => {
  await demoLogin(page);
  await expect(page.getByRole("img", { name: /Insurance Health Score/ })).toBeVisible();
  await expect(page.getByText("What needs your attention?")).toBeVisible();
});

test("AI answers with citations and requires approval for actions", async ({ page, isMobile }) => {
  test.skip(isMobile, "covered on desktop");
  await demoLogin(page);
  await page.getByRole("button", { name: /Open AI Command Center/ }).click();
  await page.getByLabel("Message InsurePilot").fill("Prepare my claim");
  await page.keyboard.press("Enter");
  await expect(page.getByText("Needs your approval").first()).toBeVisible({ timeout: 60_000 });
  await page.getByRole("button", { name: "Cancel" }).first().click();
  await expect(page.getByText("Decision recorded").first()).toBeVisible();
});

test("command palette searches the portfolio", async ({ page, isMobile }) => {
  test.skip(isMobile, "keyboard shortcut is desktop-only");
  await demoLogin(page);
  await expect(page.getByRole("img", { name: /Insurance Health Score/ })).toBeVisible(); // hydrated
  await page.keyboard.press("Control+k");
  await page.keyboard.type("water");
  await expect(page.getByText(/Ask InsurePilot/)).toBeVisible();
});

test("universe offers an accessible 2D view", async ({ page }) => {
  await demoLogin(page);
  await page.goto("/universe");
  await page.getByRole("radio", { name: "2D" }).click();
  await expect(page.getByRole("list", { name: "Your insurance network" })).toBeVisible();
});

test("3D universe and AI chat run without console errors", async ({ page, isMobile }) => {
  test.skip(isMobile, "desktop WebGL check");
  const errors: string[] = [];
  page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
  page.on("pageerror", (e) => errors.push(e.message));
  await demoLogin(page);
  await page.goto("/universe");
  await expect(page.getByRole("radio", { name: "3D" })).toBeVisible();
  await page.waitForTimeout(2500);
  await page.mouse.move(720, 560);
  await page.waitForTimeout(800);
  expect(errors).toEqual([]);
});
