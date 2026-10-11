'use strict';
let serverVersion=7;
const pageVersion=document.querySelector('#page-version');
const statusLine=document.querySelector('#status');
const approveForm=document.querySelector('#approve-form');
const returnForm=document.querySelector('#return-form');
const dialog=document.querySelector('#return-dialog');
const staleButton=document.querySelector('#simulate-stale');
const refreshButton=document.querySelector('#refresh-version');
const badge=document.querySelector('#workflow-badge');
const approvalStep=document.querySelector('#approval-step');
const setStatus=(text,kind='info')=>{statusLine.textContent=text;statusLine.dataset.kind=kind;};
const wait=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function fakeSubmit(form,action){
  const expected=Number(new FormData(form).get('expected_version'));
  setStatus('Wird serverseitig geprüft …');
  for(const button of form.querySelectorAll('button'))button.disabled=true;
  await wait(180);
  for(const button of form.querySelectorAll('button'))button.disabled=false;
  if(expected!==serverVersion){
    setStatus(`Zwischenzeitlich liegt Version ${serverVersion} vor. Vor einer Entscheidung muss der aktuelle Stand geprüft werden.`,'error');
    refreshButton.hidden=false;refreshButton.focus();return false;
  }
  serverVersion+=1;
  pageVersion.textContent=String(serverVersion);
  for(const input of document.querySelectorAll('[name=expected_version]'))input.value=String(serverVersion);
  badge.textContent=action==='approve'?'Freigegeben':'Zurückgegeben';badge.dataset.state=action==='approve'?'approved':'review';
  approvalStep.dataset.state='done';approvalStep.textContent=action==='approve'?'3. Freigabe ✓':'3. Freigabe – zurückgegeben';
  setStatus(action==='approve'?'Freigabe serverseitig bestätigt. Version '+serverVersion+'.':'Rückgabe serverseitig bestätigt. Version '+serverVersion+'.');
  return true;
}
approveForm.addEventListener('submit',async event=>{event.preventDefault();await fakeSubmit(approveForm,'approve');});
document.querySelector('#return-open').addEventListener('click',()=>dialog.showModal());
document.querySelector('#return-cancel').addEventListener('click',()=>dialog.close());
returnForm.addEventListener('submit',async event=>{event.preventDefault();if(await fakeSubmit(returnForm,'return'))dialog.close();});
staleButton.addEventListener('click',()=>{serverVersion+=1;setStatus(`Testzustand: Server ist jetzt auf Version ${serverVersion}, diese Seite noch auf Version ${pageVersion.textContent}.`);});
refreshButton.addEventListener('click',()=>{pageVersion.textContent=String(serverVersion);for(const input of document.querySelectorAll('[name=expected_version]'))input.value=String(serverVersion);refreshButton.hidden=true;setStatus('Aktueller Serverstand wurde für den Prototyp übernommen. Entscheidung kann erneut geprüft werden.');approveForm.querySelector('button').focus();});
