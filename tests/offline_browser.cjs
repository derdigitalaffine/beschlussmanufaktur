/* Frontend integration against explicit transport fixtures. Backend contract is
   covered separately by core.test_offline on SQLite and PostgreSQL. */
const assert=require('node:assert/strict');
const {chromium}=require('playwright');
const {spawn}=require('node:child_process');
const server=spawn('python3',['-m','http.server','8765','--bind','127.0.0.1','--directory','backend'],{stdio:'ignore'});
const wait=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{
 let browser;
 try {
  for(let i=0;i<30;i++){try{if((await fetch('http://127.0.0.1:8765/static/offline.html')).ok)break;}catch{}await wait(100);}
  browser=await chromium.launch();const context=await browser.newContext();const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>d.accept());
  let changed=false,syncCount=0;
  const id={user_id:'user-a',context_id:'context-a',label:'Gemeinde · Schriftführung',csrf:'test-csrf',email:'clerk@example.org'};
  const prepared={schema:1,...id,meeting_id:'meeting-a',expires_at:new Date(Date.now()+3600000).toISOString(),prepared_at:new Date().toISOString(),version:7,epoch:1,device:'device-a',writer:true,grant:'transport-fixture-only',meeting:{title:'Test-Sitzung',items:[{id:'item-a',position:1,title:'TOP eins',public:true,markdown:'SICHERE VORLAGE <script>window.hacked=true</script>'}]},roster:[{id:'person-a',name:'Person A',present:false,voting:true}],notes:{},personal_note:{markdown:'',version:0},queue:[],packet_url:null};
  await context.route('**/offline/identitaet/',r=>r.fulfill({contentType:'application/json',body:JSON.stringify(changed?{...id,context_id:'context-b'}:id)}));
  await context.route('**/offline/sitzungen/',r=>r.fulfill({contentType:'application/json',body:JSON.stringify({meetings:[{id:'meeting-a',title:'Test-Sitzung'}]})}));
  await context.route('**/offline/sitzungen/meeting-a/',r=>r.fulfill({contentType:'application/json',body:JSON.stringify(prepared)}));
  await context.route('**/offline/abgleich/',r=>{syncCount++;return r.fulfill({status:409,contentType:'application/json',body:JSON.stringify({error:'Zentralstand geändert; lokale Daten bleiben erhalten.'})});});
  await page.goto('http://127.0.0.1:8765/static/offline.html');await page.waitForFunction(()=>document.getElementById('meeting').options.length===1);
  await page.fill('#password','Offline Passphrase ausreichend lang');await page.click('#prepare button');await page.waitForFunction(()=>!document.getElementById('workspace').hidden);
  const records=await page.evaluate(()=>OfflineStore.list());assert.equal(records.length,1);assert(!JSON.stringify(records).includes('SICHERE VORLAGE'));assert(!JSON.stringify(records).includes('Test-Sitzung'));assert.equal(await page.evaluate(()=>window.hacked),undefined);
  await page.fill('#personal-note','MEINE GEHEIME NOTIZ');await page.click('#save-personal');await page.waitForFunction(()=>document.getElementById('status').textContent.includes('Notiz lokal'));
  await page.fill('#item-note','LOKALE PROTOKOLLNOTIZ');await page.click('#text button');await page.waitForFunction(()=>document.getElementById('queue').textContent.includes('LOKALE PROTOKOLLNOTIZ'));
  await context.setOffline(true);await page.reload();await page.waitForFunction(()=>document.getElementById('local').options.length===1);assert(await page.locator('#workspace').isHidden());
  await page.fill('#password','Offline Passphrase ausreichend lang');await page.click('#unlock');await page.waitForFunction(()=>!document.getElementById('workspace').hidden);assert.equal(await page.inputValue('#personal-note'),'MEINE GEHEIME NOTIZ');assert((await page.textContent('#queue')).includes('LOKALE PROTOKOLLNOTIZ'));
  await context.setOffline(false);changed=true;await page.click('#sync');await page.waitForFunction(()=>document.getElementById('status').textContent.includes('Anderes Konto'));assert.equal(syncCount,0);
  changed=false;await page.click('#sync');await page.waitForFunction(()=>document.getElementById('status').textContent.includes('Zentralstand geändert'));assert.equal(syncCount,1);assert((await page.textContent('#queue')).includes('LOKALE PROTOKOLLNOTIZ'));
  await page.click('#lock');await page.waitForFunction(()=>document.getElementById('workspace').hidden);assert.equal(await page.inputValue('#personal-note'),'');
  const keys=await page.evaluate(()=>caches.keys());for(const key of keys){const urls=await page.evaluate(async k=>(await (await caches.open(k)).keys()).map(r=>r.url),key);assert(urls.every(url=>new URL(url).pathname.startsWith('/static/')));}
  assert.deepEqual(errors,[]);console.log('Browser: verschlüsselte Vorbereitung, Offline-Neuladen, Notizen, Kontext- und Versionskonflikt, sichere Textausgabe und reine Shell-Caches erfolgreich.');
 } finally {if(browser)await browser.close();server.kill();}
})().catch(error=>{console.error(error);process.exitCode=1;});
