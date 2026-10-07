(() => {
 'use strict';
 const $=id=>document.getElementById(id),store=OfflineStore;
 let data=null,password=null,recordId=null,identity=null,busy=false,persistChain=Promise.resolve();
 const say=(message,error=false)=>{$('status').textContent=message;$('status').classList.toggle('notice',error);};
 let saveTimer;
 const scheduleSave=()=>{clearTimeout(saveTimer);saveTimer=setTimeout(()=>persist().catch(()=>say('Lokales Speichern fehlgeschlagen. Texte exportieren.',true)),600);};
 const key=d=>`${d.user_id}.${d.context_id}.${d.meeting_id}`;
 const action=fn=>async event=>{if(event)event.preventDefault();if(busy)return;busy=true;try{await fn(event);}catch(e){say(e.message||'Vorgang fehlgeschlagen. Lokale Daten bleiben erhalten.',true);}finally{busy=false;}};
 const text=(tag,value)=>{const e=document.createElement(tag);e.textContent=value;return e;};
 function localLock(){data=null;password=null;recordId=null;$('password').value='';$('workspace').hidden=true;$('workspace').querySelectorAll('textarea,input').forEach(e=>{e.value='';});$('position').value='1';$('personal-note').value='';$('item-note').value='';$('title').textContent='';$('context').textContent='';$('queue').replaceChildren();$('material').replaceChildren();$('people').replaceChildren();say('Lokale Ansicht gesperrt. Zum Öffnen erneut Offline-Passwort eingeben.');}
 function requireData(){if(!data)throw Error('Zuerst eine vorbereitete Fassung entsperren.');if(Date.parse(data.expires_at)<=Date.now())throw Error('Offline-Freigabe abgelaufen. Texte zur fachlichen Prüfung exportieren, Sitzung erneut online vorbereiten.');}
 async function persist(){if(!data||!password)return;const snapshot=structuredClone(data),secret=password,id=recordId;persistChain=persistChain.catch(()=>{}).then(async()=>store.put(await store.seal(snapshot,secret,id)));return persistChain;}
 async function list(){const rows=await store.list();$('local').replaceChildren();for(const row of rows){const option=text('option',`Offline-Fassung · verfügbar bis ${new Date(row.expires_at).toLocaleString('de-DE')}`);option.value=row.id;$('local').append(option);}if(recordId)$('local').value=recordId;}
 async function online(){
  const r=await fetch('/offline/identitaet/',{cache:'no-store',credentials:'same-origin'});
  if(!r.ok||!r.headers.get('Content-Type')?.includes('application/json'))throw Error('Online anmelden und den passenden Arbeitskontext wählen; lokale Daten bleiben erhalten.');
  const current=await r.json();
  if(data&&(current.user_id!==data.user_id||current.context_id!==data.context_id))throw Error('Anderes Konto oder anderer Arbeitskontext aktiv. Vor Abgleich den ursprünglichen Kontext wählen.');
  identity=current;return current;
 }
 async function send(url,payload,form=false){const current=await online();const r=await fetch(url,{method:'POST',credentials:'same-origin',cache:'no-store',headers:{'X-CSRFToken':current.csrf,...(!form?{'Content-Type':'application/json'}:{})},body:form?payload:JSON.stringify(payload)});
  if(!r.headers.get('Content-Type')?.includes('application/json'))throw Error('Anmeldung oder Rechteprüfung fehlgeschlagen. Lokale Daten bleiben erhalten.');
  const result=await r.json();if(!r.ok)throw Error(result.error||'Aktuelle Rechte oder Sitzungshoheit geändert. Lokal exportieren und fachlich prüfen.');return result;
 }
 function selected(){const item=data?.meeting.items.find(i=>i.id===$('item').value);if(!item)throw Error('TOP auswählen.');return item;}
 function showItem(){if(!data)return;const item=data.meeting.items.find(i=>i.id===$('item').value);$('material').replaceChildren();if(!item)return;
  $('material').append(text('h3',`${item.position} · ${item.title}`));$('material').append(text('pre',item.markdown||''));
  if(item.template){$('material').append(text('h4',`${item.template.number} · ${item.template.subject}`));$('material').append(text('pre',item.template.markdown||''));}
  $('item-note').value=data.drafts?.[item.id]??data.notes[item.id]??'';
 }
 function render(){
  $('workspace').hidden=false;$('title').textContent=data.meeting.title;$('context').textContent=data.label;
  const expired=Date.parse(data.expires_at)<=Date.now(),writer=data.writer&&!expired;
  $('state').textContent=`Vorbereitet ${new Date(data.prepared_at).toLocaleString('de-DE')} · Zentralstand ${data.version} · ${expired?'abgelaufen':`bis ${new Date(data.expires_at).toLocaleString('de-DE')}`} · ${data.queue.length} lokale Ereignisse`;
  $('offline-body').hidden=expired;$('sync-note').disabled=expired;
  $('writer-controls').hidden=!writer;$('readonly').hidden=writer;$('sync').hidden=!writer;$('packet').hidden=!data.packet||expired;
  $('personal-note').value=data.personal_note.markdown;
  const previous=$('item').value;$('item').replaceChildren();for(const item of data.meeting.items){const option=text('option',`${item.position} · ${item.title}`);option.value=item.id;$('item').append(option);}if(data.meeting.items.some(i=>i.id===previous))$('item').value=previous;
  $('people').replaceChildren();$('conflict-person').replaceChildren();
  for(const p of data.roster){const row=document.createElement('div');row.append(text('p',`${p.name} · ${p.present?'lokal anwesend':'lokal abwesend'}`));if(writer){const button=text('button',p.present?'Austritt lokal erfassen':'Eintritt lokal erfassen');button.type='button';button.addEventListener('click',action(async()=>{await queue('presence',{participant_id:p.id,present:!p.present});}));row.append(button);}$('people').append(row);const option=text('option',p.name);option.value=p.id;$('conflict-person').append(option);}
  $('queue').replaceChildren();for(const e of data.queue)$('queue').append(text('pre',`${new Date(e.occurred_at).toLocaleString('de-DE')} · ${e.kind}\n${JSON.stringify(e.payload,null,2)}`));showItem();
 }
 async function queue(kind,payload){
  requireData();if(!data.writer)throw Error('Nur vorbereitete Schriftführung erfasst Sitzungsereignisse.');if(data.pendingBatch)throw Error('Ein übermittelter Stapel wartet auf Rückmeldung. Unverändert erneut abgleichen oder exportieren.');if(data.queue.length>=500)throw Error('500 lokale Ereignisse erreicht. Erst abgleichen.');
  const next={id:crypto.randomUUID(),kind,payload,occurred_at:new Date().toISOString()};
  if(new TextEncoder().encode(JSON.stringify([...data.queue,next])).length>1800000)throw Error('Lokaler Stapel erreicht die Übertragungsgrenze. Vor weiteren Ereignissen abgleichen oder zur Prüfung exportieren.');
  data.queue.push(next);
  if(kind==='presence'){const p=data.roster.find(p=>p.id===payload.participant_id);p.present=payload.present;}
  if(kind==='text'){data.notes[payload.item_id]=payload.markdown;if(data.drafts)delete data.drafts[payload.item_id];}
  await persist();render();say('Lokal verschlüsselt gespeichert. Noch nicht zentral übernommen.');
 }
 $('prepare').addEventListener('submit',action(async()=>{
  const chosenPassword=$('password').value;if(chosenPassword.length<12)throw Error('Offline-Passwort benötigt mindestens zwölf Zeichen.');
  if(data?.queue.length||data?.pendingBatch||data?.noteDirty||Object.values(data?.drafts??{}).some(text=>text.trim()))throw Error('Lokale Änderungen zuerst abgleichen oder exportieren. Eine neue Vorbereitung würde sie ersetzen.');
  await online();const form=new FormData();form.set('hours',$('hours').value);const prepared=await send(`/offline/sitzungen/${$('meeting').value}/`,form,true);const id=key(prepared);
  if(await store.get(id)&&!confirm('Vorhandene lokale Fassung dieser Sitzung ersetzen? Vorher alle lokalen Änderungen abgleichen oder exportieren.'))return;
  if($('with-packet').checked&&prepared.packet_url){const r=await fetch(prepared.packet_url,{credentials:'same-origin',cache:'no-store'});if(!r.ok||!r.headers.get('Content-Type')?.includes('application/pdf'))throw Error('PDF-Mappe nicht freigegeben oder noch nicht verfügbar.');const bytes=new Uint8Array(await r.arrayBuffer());if(bytes.length>20*1024*1024)throw Error('PDF-Mappe überschreitet 20 MB. Ohne PDF erneut vorbereiten.');let value='';for(let i=0;i<bytes.length;i+=32768)value+=String.fromCharCode(...bytes.subarray(i,i+32768));prepared.packet=btoa(value);}
  prepared.noteDirty=false;await store.put(await store.seal(prepared,chosenPassword,id));data=prepared;password=chosenPassword;recordId=id;await list();render();$('password').value='';say('Online geprüft und lokal verschlüsselt vorbereitet. Offline-Passwort bleibt nur im Arbeitsspeicher.');
 }));
 $('unlock').addEventListener('click',action(async()=>{const id=$('local').value,p=$('password').value;localLock();const record=await store.get(id);if(!record)throw Error('Keine lokale Fassung gewählt.');try{data=await store.open(record,p);}catch{throw Error('Offline-Passwort falsch oder lokale Fassung beschädigt.');}password=p;recordId=id;render();if(Date.parse(data.expires_at)<=Date.now())say('Freigabe abgelaufen. Nur Export zur fachlichen Prüfung und lokale Löschung verfügbar.',true);else say('Vorbereitete lokale Fassung entsperrt. Sie sehen keinen aktuellen Zentralstand.');}));
 $('lock').addEventListener('click',action(async()=>{await persist();localLock();}));
 $('delete').addEventListener('click',action(async()=>{const id=$('local').value;if(!id)return;if(!confirm('Diese Offline-Fassung einschließlich nicht abgeglichener Notizen und Ereignisse endgültig lokal löschen?'))return;await store.remove(id);if(id===recordId)localLock();await list();say('Lokale Fassung gelöscht. Zentraldaten wurden nicht geändert.');}));
 $('delete-all').addEventListener('click',action(async()=>{if(!confirm('Alle lokalen Offline-Fassungen und nicht abgeglichenen Texte dieses Browsers endgültig löschen?'))return;await store.clear();localLock();await list();say('Alle lokalen Fassungen gelöscht.');}));
 $('item').addEventListener('change',showItem);
 $('item-note').addEventListener('input',()=>{if(!data)return;data.drafts??={};data.drafts[$('item').value]=$('item-note').value;scheduleSave();});
 $('personal-note').addEventListener('input',()=>{if(!data)return;data.personal_note.markdown=$('personal-note').value;data.noteDirty=true;scheduleSave();});
 $('save-personal').addEventListener('click',action(async()=>{requireData();await persist();say('Persönliche Notiz lokal verschlüsselt gespeichert.');}));
 $('text').addEventListener('submit',action(()=>queue('text',{item_id:selected().id,markdown:$('item-note').value})));
 $('call-item').addEventListener('click',action(()=>queue('top',{item_id:selected().id})));
 $('flow').addEventListener('submit',action(event=>queue(event.submitter.value,{})));
 $('motion').addEventListener('submit',action(()=>queue('motion',{item_id:selected().id,applicant:$('applicant').value,wording:$('wording').value,kind:$('motion-kind').value,position:Number($('position').value)})));
 $('quorum').addEventListener('submit',action(()=>queue('quorum',{item_id:selected().id,confirmed:$('confirmed').value==='true',reason:$('quorum-reason').value})));
 $('conflict').addEventListener('submit',action(()=>queue('conflict',{item_id:selected().id,participant_id:$('conflict-person').value,active:$('conflict-active').value==='true',reason:$('conflict-reason').value})));
 $('sync-note').addEventListener('click',action(async()=>{requireData();await persist();const result=await send(`/offline/notizen/${data.meeting_id}/`,{user_id:data.user_id,context_id:data.context_id,version:data.personal_note.version,markdown:data.personal_note.markdown});data.personal_note.version=result.version;data.noteDirty=false;await persist();say('Persönliche Notiz zentral gespeichert.');}));
 $('sync').addEventListener('click',action(async()=>{
  requireData();if(!data.queue.length)throw Error('Keine lokalen Ereignisse zum Abgleich.');if(!confirm('Den aufgeführten lokalen Ereignisverlauf jetzt nach aktueller Rechteprüfung verbindlich zentral übernehmen?'))return;
  data.pendingBatch??={batch_id:crypto.randomUUID(),meeting_id:data.meeting_id,user_id:data.user_id,context_id:data.context_id,base_version:data.version,epoch:data.epoch,device:data.device,expires_at:data.expires_at,grant:data.grant,events:structuredClone(data.queue)};await persist();
  const result=await send('/offline/abgleich/',data.pendingBatch);data.queue=[];data.pendingBatch=null;data.version=result.version;data.writer=false;await persist();render();say('Sitzungsverlauf zentral übernommen. Für weitere Offline-Schriftführung ausdrücklich neu vorbereiten.');
 }));
 function download(bytes,name,type){const url=URL.createObjectURL(new Blob([bytes],{type})),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),30000);}
 $('packet').addEventListener('click',action(async()=>{requireData();download(Uint8Array.from(atob(data.packet),c=>c.charCodeAt(0)),`sitzungsmappe-${data.meeting_id}.pdf`,'application/pdf');}));
 $('export').addEventListener('click',action(async()=>{if(!data)throw Error('Fassung zuerst mit Ihrem Offline-Passwort entsperren.');await persist().catch(()=>{});const copy=structuredClone(data);delete copy.packet;delete copy.grant;if(copy.pendingBatch)delete copy.pendingBatch.grant;download(JSON.stringify(copy,null,2),`lokaler-verlauf-${data.meeting_id}.json`,'application/json');say('Lokaler Export erstellt. Vertrauliche Datei sicher aufbewahren.');}));
 if('BroadcastChannel' in window){const channel=new BroadcastChannel('beschlussmanufaktur-auth');channel.onmessage=e=>{if(e.data==='logout'){persist().finally(localLock);}};}
 document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='hidden'&&data){persist().catch(()=>say('Lokales Speichern fehlgeschlagen. Seite geöffnet lassen und Texte exportieren.',true));}});
 setInterval(()=>{if(data&&Date.parse(data.expires_at)<=Date.now()){$('offline-body').hidden=true;$('sync-note').disabled=true;$('writer-controls').hidden=true;$('sync').hidden=true;$('packet').hidden=true;}},30000);
 action(async()=>{
  if(!window.isSecureContext||!crypto.subtle)throw Error('Offline benötigt HTTPS und einen aktuellen Browser. Lokale Caddy-CA auf diesem Gerät ausdrücklich vertrauen.');
  if('serviceWorker' in navigator){await navigator.serviceWorker.register('/static/offline-sw.js',{scope:'/static/'});await navigator.serviceWorker.ready;}
  await list();try{const current=await online();const r=await fetch('/offline/sitzungen/',{credentials:'same-origin',cache:'no-store'});if(r.ok){const rows=await r.json();$('meeting').replaceChildren();for(const item of rows.meetings){const option=text('option',item.title);option.value=item.id;$('meeting').append(option);}const chosen=new URL(location.href).searchParams.get('meeting');if(chosen)$('meeting').value=chosen;}say(`Online · ${current.label}. Eine Sitzung vorbereiten oder eine lokale Fassung entsperren.`);}catch{say('Offline oder nicht angemeldet. Bereits vorbereitete Fassung mit Offline-Passwort entsperren.');}
 })();
})();
