import { expect, test } from "../../../../../frontend/e2e/playwright";
import { expectNoHorizontalOverflow } from "../../../mystic_auth/e2e/support/browserLayoutAssertions";

test.describe("app landing page browser behavior", () => {
  test("renders the product story and keeps both auth paths reachable", async ({ page }) => {
    await page.goto("/");

    const brandHome = page.locator('header a[aria-label]').first();
    const brandHomeLabel = await brandHome.getAttribute("aria-label");
    const title = await page.title();

    expect(title).not.toBe("");
    expect(brandHomeLabel).toContain(title);
    await expect(page.getByRole("link", { name: /log in/i }).first()).toBeVisible();
    await expect(page.getByRole("link", { name: /create your workspace/i }).first()).toBeVisible();
    await expect(page.getByRole("main")).toBeVisible();
    await expect(page.getByRole("heading", { name: /make your next move/i })).toBeVisible();
    await expect(page.getByRole("heading", { name: /your experience, finally working together/i })).toBeVisible();
    await expect(page.getByRole("heading", { name: /from experience to next step/i })).toBeVisible();
    await expect(page.getByText("Career workspace", { exact: true })).toBeVisible();
    await expect(page.locator("main article")).toHaveCount(4);
  });

  test("uses the intended signup and login destinations", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByRole("link", { name: /build your workspace/i })).toHaveAttribute("href", "/signup");
    await expect(page.getByRole("link", { name: /log in/i }).first()).toHaveAttribute("href", "/login");
    await expect(page.getByRole("link", { name: /privacy policy/i })).toHaveAttribute("href", "/privacy");
    await expect(page.getByRole("link", { name: /terms of service/i })).toHaveAttribute("href", "/terms");
  });

  test("supports keyboard skip navigation and remains usable at zoom", async ({ page }) => {
    await page.goto("/");

    const skipLink = page.getByRole("link", { name: /skip to main content/i });
    await skipLink.focus();
    await expect(skipLink).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(page.getByRole("main")).toBeFocused();

    for (const zoom of ["1.25", "1.5"]) {
      await page.evaluate((value) => { document.documentElement.style.zoom = value; }, zoom);
      await expectNoHorizontalOverflow(page);
      await expect(page.getByRole("main")).toBeVisible();
    }
  });

  test("stays usable in a laptop viewport and on a narrow screen", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("/");
    await expectNoHorizontalOverflow(page);
    await expect(page.getByRole("heading", { name: /make your next move/i })).toBeVisible();

    await page.setViewportSize({ width: 390, height: 844 });
    await page.reload();
    await expectNoHorizontalOverflow(page);
    await expect(page.getByRole("heading", { name: /make your next move/i })).toBeVisible();
    await expect(page.getByRole("link", { name: /create your workspace/i }).first()).toBeVisible();
  });
});
