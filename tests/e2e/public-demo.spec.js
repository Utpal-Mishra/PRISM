const { test, expect } = require("@playwright/test");
const AxeBuilder = require("@axe-core/playwright").default;

test("public demo loads synthetic data and switches analysis views", async ({ page, isMobile }) => {
  await page.goto("/");
  await expect(page.locator("#datasetName")).toHaveText(
    /PRISM synthetic enterprise dataset/i
  );
  await expect(page.locator("#rowCountTag")).not.toHaveText("0 rows", {
    timeout: 15000,
  });

  const relationshipsNav = isMobile
    ? page.locator('.mobile-dock [data-view="relationships"]')
    : page.locator('.nav-list [data-view="relationships"]');
  await relationshipsNav.click();
  await expect(page.locator("#view-relationships")).toHaveClass(/active/);
  await expect(page.locator("#correlationList")).toBeVisible();
});

test("mobile navigation remains operable", async ({ page, isMobile }) => {
  test.skip(!isMobile, "mobile project only");
  await page.goto("/");
  await expect(page.locator(".mobile-dock")).toBeVisible();

  await page.locator('.mobile-dock [data-view="forecast"]').click();
  await expect(page.locator("#view-forecast")).toHaveClass(/active/);

  const menu = page.locator("#menuToggle");
  await menu.click();
  await expect(menu).toHaveAttribute("aria-expanded", "true");
  await expect(page.locator("#sidebar")).toBeVisible();
});

test("public demo has no serious or critical axe violations", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("#rowCountTag")).not.toHaveText("0 rows", {
    timeout: 15000,
  });

  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
    .analyze();

  const blocking = results.violations.filter((item) =>
    ["serious", "critical"].includes(item.impact)
  );
  expect(blocking).toEqual([]);
});

test("initial browser response stays inside the P1 smoke threshold", async ({ page }) => {
  const started = Date.now();
  await page.goto("/");
  await expect(page.locator("#rowCountTag")).not.toHaveText("0 rows", {
    timeout: 15000,
  });
  const readyMs = Date.now() - started;

  const navigation = await page.evaluate(() => {
    const entry = performance.getEntriesByType("navigation")[0];
    return {
      domContentLoadedMs: entry ? entry.domContentLoadedEventEnd : 0,
    };
  });

  expect(navigation.domContentLoadedMs).toBeLessThan(6000);
  expect(readyMs).toBeLessThan(15000);
});
