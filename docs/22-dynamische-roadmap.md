# Dynamische Produktroadmap

Die Roadmap ist kein statischer Terminplan. Sie ist ein priorisiertes Portfolio überprüfbarer **Outcomes**. GitHub-Issues sind die operative Quelle; dieses Dokument definiert den Vertrag. Issue #41 zeigt das automatisch erzeugte Lagebild, Issue #38 die parallelen Arbeitsclaims/Kollisionen.

## 1. Roadmap-Ziele

Die Roadmap soll jederzeit beantworten:

1. Welches Nutzer-/Produktproblem lösen wir als Nächstes?
2. Warum ist es jetzt wichtiger als andere Arbeit?
3. Welche Risiken und Abhängigkeiten bestehen?
4. Welche Qualitätsgates fehlen noch?
5. Welche Entscheidung ist offen und welche Perspektiven müssen sie challengen?
6. Was blockiert Produktivfreigabe?

## 2. Maschinenlesbares Roadmap-Issue

Jedes Roadmap-Arbeitspaket beginnt mit dem exakten Marker und Feldern:

```md
<!-- roadmap:item:v1 -->
## Roadmap metadata
- Stream: ux | architecture | security | identity | portal | operations | voting | release | other
- Outcome: <messbare gewünschte Wirkung>
- Horizon: now | next | later | release-gate
- Priority: P0 | P1 | P2 | P3
- Status: discovery | ready | implementation | validation | blocked
- Risk: critical | high | medium | low
- Quality gates: G0 | G0,G1 | G0,G1,G2 | G0,G1,G2,G3 | G0,G1,G2,G3,G4
- Depends on: #... | none
- Blocks: #... | none
- Coordination keys: <keys> | none
- Council required: yes | no
- Decision questions: <kurze offene Fragen> | none
- Evidence: <PR/Test/Abnahme/ADR> | none yet
- Last reviewed: YYYY-MM-DD
```

Danach folgen Problem, Nicht-Ziele, Akzeptanzkriterien und konkrete Fragestellungen.

## 3. Horizonte

### `now`
Arbeit, die aktuell den höchsten Wert/Risikobau oder eine direkte Abhängigkeit für weitere Kernarbeit besitzt. `now` bedeutet nicht automatisch „bereits implementieren“; Discovery kann die richtige aktuelle Arbeit sein.

### `next`
Klar genug vorbereitet, aber von `now` abhängig oder bewusst nachgelagert. Ein `next`-Item sollte nicht gleichzeitig breit implementiert werden, wenn sein Vertrag noch durch `now` verändert wird.

### `later`
Wichtig, aber aktuell kein Engpass. Es darf Discovery geben, wenn dadurch eine spätere Sackgasse vermieden wird, jedoch keine heimliche Prioritätsverschiebung.

### `release-gate`
Querschnittsarbeit, die vor Produktivfreigabe nachweislich abgeschlossen sein muss, z. B. End-to-End-Abnahme, Geräte, Restore, Last oder unabhängige Sicherheitsprüfung.

## 4. Priorität

Priorität ist keine Wunschliste:

- **P0:** akuter Sicherheits-/Datenintegritätsfehler oder zwingender Releaseblocker; unterbricht gewöhnliche Roadmaparbeit;
- **P1:** hoher Nutzerwert, hohes Risiko oder kritische Abhängigkeit des KERNs;
- **P2:** wichtige Qualitäts-/Komfortverbesserung ohne unmittelbaren Blocker;
- **P3:** opportunistisch/später, solange P0–P2 nicht begründet verdrängt werden.

Der Hauptagent darf Horizonte/Prioritäten ändern, muss aber im Issue eine kurze Begründung und neue Abhängigkeiten hinterlassen. Das Dashboard spiegelt Metadaten; es entscheidet nicht selbst über Produktstrategie.

## 5. Status

- `discovery`: Problem/Optionen werden untersucht; keine voreilige Implementierungsbindung;
- `ready`: G0/G1 ausreichend erfüllt, Umfang/Abnahme implementierbar;
- `implementation`: aktiver Claim/Branch nach AGENTS.md;
- `validation`: Implementierung vorhanden, aber G3/G4-Nachweise fehlen;
- `blocked`: externer/architektonischer Blocker benannt; keine stille Dauerreservierung.

## 6. Dynamische Pflege

Roadmap-Metadaten werden bei folgenden Ereignissen geprüft/aktualisiert:

- neue Erkenntnis ändert Risiko oder Outcome;
- Council-Entscheidung schließt/öffnet eine Architekturfrage;
- PR verändert Verträge oder schließt Teilumfang;
- Abhängigkeit wird geschlossen oder entsteht neu;
- Test/Abnahme widerlegt eine Annahme;
- Security-Finding ändert Priorität;
- Nutzerforschung zeigt einen anderen Engpass.

Der Workflow `.github/workflows/roadmap-dashboard.yml` reagiert auf Issue-/PR-Aktivität und zusätzlich zeitgesteuert. Er aktualisiert in #41 eine einzige Sticky-Übersicht mit offenen Items, Warnungen und Review-Alter.

## 7. Portfolio-Regeln für parallele Agenten

### Begrenzte Parallelität
Nicht möglichst viele Agenten gleichzeitig starten. Parallelisiert werden nur Arbeitspakete, deren Verträge ausreichend getrennt sind. Shared Contracts zuerst stabilisieren.

### Outcome-Split statt Dateisplit
Gute Aufteilung: „Navigation/Designsystem“, „Threat Model/Auth“, „Backup/Restore“. Schlechte Aufteilung: „Agent A bearbeitet views.py, Agent B CSS“, wenn beide dieselbe Nutzerfunktion designen.

### Discovery parallel, Implementierung sequenziert
Bei unklarer Architektur dürfen mehrere Perspektiven Optionen untersuchen. Nach einer Council-Entscheidung gibt es genau einen kanonischen Implementierungsvertrag.

### Challenger unabhängig halten
Wer die Lösung implementiert, soll bei hohem Risiko nicht allein ihre Sicherheit/UX-Freigabe definieren. Challenger prüfen Annahmen und Negativfälle, nicht nur Codeformat.

## 8. Qualitätsgates aus dem Zielbild

- **G0 Problem verstanden**
- **G1 Lösung entschieden**
- **G2 Implementiert**
- **G3 Integriert geprüft**
- **G4 Freigabereif**

Roadmap-Status und Gate sind verschieden: Ein Item kann `validation` sein und G0–G2 besitzen. `completed`/geschlossen bedeutet, dass die im Issue definierten Akzeptanzkriterien erfüllt sind; für Produktivfreigabe können übergeordnete G4-Gates weiterhin offen sein.

## 9. Initiale strategische Reihenfolge

Die folgende Reihenfolge ist ein Startpunkt und wird durch Roadmap-Issues konkretisiert.

### Horizont NOW – Fundament perfektionieren

1. **UX-/Designsystem und kritische Nutzerreisen**: vorhandene technische/uneinheitliche Oberflächen in ein konsistentes Interaktionsmodell überführen; echte Fachanwenderaufgaben messen.
2. **Frontend-Architekturentscheidung per Prototyp**: Django/Progressive Enhancement vs. Hybrid/React anhand Live-/Offline-/Accessibility-/Performance-Evidenz entscheiden, keine Technologiemigration aus Modegründen.
3. **Security Baseline und Threat Model**: Vertrauensgrenzen, Missbrauchsfälle, ASVS-orientierte Verifikation, Security-Regression-Gates.

### Horizont NEXT – offene Kernflächen

4. **Bürgerportal, Suche, Domain/CI, iframe-Grenzen**: eigenständige öffentliche UX mit strikter Projektion und Leak-Negativtests.
5. **Identität/Admin-Komfort sicher vervollständigen**: Import, Recovery, TOTP/Passkeys, Notfallzugriff, sichere Diagnose und Rechte-UX.
6. **Betrieb, Backup/Restore, Upgrade/Rollback**: nachweisbare Wiederherstellung und verständliche Betriebszustände statt „Container läuft“.

### Horizont LATER – Hochrisiko-Spezialfunktion

7. **Digitale geheime Verfahren**: fachliche/rechtliche Zulässigkeit, Protokollentwurf, unabhängige Security-Analyse und erst dann Implementierungsentscheidung. Papierweg bleibt sichere Rückfallebene.

### RELEASE-GATE

8. **Freigabereife**: vollständige KERN-Szenarien, Geräte/iPad/Firefox, Accessibility, Last, Zweiserverbetrieb, Restore, Security und Fachanwenderabnahme mit dokumentierter Evidenz.

Aufnahme/Transkription/KI und Sitzungsgeld bleiben bis nach Kernfreigabe außerhalb dieser Reihenfolge.

## 10. WIP-Leitplanken

Als Default gelten:

- maximal 3 gleichzeitig aktive P1-Implementierungs-Outcomes;
- beliebige zusätzliche Discovery nur, wenn sie aktive Verträge nicht blockiert und einen klaren Entscheidungstermin besitzt;
- pro Shared Contract genau ein führendes Issue;
- kein neues `now`, wenn ein bestehendes `now` nur wegen fehlender Handoff-/Validierungsarbeit liegen bleibt.

Der Hauptagent kann abweichen, dokumentiert aber warum die zusätzliche Parallelität den Durchsatz statt nur Aktivität erhöht.

## 11. Roadmap-Review

Bei jeder wesentlichen Lieferung prüft der Hauptagent:

- Ist der aktuelle Engpass noch derselbe?
- Wurde ein Risiko geschlossen oder nur verschoben?
- Welche Abhängigkeit ist jetzt frei?
- Muss ein `next` zu `now` werden?
- Gibt es ein P0/P1-Finding?
- Welche Items sind >7 Tage nicht geprüft und warum?
- Welche G3/G4-Evidenz fehlt trotz fertigem Code?

Roadmappflege ist Teil der Lieferung, keine separate spätere Verwaltungsarbeit.
