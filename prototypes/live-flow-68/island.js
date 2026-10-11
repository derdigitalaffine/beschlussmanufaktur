'use strict';
class LiveMeetingIsland extends HTMLElement {
  constructor(){
    super();
    this.state={pageVersion:42,serverVersion:42,connection:'online',authority:true,quorum:18,pending:false,vote:'idle',ballots:0,message:'',messageKind:'info'};
  }
  connectedCallback(){this.renderShell();this.bind();this.update();}
  renderShell(){
    this.innerHTML=`
      <header class="page-head"><div><p class="eyebrow">Sitzung 12/2026 · 11.10.2026</p><h1>Rat der Stadt Beispiel · Sitzungsführung</h1><p class="small">Stand <strong data-role="page-version">42</strong> · Führender Dienst intern</p></div><a href="#island-events">Ereignisverlauf</a></header>
      <section class="live-status" aria-label="Live-Status">
        <div class="status-cell" data-role="connection-cell"><strong>Verbindung</strong><span data-role="connection-value"></span></div>
        <div class="status-cell" data-role="authority-cell"><strong>Sitzungshoheit</strong><span data-role="authority-value"></span></div>
        <div class="status-cell"><strong>Aktiver TOP</strong><span>TOP 7 · Grundschule Nord</span></div>
        <div class="status-cell" data-role="quorum-cell"><strong>Beschlussfähigkeit</strong><span data-role="quorum-value"></span></div>
        <div class="status-cell" data-role="vote-cell"><strong>Abstimmung</strong><span data-role="vote-value"></span></div>
      </section>
      <section class="test-controls" aria-label="Testzustände"><strong>Nur für Experiment:</strong><button data-action="stale" type="button" class="secondary">Neueren Serverstand simulieren</button><button data-action="offline" type="button" class="secondary">Verbindung trennen</button><button data-action="authority-loss" type="button" class="secondary">Sitzungshoheit verlieren</button><button data-action="recover" type="button" class="secondary" hidden>Serverstand neu laden</button></section>
      <div class="live-grid">
        <aside class="card"><h2>Tagesordnung</h2><ol class="agenda"><li><button data-state="done">TOP 5 · Jahresabschluss ✓</button></li><li><button data-state="done">TOP 6 · Feuerwehr ✓</button></li><li><button data-state="active" aria-current="step">TOP 7 · Grundschule Nord</button></li><li><button data-state="next">TOP 8 · Stadtentwicklung</button></li><li><button data-state="next">TOP 9 · Anfragen</button></li></ol></aside>
        <section class="card"><h2>TOP 7 · Neubau Grundschule Nord</h2><p><span class="badge ok">öffentlich</span> <span class="badge">Vorlage BM-2026-0042</span></p><label><strong>Protokolltext</strong><textarea data-role="note" class="note">Der Vorsitz ruft TOP 7 auf. Die Verwaltung erläutert die aktualisierte Kostenberechnung.</textarea></label><div class="motion"><strong>Antrag 1 · Sachantrag</strong><p>Bauabschnitt 2 wird ausdrücklich in den Beschluss aufgenommen.</p></div>
          <section class="vote-panel" aria-labelledby="island-vote-title"><h3 id="island-vote-title">Namentliche Abstimmung</h3><p data-role="vote-description"></p><div class="vote-progress" data-role="vote-progress" hidden><progress data-role="ballots" max="18" value="0"></progress><span><strong data-role="ballot-count">0</strong> / 18 Stimmen</span></div><div class="result-grid" data-role="vote-result" hidden><div><strong>11</strong>Ja</div><div><strong>6</strong>Nein</div><div><strong>1</strong>Enthaltung</div></div></section>
        </section>
        <aside class="card"><h2>Anwesenheit &amp; Quorum</h2><p class="quorum"><strong data-role="quorum-number"></strong><span>stimmberechtigt anwesend</span></p><p><span class="badge" data-role="quorum-badge"></span></p><ul class="participant-list"><li class="participant"><strong>A. Beispiel</strong> · anwesend · stimmberechtigt</li><li class="participant"><strong>B. Muster</strong> · anwesend · stimmberechtigt</li><li class="participant"><strong>C. Demo</strong> · anwesend · <span class="badge warn">Befangenheit geprüft: nein</span></li><li class="participant">… weitere 15 anwesend</li></ul><button data-action="quorum" type="button" class="secondary">Test: Quorum wechseln</button></aside>
      </div>
      <p class="status-message" data-role="message" role="status" aria-live="polite"></p>
      <div class="action-bar" aria-label="Live-Aktionen"><button data-action="save" type="button" class="secondary">Protokollstand speichern</button><button data-action="motion" type="button" class="secondary">Antrag aufnehmen</button><button data-action="primary" type="button" class="primary"></button></div>
      <details id="island-events"><summary>Vollständiger Ereignisverlauf</summary><div class="card"><p>Stand 42 · TOP 7 aufgerufen · Schriftführung</p><p>Stand 41 · Beschlussfähigkeit 18/28 festgestellt · Vorsitz</p></div></details>`;
  }
  bind(){
    this.addEventListener('click',event=>{
      const action=event.target.closest('[data-action]')?.dataset.action;if(!action)return;
      if(action==='primary')this.primary();
      if(action==='stale')this.simulateStale();
      if(action==='offline')this.simulateOffline();
      if(action==='authority-loss')this.simulateAuthorityLoss();
      if(action==='recover')this.recover();
      if(action==='quorum')this.toggleQuorum();
      if(action==='save')this.saveNote();
      if(action==='motion')this.setMessage('Prototyp: Antragserfassung ist sekundär und verändert den Vote-State in diesem Architekturvergleich nicht.');
    });
  }
  wait(ms){return new Promise(resolve=>setTimeout(resolve,ms));}
  setMessage(text,kind='info'){this.state.message=text;this.state.messageKind=kind;this.update();}
  blocked(){const s=this.state;return s.pending||s.connection!=='online'||!s.authority||s.pageVersion!==s.serverVersion||s.vote==='closed';}
  async primary(){
    if(this.blocked())return;
    if(this.state.vote==='idle')await this.transitionVote('pending-open','open');
    else if(this.state.vote==='open')await this.transitionVote('pending-close','closed');
  }
  async transitionVote(pendingState,doneState){
    this.state.pending=true;this.state.vote=pendingState;this.setMessage('Kritische Aktion gesendet · warte auf Serverbestätigung …');
    await this.wait(180);
    this.state.serverVersion+=1;this.state.pageVersion=this.state.serverVersion;this.state.pending=false;this.state.vote=doneState;
    if(doneState==='open'){
      this.state.ballots=0;this.setMessage(`Abstimmung serverseitig geöffnet · Stand ${this.state.serverVersion}.`);
      setTimeout(()=>{if(this.state.vote==='open'&&this.state.connection==='online'&&this.state.authority){this.state.ballots=18;this.setMessage('18 von 18 Stimmen serverseitig eingegangen. Abstimmung kann geschlossen werden.');}},160);
    }else{this.state.ballots=18;this.setMessage(`Abstimmung serverseitig abgeschlossen · Stand ${this.state.serverVersion}. Ergebnis 11 Ja · 6 Nein · 1 Enthaltung.`);}
  }
  simulateStale(){if(this.state.pending||this.state.vote==='closed')return;this.state.serverVersion+=1;this.state.connection='stale';this.setMessage(`Server ist bereits auf Stand ${this.state.serverVersion}. Kritische Aktionen bleiben bis zur Übernahme gesperrt.`,'error');this.focusRecover();}
  simulateOffline(){if(this.state.pending||this.state.vote==='closed')return;this.state.connection='offline';this.setMessage('Verbindung unterbrochen. Keine kritische Aktion wird lokal als erfolgreich behandelt.','error');this.focusRecover();}
  simulateAuthorityLoss(){if(this.state.pending||this.state.vote==='closed')return;this.state.authority=false;this.state.serverVersion+=1;this.setMessage('Sitzungshoheit wurde auf einem anderen Gerät übernommen. Schreiben und Abstimmen sind gesperrt.','error');this.focusRecover();}
  focusRecover(){this.update();this.querySelector('[data-action=recover]').focus();}
  recover(){this.state.pageVersion=this.state.serverVersion;this.state.connection='online';this.state.authority=true;this.setMessage(`Autoritativer Serverstand ${this.state.serverVersion} wurde übernommen. Kritische Aktionen sind wieder möglich.`);this.querySelector('[data-action=primary]').focus();}
  toggleQuorum(){if(this.state.pending)return;this.state.quorum=this.state.quorum===18?13:18;this.setMessage(this.state.quorum>=15?'Beschlussfähigkeit erneut mit 18 / 28 festgestellt.':'Testzustand: nur 13 / 28 anwesend. Abstimmung müsste fachlich neu bewertet werden.',this.state.quorum>=15?'info':'error');}
  async saveNote(){if(this.querySelector('[data-action=save]').disabled)return;this.state.pending=true;this.setMessage('Protokollstand wird gespeichert …');await this.wait(120);this.state.serverVersion+=1;this.state.pageVersion=this.state.serverVersion;this.state.pending=false;this.setMessage(`Protokollstand serverseitig bestätigt · Stand ${this.state.serverVersion}.`);}
  update(){
    const s=this.state;
    this.querySelector('[data-role=page-version]').textContent=String(s.pageVersion);
    const connectionCell=this.querySelector('[data-role=connection-cell]');connectionCell.dataset.kind=s.connection==='online'?'ok':s.connection==='stale'?'warn':'danger';this.querySelector('[data-role=connection-value]').textContent=s.connection==='online'?'● Online · bestätigt':s.connection==='stale'?`● Veraltet · Server Stand ${s.serverVersion}`:'● Offline · keine Bestätigung';
    const authorityCell=this.querySelector('[data-role=authority-cell]');authorityCell.dataset.kind=s.authority?'ok':'danger';this.querySelector('[data-role=authority-value]').textContent=s.authority?'Schriftführung aktiv':'Sitzungshoheit verloren';
    const qok=s.quorum>=15;this.querySelector('[data-role=quorum-cell]').dataset.kind=qok?'ok':'danger';this.querySelector('[data-role=quorum-value]').textContent=`${s.quorum} / 28 · ${qok?'festgestellt':'nicht beschlussfähig'}`;this.querySelector('[data-role=quorum-number]').textContent=`${s.quorum} / 28`;const qbadge=this.querySelector('[data-role=quorum-badge]');qbadge.textContent=qok?'Beschlussfähigkeit festgestellt':'Nicht beschlussfähig';qbadge.className=`badge ${qok?'ok':'warn'}`;
    const labels={idle:'Keine Abstimmung offen','pending-open':'Öffnung wird bestätigt …',open:`Offen · ${s.ballots} / 18 Stimmen`,'pending-close':'Abschluss wird bestätigt …',closed:'Abgeschlossen · 11 / 6 / 1'};this.querySelector('[data-role=vote-value]').textContent=labels[s.vote];this.querySelector('[data-role=vote-cell]').dataset.kind=s.vote==='open'?'warn':s.vote==='closed'?'ok':'';
    const voteProgress=this.querySelector('[data-role=vote-progress]');voteProgress.hidden=!['open','pending-close'].includes(s.vote);this.querySelector('[data-role=ballots]').value=s.ballots;this.querySelector('[data-role=ballot-count]').textContent=String(s.ballots);this.querySelector('[data-role=vote-result]').hidden=s.vote!=='closed';
    this.querySelector('[data-role=vote-description]').textContent=s.vote==='idle'?'Noch nicht gestartet. Gegenstand: Beschlussvorschlag inklusive Antrag 1.':s.vote==='open'?'Abstimmung ist serverseitig geöffnet. Eingehende Stimmen werden angezeigt.':s.vote==='closed'?'Ergebnis serverseitig bestätigt und diesem TOP zugeordnet.':'Kritische Aktion wartet auf Serverbestätigung.';
    const primary=this.querySelector('[data-action=primary]');primary.textContent=s.vote==='idle'?'Namentliche Abstimmung starten':s.vote==='open'?'Abstimmung schließen':s.vote==='closed'?'Abstimmung abgeschlossen':'Serverbestätigung ausstehend …';primary.disabled=this.blocked();
    const secondaryLocked=s.pending||s.connection!=='online'||!s.authority||s.pageVersion!==s.serverVersion;this.querySelector('[data-action=save]').disabled=secondaryLocked;this.querySelector('[data-action=motion]').disabled=secondaryLocked;
    const recover=this.querySelector('[data-action=recover]');recover.hidden=s.connection==='online'&&s.authority&&s.pageVersion===s.serverVersion;recover.textContent=!s.authority?'Sitzungshoheit neu prüfen':s.connection==='offline'?'Neu verbinden':'Serverstand neu laden';
    const message=this.querySelector('[data-role=message]');message.textContent=s.message;message.dataset.kind=s.messageKind;
  }
}
customElements.define('live-meeting-island',LiveMeetingIsland);
