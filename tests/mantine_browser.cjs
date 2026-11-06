/* Browser contract for true Mantine/Font Awesome islands with a working
   no-JS fallback. Fixtures have no backend authority; Django tests still own it. */
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const { spawn } = require('node:child_process');

const server = spawn('python3', ['-m', 'http.server', '8798', '--bind', '127.0.0.1', '--directory', '.'], { stdio: 'ignore' });
const base = 'http://127.0.0.1:8798/tests/fixtures/mantine.html';
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function ensureServer() {
  for (let i = 0; i < 45; i += 1) {
    try {
      if ((await fetch(base)).ok) return;
    } catch {}
    await sleep(100);
  }
  throw Error('Fixture server did not start');
}

(async () => {
  let browser;
  try {
    await ensureServer();
    browser = await chromium.launch();
    const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', (err) => errors.push(err.message));
    await page.goto(base, { waitUntil: 'networkidle' });

    await page.getByTestId('bm-mantine-dashboard').waitFor();
    await page.getByTestId('bm-mantine-membership').waitFor();
    await page.getByTestId('bm-mantine-invitation').waitFor();
    const desktopColumns = await page.locator('.bm-membership-grid > div').evaluateAll((nodes) =>
      nodes.map((node) => ({ x: node.getBoundingClientRect().x, y: node.getBoundingClientRect().y }))
    );
    assert.equal(desktopColumns.length, 2);
    assert.ok(desktopColumns[1].x > desktopColumns[0].x + 100,
      'Desktop membership form and guidance must form two columns under strict CSP');
    assert.equal(await page.locator('.next-step').isHidden(), true, 'Fallback replaced after React mount');
    assert.equal(await page.locator('.today-work').isHidden(), true, 'Duplicate today panels are removed only after Mantine mount');
    assert.equal(await page.locator('.bm-task-worklist a[href="/beschluss/eins/"]').count(), 1);
    assert.equal(await page.getByText('Ausbau des Schulwegs').first().isVisible(), true);
    assert.equal(await page.locator('.bm-task-worklist').getByText('Überfällig').count(), 1);
    assert.equal(await page.locator('#membership-fallback').isHidden(), true);
    assert.equal(await page.locator('#invitation-fallback').isHidden(), true);
    assert.equal(await page.locator('[data-fa-icon="home"] svg').count(), 1, 'Local Font Awesome SVG mounted');
    assert.equal(await page.getByText('Vorlage erarbeiten').first().isVisible(), true);
    const dashboardSvg = await page.locator('.bm-section-label svg').evaluate((node) => {
      const box = node.getBoundingClientRect();
      return { width: box.width, height: box.height };
    });
    assert.ok(dashboardSvg.width <= 22 && dashboardSvg.height <= 22,
      'Bundled Font Awesome icons must remain inline-sized: ' + JSON.stringify(dashboardSvg));
    const primaryColor = await page.locator('.bm-feature-actions a.mantine-Button-root').evaluate(
      (node) => getComputedStyle(node).color
    );
    assert.equal(primaryColor, 'rgb(255, 255, 255)', 'Primary action must have readable foreground');
    await page.screenshot({ path: 'mantine-ui-desktop.png', fullPage: true });

    let rolePosted = null;
    await page.route('**/submit-role/', async (route) => {
      rolePosted = new URLSearchParams(route.request().postData());
      await route.fulfill({ status: 200, contentType: 'text/html', body: '<p>Server response fixture</p>' });
    });
    await page.locator('#mantine-membership [name="reason"]').fill('Fachliche Zuständigkeit geprüft');
    await page.locator('#mantine-membership [name="role"]').selectOption('reviewer');
    await page.locator('#mantine-membership button[type="submit"]').click();
    await page.waitForURL('**/submit-role/');
    assert.equal(rolePosted.get('csrfmiddlewaretoken'), 'fixture-csrf-token');
    assert.equal(rolePosted.get('version'), '5', 'Optimistic concurrency token preserved');
    assert.equal(rolePosted.get('role'), 'reviewer');
    assert.equal(rolePosted.get('reason'), 'Fachliche Zuständigkeit geprüft');

    const invite = await context.newPage();
    const inviteErrors = [];
    invite.on('pageerror', (err) => inviteErrors.push(err.message));
    await invite.goto(base, { waitUntil: 'networkidle' });
    await invite.getByTestId('bm-mantine-invitation').waitFor();
    let invitePosted = null;
    await invite.route('**/submit-invite/', async (route) => {
      invitePosted = new URLSearchParams(route.request().postData());
      await route.fulfill({ status: 200, contentType: 'text/html', body: '<p>Invitation server response</p>' });
    });
    await invite.locator('#mantine-invitation [name="email"]').fill('person@example.invalid');
    await invite.locator('#mantine-invitation button[type="submit"]').click();
    await invite.waitForURL('**/submit-invite/');
    assert.equal(invitePosted.get('csrfmiddlewaretoken'), 'invite-fixture-csrf');
    assert.equal(invitePosted.get('email'), 'person@example.invalid');
    assert.equal(invitePosted.get('role'), 'reviewer');

    const narrow = await context.newPage();
    await narrow.setViewportSize({ width: 360, height: 780 });
    narrow.on('pageerror', (err) => errors.push(err.message));
    await narrow.goto(base, { waitUntil: 'networkidle' });
    await narrow.getByTestId('bm-mantine-membership').waitFor();
    const fit = await narrow.evaluate(() => ({
      documentWidth: document.documentElement.scrollWidth,
      viewportWidth: window.innerWidth,
    }));
    assert.ok(fit.documentWidth <= fit.viewportWidth + 1, '360px layout must not overflow: ' + JSON.stringify(fit));
    const mobileColumns = await narrow.locator('.bm-membership-grid > div').evaluateAll((nodes) =>
      nodes.map((node) => ({ x: node.getBoundingClientRect().x, y: node.getBoundingClientRect().y }))
    );
    assert.ok(Math.abs(mobileColumns[0].x - mobileColumns[1].x) <= 2,
      'Membership form and guidance must stack at 360px with production CSP');
    await narrow.screenshot({ path: 'mantine-ui-mobile-360.png', fullPage: true });

    const noJs = await browser.newContext({ javaScriptEnabled: false });
    const plain = await noJs.newPage();
    await plain.goto(base);
    assert.equal(await plain.locator('.next-step').isVisible(), true, 'Dashboard remains usable without JS');
    assert.equal(await plain.locator('.today-work').isVisible(), true, 'Original task links remain accessible without JavaScript');
    assert.equal(await plain.locator('#membership-fallback form [name="version"]').count(), 1);
    assert.equal(await plain.locator('#invitation-fallback form [name="email"]').count(), 1);
    assert.equal(await plain.locator('#membership-fallback').isVisible(), true);
    assert.deepEqual(errors.concat(inviteErrors), [], 'No uncaught JS errors');
    console.log('Mantine browser: real islands, local icons, CSRF/version POST, no-JS fallback and 360px layout verified.');
  } finally {
    if (browser) await browser.close();
    server.kill();
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
