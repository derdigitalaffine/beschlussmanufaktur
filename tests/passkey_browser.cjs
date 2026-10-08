const assert=require('node:assert/strict');
const {chromium}=require('playwright');
const {spawn}=require('node:child_process');
const server=spawn(process.env.TEST_PYTHON||'python',['tests/passkey_fixture.py'],{stdio:['ignore','pipe','pipe']});
let logs='';server.stderr.on('data',d=>{logs+=d;});
(async()=>{
 let browser;
 try {
  await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(new Error('Fixture startup: '+logs)),20000);server.stdout.on('data',d=>{if(String(d).includes('READY')){clearTimeout(timer);resolve();}});server.on('exit',code=>reject(new Error('Fixture exit '+code+': '+logs)));});
  browser=await chromium.launch();const context=await browser.newContext();const page=await context.newPage();
  const cdp=await context.newCDPSession(page);await cdp.send('WebAuthn.enable');await cdp.send('WebAuthn.addVirtualAuthenticator',{options:{protocol:'ctap2',transport:'internal',hasResidentKey:true,hasUserVerification:true,isUserVerified:true,automaticPresenceSimulation:true}});
  await page.goto('http://localhost:8766/anmelden/');await page.locator('[name=email]').fill('browser@example.invalid');await page.locator('[name=password]').fill('Browser-test-password-2026');await page.locator('button[type=submit]').click();
  const {code}=await (await context.request.get('http://localhost:8766/fixture-code/')).json();await page.locator('[name=code]').fill(code);await page.locator('button[type=submit]').click();await page.waitForURL('http://localhost:8766/');
  await page.goto('http://localhost:8766/sicherheit/passkeys/');await page.locator('[name=password]').fill('Browser-test-password-2026');await page.locator('[data-passkey=register]').click();await page.waitForFunction(()=>document.getElementById('passkey-recovery').textContent.length>100,{},{timeout:15000});
  assert.equal((await page.locator('#passkey-recovery').textContent()).trim().split('\n').length,10);
  await page.locator('form[action="/abmelden/"] button').click();await page.waitForURL('**/anmelden/');await page.locator('[data-passkey=login]').click();await page.waitForURL('http://localhost:8766/',{timeout:15000});
  await page.goto('http://localhost:8766/sicherheit/passkeys/');assert.equal(await page.locator('[data-passkey-remove]').count(),1);
  console.log('Real WebAuthn registration and passwordless authentication passed with UV and resident key.');
 } finally {if(browser) await browser.close();server.kill();}
})().catch(error=>{console.error(error,logs);process.exitCode=1;});
