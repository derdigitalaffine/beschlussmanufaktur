'use strict';
(() => {
  const decode = text => Uint8Array.from(atob(text.replace(/-/g,'+').replace(/_/g,'/')), c => c.charCodeAt(0));
  const encode = value => btoa(String.fromCharCode(...new Uint8Array(value))).replace(/\+/g,'-').replace(/\//g,'_').replace(/=/g,'');
  const status = text => { document.getElementById('passkey-status').textContent = text; };
  const post = async (url, data) => {
    const csrf = document.querySelector('input[name=csrfmiddlewaretoken]').value;
    const response = await fetch(url,{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':csrf},body:JSON.stringify(data)});
    const result = await response.json();if (!response.ok) throw new Error(result.error || 'Sicherheitsprüfung fehlgeschlagen.');return result;
  };
  for (const button of document.querySelectorAll('[data-passkey]')) button.addEventListener('click', async () => {
    button.disabled=true;
    try {
      if (!navigator.credentials || !window.PublicKeyCredential) throw new Error('Dieser Browser unterstützt keine Passkeys.');
      const purpose=button.dataset.passkey;
      const form=document.getElementById('passkey-form');
      const data=form ? Object.fromEntries(new FormData(form)) : {};
      const options=await post('/sicherheit/passkeys/optionen/'+purpose+'/',data);
      options.challenge=decode(options.challenge);
      if (purpose==='register') {options.user.id=decode(options.user.id);options.excludeCredentials=(options.excludeCredentials||[]).map(c=>({...c,id:decode(c.id)}));}
      else options.allowCredentials=(options.allowCredentials||[]).map(c=>({...c,id:decode(c.id)}));
      const credential=purpose==='register' ? await navigator.credentials.create({publicKey:options}) : await navigator.credentials.get({publicKey:options});
      const response={clientDataJSON:encode(credential.response.clientDataJSON)};
      for (const name of ['attestationObject','authenticatorData','signature','userHandle']) if (credential.response[name]) response[name]=encode(credential.response[name]);
      if (credential.response.getTransports) response.transports=credential.response.getTransports();
      const result=await post('/sicherheit/passkeys/pruefen/',{id:credential.id,rawId:encode(credential.rawId),type:credential.type,response,clientExtensionResults:credential.getClientExtensionResults()});
      if (result.recovery.length) {status('Passkey gespeichert. Wiederherstellungscodes jetzt sicher speichern; danach Seite neu laden.');document.getElementById('passkey-recovery').textContent=result.recovery.join('\n');}
      else if (purpose==='reauth') status('Passkey bestätigt. Sicherheitsaktionen sind jetzt fünf Minuten freigegeben.');
      else window.location.assign(result.redirect);
    } catch (error) {status(error.name==='NotAllowedError' ? 'Browserbestätigung abgebrochen oder abgelaufen.' : error.message);}
    finally {button.disabled=false;}
  });
  for (const button of document.querySelectorAll('[data-passkey-remove]')) button.addEventListener('click',async()=> {
    try {await post('/sicherheit/passkeys/'+button.dataset.passkeyRemove+'/entfernen/',Object.fromEntries(new FormData(document.getElementById('passkey-form'))));window.location.reload();}
    catch(error) {status(error.message);}
  });
})();
