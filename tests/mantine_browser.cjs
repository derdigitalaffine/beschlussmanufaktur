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
    assert.equal(await page.locator('.next-step').isHidden(), true, 'Fallback replaced after React mount');
    assert.equal(await page.locator('#membership-fallback').isHidden(), true);
    assert.equal(await page.locator('#invitation-fallback').isHidden(), true);
    assert.equal(await page.locator('[data-fa-icon="home"] svg').count(), 1, 'Local Font Awesome SVG mounted');
    assert.equal(await page.getByText('Vorlage erarbeiten').first().isVisible(), true);

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

    const noJs = await browser.newContext({ javaScriptEnabled: false });
    const plain = await noJs.newPage();
    await plain.goto(base);
    assert.equal(await plain.locator('.next-step').isVisible(), true, 'Dashboard remains usable without JS');
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
