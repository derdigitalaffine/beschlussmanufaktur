const assert=require('node:assert/strict');
const {chromium}=require('playwright');
const {spawn}=require('node:child_process');
const server=spawn('python3',['-m','http.server','8769','--bind','127.0.0.1','--directory','prototypes/template-flow-69'],{stdio:'ignore'});
const wait=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function ready(){for(let i=0;i<30;i++){try{if((await fetch('http://127.0.0.1:8769/progressive.html')).ok)return;}catch{}await wait(100);}throw Error('prototype server did not start');}
async function exercise(page,url,selectors){
  await page.goto(url);await page.setViewportSize({width:1280,height:800});
  assert.equal(await page.locator('h1').textContent(),'Neubau der Grundschule Nord');
  assert((await page.locator('[aria-label="Bearbeitungsstand"]').textContent()).includes('Freigabe'));
  await page.click(selectors.stale);await page.click(selectors.approve);
  await page.waitForFunction(sel=>document.querySelector(sel).textContent.includes('Zwischenzeitlich'),selectors.status);
  assert.equal(await page.evaluate(sel=>document.activeElement===document.querySelector(sel),selectors.refresh),true);
  await page.click(selectors.refresh);await page.click(selectors.approve);
  await page.waitForFunction(sel=>document.querySelector(sel).textContent.includes('serverseitig bestätigt'),selectors.status);
  assert.equal(await page.locator(selectors.approve).isDisabled(),true);
  assert.equal(await page.locator(selectors.returnOpen).isDisabled(),true);
  await page.setViewportSize({width:360,height:780});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=document.documentElement.clientWidth),true);
}
(async()=>{let browser;try{await ready();browser=await chromium.launch();const page=await browser.newPage();
  await exercise(page,'http://127.0.0.1:8769/progressive.html',{stale:'#simulate-stale',approve:'#approve-form button',returnOpen:'#return-open',status:'#status',refresh:'#refresh-version'});
  await exercise(page,'http://127.0.0.1:8769/island.html',{stale:'template-flow-island [data-action=stale]',approve:'template-flow-island [data-action=approve]',returnOpen:'template-flow-island [data-action=return-open]',status:'template-flow-island [data-role=status]',refresh:'template-flow-island [data-action=refresh]'});
  console.log('Prototype #69: stale-state focus, server-confirmed success, duplicate-decision lock and narrow reflow pass for both variants.');
}finally{if(browser)await browser.close();server.kill();}})().catch(error=>{console.error(error);process.exitCode=1;});
