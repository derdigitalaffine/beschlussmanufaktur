'use strict';
let serverVersion=42;
let pageVersion=42;
let connectionState='online';
let authority=true;
let quorum=18;
let voteState='idle';
let serverVoteState='idle';
let ballots=0;
let pending=false;
const pageVersionEl=document.querySelector('#page-version');
const connectionCell=document.querySelector('#connection-cell');
const connectionValue=document.querySelector('#connection-value');
const authorityCell=document.querySelector('#authority-cell');
const authorityValue=document.querySelector('#authority-value');
const quorumCell=document.querySelector('#quorum-cell');
const quorumValue=document.querySelector('#quorum-value');
const voteCell=document.querySelector('#vote-cell');
const voteValue=document.querySelector('#vote-value');
const voteDescription=document.querySelector('#vote-description');
const voteProgress=document.querySelector('#vote-progress');
const ballotsEl=document.querySelector('#ballots');
const ballotCount=document.querySelector('#ballot-count');
const voteResult=document.querySelector('#vote-result');
const statusMessage=document.querySelector('#status-message');
const primary=document.querySelector('#primary-action');
const recover=document.querySelector('#recover');
const saveNote=document.querySelector('#save-note');
const addMotion=document.querySelector('#add-motion');
const wait=ms=>new Promise(resolve=>setTimeout(resolve,ms));
const setMessage=(text,kind='info')=>{statusMessage.textContent=text;statusMessage.dataset.kind=kind;};
function isBlocked(){return pending||connectionState!=='online'||!authority||pageVersion!==serverVersion||['closed','unknown'].includes(voteState);}
function focusRecoverWhenReady(){if(!pending&&!recover.hidden&&!recover.disabled)recover.focus();}
function render(){
  pageVersionEl.textContent=String(pageVersion);
  connectionCell.dataset.kind=connectionState==='online'?'ok':connectionState==='stale'?'warn':'danger';
  connectionValue.textContent=connectionState==='online'?'● Online · bestätigt':connectionState==='stale'?`● Veraltet · Server Stand ${serverVersion}`:'● Offline · keine Bestätigung';
  authorityCell.dataset.kind=authority?'ok':'danger';authorityValue.textContent=authority?'Schriftführung aktiv':'Sitzungshoheit verloren';
  quorumCell.dataset.kind=quorum>=15?'ok':'danger';quorumValue.textContent=`${quorum} / 28 · ${quorum>=15?'festgestellt':'nicht beschlussfähig'}`;
  const voteLabels={idle:'Keine Abstimmung offen','pending-open':'Öffnung wird bestätigt …',open:`Offen · ${ballots} / 18 Stimmen`,'pending-close':'Abschluss wird bestätigt …',unknown:'Ausgang unklar · Server prüfen',closed:'Abgeschlossen · 11 / 6 / 1'};
  voteValue.textContent=voteLabels[voteState];voteCell.dataset.kind=voteState==='open'?'warn':voteState==='closed'?'ok':voteState==='unknown'?'danger':'';
  voteProgress.hidden=!['open','pending-close'].includes(voteState);ballotsEl.value=ballots;ballotCount.textContent=String(ballots);voteResult.hidden=voteState!=='closed';
  voteDescription.textContent=voteState==='idle'?'Noch nicht gestartet. Gegenstand: Beschlussvorschlag inklusive Antrag 1.':voteState==='open'?'Abstimmung ist serverseitig geöffnet. Eingehende Stimmen werden angezeigt.':voteState==='closed'?'Ergebnis serverseitig bestätigt und diesem TOP zugeordnet.':voteState==='unknown'?'Die Aktion kann serverseitig wirksam geworden sein. Nicht wiederholen; zuerst autoritativen Serverstand laden.':'Kritische Aktion wartet auf Serverbestätigung.';
  if(voteState==='idle')primary.textContent='Namentliche Abstimmung starten';else if(voteState==='open')primary.textContent='Abstimmung schließen';else if(voteState==='closed')primary.textContent='Abstimmung abgeschlossen';else if(voteState==='unknown')primary.textContent='Ausgang unklar · nicht wiederholen';else primary.textContent='Serverbestätigung ausstehend …';
  const blocked=isBlocked();primary.disabled=blocked;saveNote.disabled=pending||connectionState!=='online'||!authority||pageVersion!==serverVersion||voteState==='unknown';addMotion.disabled=saveNote.disabled;
  recover.hidden=connectionState==='online'&&authority&&pageVersion===serverVersion&&voteState!=='unknown';recover.disabled=pending;
  recover.textContent=!authority?'Sitzungshoheit und Serverstand prüfen':connectionState==='offline'?'Neu verbinden und Serverstand prüfen':'Autoritativen Serverstand laden';
}
async function confirmVoteTransition(nextPending,nextDone){
  if(isBlocked())return;
  const requestBase=pageVersion;
  pending=true;voteState=nextPending;setMessage('Kritische Aktion gesendet · warte auf Serverbestätigung …');render();
  await wait(180);
  const externalChanged=serverVersion!==requestBase;
  serverVersion+=1;serverVoteState=nextDone;pending=false;
  if(connectionState!=='online'||!authority||externalChanged){
    voteState='unknown';
    if(connectionState==='online'&&authority)connectionState='stale';
    setMessage(`Antwort nicht verlässlich angekommen. Die Aktion kann serverseitig wirksam sein (Server Stand ${serverVersion}). Nicht wiederholen; Serverstand prüfen.`,'error');render();focusRecoverWhenReady();return;
  }
  pageVersion=serverVersion;voteState=nextDone;
  if(nextDone==='open'){
    ballots=0;setMessage(`Abstimmung serverseitig geöffnet · Stand ${serverVersion}.`);render();
    setTimeout(()=>{if(voteState==='open'&&connectionState==='online'&&authority){ballots=18;setMessage('18 von 18 Stimmen serverseitig eingegangen. Abstimmung kann geschlossen werden.');render();}},160);
  }else{ballots=18;setMessage(`Abstimmung serverseitig abgeschlossen · Stand ${serverVersion}. Ergebnis 11 Ja · 6 Nein · 1 Enthaltung.`);render();}
}
primary.addEventListener('click',()=>{if(voteState==='idle')confirmVoteTransition('pending-open','open');else if(voteState==='open')confirmVoteTransition('pending-close','closed');});
document.querySelector('#simulate-stale').addEventListener('click',()=>{if(voteState==='closed')return;serverVersion+=1;connectionState='stale';setMessage(`Der Server ist bereits auf Stand ${serverVersion}. Kritische Aktionen sind gesperrt, bis der gültige Stand übernommen wurde.`,'error');render();focusRecoverWhenReady();});
document.querySelector('#simulate-offline').addEventListener('click',()=>{if(voteState==='closed')return;connectionState='offline';setMessage('Verbindung unterbrochen. Eine laufende Aktion wird nicht lokal als erfolgreich behandelt.','error');render();focusRecoverWhenReady();});
document.querySelector('#simulate-authority-loss').addEventListener('click',()=>{if(voteState==='closed')return;authority=false;serverVersion+=1;setMessage('Sitzungshoheit wurde auf einem anderen Gerät übernommen. Eine laufende Aktion wird nicht wiederholt; autoritativen Stand prüfen.','error');render();focusRecoverWhenReady();});
recover.addEventListener('click',()=>{pageVersion=serverVersion;connectionState='online';authority=true;if(voteState==='unknown'){voteState=serverVoteState;if(voteState==='open'||voteState==='closed')ballots=18;}setMessage(`Autoritativer Serverstand ${serverVersion} wurde übernommen. ${voteState==='open'?'Die Abstimmung ist serverseitig offen.':voteState==='closed'?'Die Abstimmung ist serverseitig abgeschlossen.':'Kritische Aktionen sind wieder möglich.'}`);render();primary.focus();});
document.querySelector('#toggle-quorum').addEventListener('click',()=>{if(pending)return;quorum=quorum===18?13:18;setMessage(quorum>=15?'Beschlussfähigkeit erneut mit 18 / 28 festgestellt.':'Testzustand: nur 13 / 28 anwesend. Abstimmung müsste fachlich neu bewertet werden.',quorum>=15?'info':'error');render();});
saveNote.addEventListener('click',async()=>{if(saveNote.disabled)return;const requestBase=pageVersion;pending=true;setMessage('Protokollstand wird gespeichert …');render();await wait(120);const externalChanged=serverVersion!==requestBase;serverVersion+=1;pending=false;if(connectionState!=='online'||!authority||externalChanged){connectionState=connectionState==='online'?'stale':connectionState;setMessage('Speicherergebnis ist unklar. Nicht erneut senden; autoritativen Serverstand prüfen.','error');render();focusRecoverWhenReady();return;}pageVersion=serverVersion;setMessage(`Protokollstand serverseitig bestätigt · Stand ${serverVersion}.`);render();});
addMotion.addEventListener('click',()=>setMessage('Prototyp: Antragserfassung ist sekundär und verändert den Vote-State in diesem Architekturvergleich nicht.'));
render();
