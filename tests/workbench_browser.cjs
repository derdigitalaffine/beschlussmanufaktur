/* Browser validation of the global Mantine workspace and public CSS boundary.
 * Fixture is representative rather than a claim of production E2E login. */
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const { spawn } = require('node:child_process');

const server = spawn('python3', ['-m', 'http.server', '8799', '--bind', '127.0.0.1', '--directory', '.'],
  { stdio: 'ignore' });
const base = 'http://127.0.0.1:8799';
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function ensureServer() {
  for (let i = 0; i < 45; i += 1) {
    try {
      if ((await fetch(`${base}/tests/fixtures/workbench.html`)).ok) return;
    } catch { /* server starting */ }
    await sleep(100);
  }
  throw Error('Workbench fixture HTTP server did not start');
}
async function noHorizontalOverflow(page, name) {
  const size = await page.evaluate(() => ({
    actual: document.documentElement.scrollWidth, allowed: window.innerWidth,
  }));
  assert.ok(size.actual <= size.allowed + 2,
    `${name} must fit viewport, got ${JSON.stringify(size)}`);
}

(async () => {
  let browser;
  try {
    await ensureServer();
    browser = await chromium.launch();
    const context = await browser.newContext({ viewport: { width: 1366, height: 900 } });
    const page = await context.newPage();
    const pageErrors = [];
    page.on('pageerror', (error) => pageErrors.push(error.message));
    await page.goto(`${base}/tests/fixtures/workbench.html`, { waitUntil: 'networkidle' });
    await page.getByTestId('bm-workbench').waitFor();

    assert.equal(await page.locator('.bm-workbench-breadcrumbs').getByText('Vorlagen').count(), 1);
    assert.equal(await page.locator('.bm-workbench-index a[href^="#"]').count(), 5,
      'In-page navigation has links to all real workflow sections');
    assert.equal(await page.getByRole('heading', { name: 'Schulwegsicherung im Ortsbeirat' }).count(), 1,
      'Mantine ribbon never duplicates native page title');
    assert.equal(await page.locator('form[action="/save-step/"] input[name="csrfmiddlewaretoken"]').count(), 1);
    assert.equal(await page.locator('form[action="/save-step/"] input[name="version"]').inputValue(), '13');
    assert.equal(await page.locator('.bm-workbench-actions a[href="/vorlagen/bearbeiten/"]').count(), 1);
    assert.equal(await page.locator('link[href$="/ux-workbench.css"]').count(), 1);
    assert.equal(await page.locator('link[href$="/workspace.css"]').count(), 1);
    await page.locator('.bm-index-link', { hasText: 'Anlagen' }).click();
    assert.equal(new URL(page.url()).hash, '#bm-section-3');

    await page.getByRole('button', { name: 'Alle für mich verfügbaren Bereiche öffnen' }).click();
    await page.getByText('Bereiche und Aufgaben').waitFor();
    assert.equal(await page.locator('.bm-area-drawer a[href="/vorlagen/"]').count(), 1);
    assert.equal(await page.locator('.bm-area-drawer a[href="/sitzungen/"]').count(), 1);
    assert.equal(await page.locator('.bm-area-drawer a[href="/verwaltung/"]').count(), 0,
      'Workbench must not expose routes outside server-provided global navigation');
    await page.keyboard.press('Escape');
    await page.screenshot({ path: 'workbench-desktop.png', fullPage: true });

    let posted;
    await page.route('**/save-step/', async (route) => {
      posted = new URLSearchParams(route.request().postData());
      await route.fulfill({ status: 200, contentType: 'text/html', body: '<h1>Vom Server bestätigt</h1>' });
    });
    await page.locator('form[action="/save-step/"] textarea').fill('Begründeter Prüfschritt');
    await page.locator('form[action="/save-step/"] button').click();
    await page.waitForURL('**/save-step/');
    assert.equal(posted.get('csrfmiddlewaretoken'), 'test-csrf');
    assert.equal(posted.get('version'), '13');
    assert.equal(posted.get('note'), 'Begründeter Prüfschritt');

    const narrow = await context.newPage();
    await narrow.setViewportSize({ width: 360, height: 800 });
    narrow.on('pageerror', (error) => pageErrors.push(error.message));
    await narrow.goto(`${base}/tests/fixtures/workbench.html`, { waitUntil: 'networkidle' });
    await narrow.getByTestId('bm-workbench').waitFor();
    await noHorizontalOverflow(narrow, 'Protected workbench 360px');
    assert.equal(await narrow.getByRole('heading', { name: 'Schulwegsicherung im Ortsbeirat' }).isVisible(), true);
    await narrow.screenshot({ path: 'workbench-mobile-360.png', fullPage: true });

    const zoom = await context.newPage();
    await zoom.setViewportSize({ width: 860, height: 900 });
    await zoom.goto(`${base}/tests/fixtures/workbench.html`, { waitUntil: 'networkidle' });
    await zoom.addStyleTag({ url: `${base}/tests/fixtures/workbench-zoom.css` });
    await noHorizontalOverflow(zoom, 'Protected workbench at 200% root font');
    assert.equal(await zoom.getByRole('heading', { name: 'Schulwegsicherung im Ortsbeirat' }).isVisible(), true);

    const noJs = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 360, height: 800 } });
    const plain = await noJs.newPage();
    await plain.goto(`${base}/tests/fixtures/workbench.html`);
    assert.equal(await plain.locator('#bm-workbench-root').isHidden(), true);
    assert.equal(await plain.locator('form[action="/save-step/"] button').isVisible(), true);
    assert.equal(await plain.locator('.ui-panel h2').count(), 5);
    await noHorizontalOverflow(plain, 'No-JS protected layout 360px');

    const publicPage = await noJs.newPage();
    await publicPage.goto(`${base}/tests/fixtures/public_workbench.html`);
    assert.equal(await publicPage.getByRole('heading', { name: 'Entscheidungen nachvollziehen.' }).isVisible(), true);
    assert.equal(await publicPage.locator('.bm-workbench').count(), 0);
    assert.equal(await publicPage.locator('script[src*="workbench.js"]').count(), 0);
    assert.equal(await publicPage.locator('form[method="get"] [name="organisation"]').count(), 1);
    await noHorizontalOverflow(publicPage, 'Public search 360px');
    await publicPage.screenshot({ path: 'workbench-public-360.png', fullPage: true });
    assert.deepEqual(pageErrors, [], 'No uncaught browser errors');
    console.log('Workbench browser: Mantine navigation, authorized links, CSRF/version POST, 360px/200% font, no-JS and public boundary passed.');
  } finally {
    if (browser) await browser.close();
    server.kill();
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
