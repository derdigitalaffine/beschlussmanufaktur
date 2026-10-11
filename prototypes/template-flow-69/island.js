'use strict';
class TemplateFlowIsland extends HTMLElement {
  constructor(){
    super();
    this.state={pageVersion:7,serverVersion:7,status:'review',pending:false,message:'',messageKind:'info'};
  }
  connectedCallback(){this.render();this.bind();}
  render(){
    this.innerHTML=`
      <header class="page-header">
        <div><p class="eyebrow">Vorlage BM-2026-0042 · Stadt Beispiel</p><h1>Neubau der Grundschule Nord</h1>
        <div class="meta"><span class="badge" data-role="badge" data-state="review">In Prüfung</span><span>Version <strong data-role="version">7</strong></span><span>Verantwortlich: Fachprüfung</span></div></div>
        <a href="#island-changes">Änderungen seit letzter Prüfung</a>
      </header>
      <ol class="workflow" aria-label="Bearbeitungsstand"><li data-state="done">1. Entwurf ✓</li><li data-state="done">2. Fachprüfung ✓</li><li data-role="approval-step" data-state="current">3. Freigabe</li><li>4. Beratung</li><li>5. Beschluss</li></ol>
      <section class="prototype-controls" aria-label="Prototyp-Testzustand"><strong>Nur für den Test</strong><button data-action="stale" type="button" class="secondary">Neuere Serverversion simulieren</button> <button data-action="refresh" type="button" class="secondary" hidden>Aktuellen Serverstand übernehmen</button> <span class="small">Island verwaltet Page/Server/Pending/Stale explizit.</span></section>
      <div class="layout"><div>
        <section class="card" id="island-changes"><h2>Was hat sich geändert?</h2><ul class="change-list"><li>Beschlussvorschlag präzisiert: Bauabschnitt 2 ausdrücklich aufgenommen.</li><li>Anlage „Kostenberechnung.pdf“ durch Version vom 11.10.2026 ersetzt.</li></ul></section>
        <section class="card"><h2>Beschlussvorschlag</h2><p>Der Stadtrat beschließt die Umsetzung des Neubaus einschließlich Bauabschnitt 2 auf Grundlage der aktualisierten Kostenberechnung.</p></section>
        <section class="card"><h2>Begründung</h2><p>Die bestehende Schule erreicht ihre Kapazitätsgrenze. Der überarbeitete Entwurf bündelt die Bauabschnitte und schafft einen nachvollziehbaren Kostenrahmen.</p></section>
      </div><aside>
        <section class="card"><h2>Prüfauftrag</h2><p><strong>Bis:</strong> 14.10.2026</p><p><strong>Von:</strong> Schulverwaltung</p><p><strong>Nächster Schritt:</strong> Freigeben oder begründet zurückgeben.</p></section>
        <section class="card"><h2>Anlagen</h2><ul class="file-list"><li><a href="#">Kostenberechnung.pdf</a> <span class="badge">neu</span></li><li><a href="#">Lageplan.pdf</a></li></ul></section>
      </aside></div>
      <p class="status-line" data-role="status" role="status" aria-live="polite"></p>
      <div class="action-bar" aria-label="Aktionen"><button data-action="return-open" type="button" class="secondary danger">Zurückgeben</button><a href="#island-changes">Änderungen prüfen</a><button data-action="approve" class="primary" type="button">Freigeben</button></div>
      <dialog data-role="return-dialog" aria-labelledby="island-return-title"><form data-role="return-form"><h2 id="island-return-title">Vorlage zurückgeben</h2><p>Die Begründung wird zusammen mit der betroffenen Fassung angezeigt.</p><label class="field">Begründung<textarea name="reason" required>Bitte Kostenannahme für Bauabschnitt 2 erläutern.</textarea></label><div class="dialog-actions"><button data-action="return-cancel" type="button" class="secondary">Abbrechen</button><button type="submit" class="secondary danger">Begründet zurückgeben</button></div></form></dialog>`;
    this.update();
  }
  bind(){
    this.addEventListener('click',event=>{
      const action=event.target.closest('[data-action]')?.dataset.action;if(!action)return;
      if(action==='stale'){this.state.serverVersion+=1;this.message(`Testzustand: Server ist jetzt auf Version ${this.state.serverVersion}, die Island noch auf Version ${this.state.pageVersion}.`);}
      if(action==='refresh'){this.state.pageVersion=this.state.serverVersion;this.message('Aktueller Serverstand wurde übernommen. Entscheidung kann erneut geprüft werden.');this.update();this.querySelector('[data-action=approve]').focus();}
      if(action==='approve')this.submit('approve');
      if(action==='return-open')this.querySelector('[data-role=return-dialog]').showModal();
      if(action==='return-cancel')this.querySelector('[data-role=return-dialog]').close();
    });
    this.querySelector('[data-role=return-form]').addEventListener('submit',event=>{event.preventDefault();this.submit('return');});
  }
  message(text,kind='info'){this.state.message=text;this.state.messageKind=kind;this.update();}
  async submit(action){
    if(this.state.pending)return;
    this.state.pending=true;this.message('Wird serverseitig geprüft …');this.update();
    await new Promise(resolve=>setTimeout(resolve,180));
    if(this.state.pageVersion!==this.state.serverVersion){this.state.pending=false;this.message(`Zwischenzeitlich liegt Version ${this.state.serverVersion} vor. Vor einer Entscheidung muss der aktuelle Stand geprüft werden.`,'error');this.update();this.querySelector('[data-action=refresh]').focus();return;}
    this.state.serverVersion+=1;this.state.pageVersion=this.state.serverVersion;this.state.pending=false;this.state.status=action==='approve'?'approved':'returned';
    this.message((action==='approve'?'Freigabe':'Rückgabe')+' serverseitig bestätigt. Version '+this.state.serverVersion+'.');
    if(action==='return')this.querySelector('[data-role=return-dialog]').close();
    this.update();
  }
  update(){
    const badge=this.querySelector('[data-role=badge]');if(!badge)return;
    const labels={review:'In Prüfung',approved:'Freigegeben',returned:'Zurückgegeben'};badge.textContent=labels[this.state.status];badge.dataset.state=this.state.status==='approved'?'approved':'review';
    this.querySelector('[data-role=version]').textContent=String(this.state.pageVersion);
    const step=this.querySelector('[data-role=approval-step]');step.dataset.state=this.state.status==='review'?'current':'done';step.textContent=this.state.status==='approved'?'3. Freigabe ✓':this.state.status==='returned'?'3. Freigabe – zurückgegeben':'3. Freigabe';
    const status=this.querySelector('[data-role=status]');status.textContent=this.state.message;status.dataset.kind=this.state.messageKind;
    const stale=this.state.pageVersion!==this.state.serverVersion;const refresh=this.querySelector('[data-action=refresh]');refresh.hidden=!stale;
    for(const button of this.querySelectorAll('[data-action=approve], [data-role=return-form] button[type=submit]'))button.disabled=this.state.pending;
  }
}
customElements.define('template-flow-island',TemplateFlowIsland);
