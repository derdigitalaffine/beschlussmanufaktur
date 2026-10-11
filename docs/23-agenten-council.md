# Agenten-Council für strittige Produktentscheidungen

Das Council ist ein sichtbares Gegenprüfungsverfahren für Entscheidungen mit hoher Tragweite. Es ersetzt keine menschliche Fach-/Rechtsfreigabe und simuliert keine unabhängigen Experten, die nicht tatsächlich beteiligt sind. Stattdessen zwingt es Coding-Agenten und Menschen, relevante Perspektiven getrennt zu formulieren, Annahmen zu widerlegen und eine begründete Entscheidung im Issue zu hinterlassen.

## 1. Wann ein Council Pflicht ist

`Council required: yes` gilt standardmäßig bei:

- neuer oder wesentlich geänderter Authentisierung/MFA/Recovery;
- Änderungen an Rechte-, Veröffentlichungs- oder Vertrauensgrenzen;
- Frontend-Architekturwechsel oder größere Frameworkmigration;
- Live-Sitzungs-, Sync- oder Offline-Konsistenzvertrag;
- digitalen geheimen Abstimmungen/Wahlen;
- Speicherung/Übertragung neuer sensibler Datenklassen;
- Backup-/Restore-/Schlüsselmanagement mit Produktivwirkung;
- bewusster Accessibility- oder Security-Ausnahme;
- Entscheidungen, die mehrere aktive Roadmap-Outcomes blockieren.

Der Hauptagent kann ein Council zusätzlich verlangen, wenn Unsicherheit hoch oder Rework teuer wäre.

## 2. Perspektiven

Nicht jede Perspektive braucht eine eigene Person; sie muss aber **separat argumentiert** werden. Bei hohem Risiko soll die Challenger-Perspektive möglichst von einem anderen Agenten/Menschen als der Implementierungsposition kommen.

### Lead / Synthese
Verantwortet Problemformulierung, Scope, Abhängigkeiten und am Ende die nachvollziehbare Entscheidung. Der Lead gewinnt keine Abstimmung automatisch durch seine Rolle.

### Fachlichkeit / Domain
Fragt: Ist die Lösung fachlich korrekt, nachvollziehbar, revisionsfähig und mit den bestätigten Abläufen vereinbar? Welche Ausnahme-/Randfälle fehlen?

### UX / Frontend
Fragt: Versteht ein Nutzer Zustand, Konsequenz und nächsten Schritt? Welche Interaktionskosten, Fehlhandlungen oder Geräteprobleme entstehen? Gibt es eine einfachere Lösung?

### Security / Privacy
Fragt: Wie kann die Funktion missbraucht werden? Welche Vertrauensannahme ist zu optimistisch? Welche Daten leaken indirekt? Wie sieht deny-by-default und sichere Wiederherstellung aus?

### Accessibility / Performance
Fragt: Funktioniert die Lösung mit Tastatur, Screenreader, Zoom/Touch und reduzierter Bewegung? Welche Latenz oder Renderingkosten entstehen unter realer Last?

### Operations / Reliability
Fragt: Wie wird deployt, beobachtet, zurückgerollt und wiederhergestellt? Was passiert bei Teilfehlern, Wiederholung, Netztrennung oder Ressourcenknappheit?

### Test / Adversarial Reviewer
Versucht die behauptete Lösung aktiv zu widerlegen: Negativfälle, Race Conditions, falsche Reihenfolgen, abgelaufene Rechte, doppelte Requests, manipulierte Inputs und unvollständige Migrationen.

## 3. Ablauf

### Schritt A – Entscheidungsfrage scharf stellen

Keine Debatte über „bestes Frontend“. Gute Frage:

> Welche UI-Architektur reduziert für Live-Schriftführung und Offline-Konflikte die Zustandskomplexität messbar, ohne Accessibility, CSP, Ladevolumen und schrittweise Migration zu verschlechtern?

Der Lead listet Optionen, Nicht-Ziele, vorhandene Evidenz und Entscheidungskriterien.

### Schritt B – unabhängige Positionen

Positionen werden als einzelne Kommentare mit Marker geschrieben:

```md
<!-- council:position:v1 -->
## Council position
- Perspective: domain | ux | security | accessibility-performance | operations | test | other
- Preferred option: ...
- Strongest reason: ...
- Evidence: ...
- Failure mode I worry about most: ...
- What would change my mind: ...
- Required test/prototype: ...
```

Wichtig: Positionen sollen sich nicht nur gegenseitig paraphrasieren. Ein Challenger nennt mindestens einen konkreten Fehlermodus oder eine widerlegbare Annahme.

### Schritt C – Gegenseitige Challenge

Nach den Positionen werden Widersprüche explizit bearbeitet:

- Welche Annahme teilen mehrere Positionen, ohne sie geprüft zu haben?
- Wo optimiert eine Option lokal und verschiebt Kosten in Betrieb/Security/UX?
- Welche Daten fehlen für eine Entscheidung?
- Kann ein kleiner Prototyp die Unsicherheit billiger reduzieren als weitere Diskussion?
- Welche Option hat den sichersten Rückweg?

### Schritt D – Entscheidung oder Experiment

Der Lead veröffentlicht einen Decision Record:

```md
<!-- council:decision:v1 -->
## Council decision
- Decision: adopt | adapt | reject | experiment | defer
- Chosen option: ...
- Why: ...
- Rejected alternatives: ...
- Security/privacy consequence: ...
- UX/accessibility consequence: ...
- Operations consequence: ...
- Required evidence before G2/G3/G4: ...
- Revisit trigger: ...
- Decision date: YYYY-MM-DD
```

Wenn Evidenz fehlt, lautet die Entscheidung `experiment` statt „gefühlte Architekturentscheidung“. Ein Experiment erhält messbare Erfolgskriterien und begrenzten Umfang.

## 4. Hauptagenten-Aufteilung

Der Hauptagent verteilt nicht einfach Features an möglichst viele Agenten. Er zerlegt zuerst nach **Fragen und Risiken**.

Beispiel Frontend:

- Agent/Perspektive A: analysiert drei repräsentative Nutzerreisen und heutige UX-Brüche;
- B: baut einen kleinen interaktiven Prototyp für den schwierigsten Zustand;
- C: threat-modelt Clientzustand, API-Verträge und Offlinecache;
- D: prüft Tastatur/Screenreader/Touch und Performancekosten;
- E: bewertet Migration, Testbarkeit und Betriebsfolgen;
- Lead: synthetisiert, lässt Widersprüche challengen und schneidet erst danach Implementierungsissues.

So entsteht Parallelität in der Erkenntnisgewinnung, ohne fünf konkurrierende Implementierungen desselben Vertrags.

## 5. Standardfragen vor Implementierung

### Produkt/Fachlichkeit
- Welcher Nutzer erreicht welches Outcome?
- Was ist der häufigste Normalfall, was der gefährlichste Randfall?
- Welche heutige Funktion wird ersetzt, vereinfacht oder wiederverwendet?

### UX
- Was sieht der Nutzer zuerst?
- Woran erkennt er Erfolg, Fehler, ausstehenden Sync und Berechtigungsgrenze?
- Was ist die primäre Aktion?
- Wie sieht derselbe Ablauf auf Laptop, Tablet und schmalem Bildschirm aus?

### Security/Privacy
- Welche Eingabe/Antwort ist untrusted?
- Welche Rechteprüfung muss serverseitig erneut stattfinden?
- Was passiert bei Replay, IDOR, Race, abgelaufener Rolle, gestohlener Session?
- Welche Metadaten verraten möglicherweise geschützte Existenz/Inhalte?

### Accessibility/Performance
- Funktioniert der Flow ohne Maus?
- Wie wird Fokus nach Mutation/Dialog/Fehler gesetzt?
- Was liest ein Screenreader bei Statusänderung?
- Welche Datenmenge/DOM-Größe/Netzrequests entstehen im Worst Case?

### Betrieb
- Wie wird ein halbfertiger Rollout erkannt/zurückgerollt?
- Was passiert bei DB/SMTP/Sync/File-Fehlern?
- Welche Metrik oder Adminmeldung macht das Problem handlungsfähig?

## 6. Review-Prinzip

Ein PR mit `Council required: yes` verweist auf den `council:decision:v1`-Kommentar. Reviewer prüfen nicht nur, ob die gewählte Option implementiert wurde, sondern ob die dort festgelegten Invarianten und Tests eingehalten sind.

Neue Evidenz darf eine Council-Entscheidung revidieren. Das ist kein Scheitern, solange die Änderung dokumentiert und abhängige Roadmap-Items aktualisiert werden.

## 7. Was ausdrücklich nicht passieren soll

- Scheindebatten, in denen derselbe Agent mehrere „Rollen“ nur pro forma bestätigt;
- Architekturentscheidungen ohne messbare Kriterien;
- Security als End-of-project-Pentest;
- UX als reine Farb-/Spacing-Nacharbeit;
- Accessibility als einmaliger Scannerlauf;
- zehn parallele Agentenbranches auf denselben Kernvertrag;
- Roadmap-Status „fertig“, obwohl Validierung/Restore/Abnahme fehlen.
