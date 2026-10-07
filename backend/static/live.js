'use strict';
const heartbeat=document.querySelector('#live-heartbeat');
const connection=document.querySelector('#live-connection');
let originalVersion=null;
async function pulse(){
  try{
    if(heartbeat){const res=await fetch(heartbeat.dataset.url,{method:'POST',headers:{'X-CSRFToken':heartbeat.querySelector('[name=csrfmiddlewaretoken]').value},body:new FormData(heartbeat)});if(!res.ok)throw Error('Schriftführung ist abgelaufen oder übernommen. Neu laden und prüfen.');}
    const res=await fetch(connection.dataset.status);if(!res.ok)throw Error('Arbeitskontext oder Verbindung nicht verfügbar.');const status=await res.json();
    if(originalVersion!==null&&status.version!==originalVersion)connection.textContent='Der Sitzungsstand hat sich geändert. Vor weiterer Bearbeitung neu laden; ungesicherte Texte vorher kopieren.';
    else connection.textContent=heartbeat?'Sitzungshoheit aktiv · Verbindung bestätigt':'Ansicht · Verbindung bestätigt';
    if(originalVersion===null)originalVersion=status.version;
  }catch(error){connection.textContent='Verbindung unterbrochen oder Sitzungshoheit geändert. Ungesicherte Texte erhalten und aktuellen Stand prüfen.';}
}
if(connection){pulse();setInterval(pulse,30000);}
for(const form of document.querySelectorAll('form[method=post]'))form.addEventListener('submit',()=>{const id=form.querySelector('[name=event_id]');if(id&&crypto.randomUUID)id.value=crypto.randomUUID();});
