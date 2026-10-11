const assert=require('node:assert/strict');
const {chromium}=require('playwright');
const {spawn}=require('node:child_process');
const server=spawn('python3',['-m','http.server','8768','--bind','127.0.0.1','--directory','prototypes/live-flow-68'],{stdio:'ignore'});
const wait=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function ready(){for(let i=0;i<30;i++){try{if((await fetch('http://127.0.0.1:8768/progressive.html')).ok)return;}catch{}await wait(100);}throw Error('prototype server did not start');}
async function exercise(page,url,s){
  await page.goto(url);await page.setViewportSize({width:1280,height:820});
  assert.equal(await page.locator('[aria-label="Live-Status"] .status-cell').count(),5);
  assert((await page.locator(s.connection).textContent()).includes('Online'));

  // Kritischster Fall: Request gesendet, Verbindung fällt vor der Bestätigung aus.
  await page.click(s.primary);assert.equal(await page.locator(s.primary).isDisabled(),true);await wait(40);await page.click(s.offline);await page.waitForFunction(sel=>document.querySelector(sel).textContent.includes('unklar'),s.vote);assert.equal(await page.locator(s.primary).isDisabled(),true);assert.equal(await page.evaluate(sel=>document.activeElement===document.querySelector(sel),s.recover),true);
  await page.click(s.recover);assert((await page.locator(s.vote).textContent()).includes('Offen'));assert((await page.locator(s.vote).textContent()).includes('18 / 18'));assert.equal(await page.locator(s.primary).isDisabled(),false);

  // Stale-Version ohne Netzverlust blockiert ebenfalls, bis der Serverstand übernommen ist.
  await page.click(s.stale);assert.equal(await page.locator(s.primary).isDisabled(),true);assert.equal(await page.evaluate(sel=>document.activeElement===document.querySelector(sel),s.recover),true);await page.click(s.recover);assert.equal(await page.locator(s.primary).isDisabled(),false);

  // Verlust der Sitzungshoheit darf keine lokale Weiterarbeit erlauben.
  await page.click(s.authorityLoss);assert.equal(await page.locator(s.primary).isDisabled(),true);assert.equal(await page.evaluate(sel=>document.activeElement===document.querySelector(sel),s.recover),true);await page.click(s.recover);assert.equal(await page.locator(s.primary).isDisabled(),false);

  await page.click(s.primary);assert.equal(await page.locator(s.primary).isDisabled(),true);await page.waitForFunction(sel=>document.querySelector(sel).textContent.includes('Abgeschlossen'),s.vote);assert.equal(await page.locator(s.primary).isDisabled(),true);assert.equal(await page.locator(s.result).isVisible(),true);

  await page.setViewportSize({width:768,height:1024});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=document.documentElement.clientWidth),true);
}
(async()=>{let browser;try{await ready();browser=await chromium.launch();const page=await browser.newPage();
  await exercise(page,'http://127.0.0.1:8768/progressive.html',{connection:'#connection-value',vote:'#vote-value',primary:'#primary-action',stale:'#simulate-stale',offline:'#simulate-offline',authorityLoss:'#simulate-authority-loss',recover:'#recover',result:'#vote-result'});
  await exercise(page,'http://127.0.0.1:8768/island.html',{connection:'live-meeting-island [data-role=connection-value]',vote:'live-meeting-island [data-role=vote-value]',primary:'live-meeting-island [data-action=primary]',stale:'live-meeting-island [data-action=stale]',offline:'live-meeting-island [data-action=offline]',authorityLoss:'live-meeting-island [data-action=authority-loss]',recover:'live-meeting-island [data-action=recover]',result:'live-meeting-island [data-role=vote-result]'});
  console.log('Prototype #68: unknown-outcome recovery, stale/authority lock, confirmed vote result and tablet reflow pass for both variants.');
}finally{if(browser)await browser.close();server.kill();}})().catch(error=>{console.error(error);process.exitCode=1;});
