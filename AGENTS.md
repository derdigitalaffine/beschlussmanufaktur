# Entwicklungsvorgaben

Dieses Repository wird von Menschen und Coding-Agenten parallel bearbeitet. **GitHub ist die gemeinsame Koordinationsebene.** Arbeitsstand, Reservierungen, Abhängigkeiten und Übergaben müssen in Issues und Pull Requests sichtbar sein; keine zweite private Aufgabenverwaltung darf für die Zusammenarbeit maßgeblich sein.

## Autorität und gemeinsames Lagebild

1. **Issue #38** ist der zentrale Steuerpunkt für repo-weite Prioritäten, Architekturkonflikte und das automatische Koordinations-Dashboard.
2. Das jeweilige **Arbeits-Issue** besitzt Umfang, Abnahmekriterien, aktiven Claim und Handoffs.
3. Der **Pull Request** besitzt die konkrete Implementierung, Tests und Review-Diskussion.
4. `AGENTS.md`, `docs/agentenkoordination.md`, README und die fachlichen Dokumente unter `docs/` definieren die gemeinsamen Regeln.

Bei widersprüchlichen Vorgaben Umfang nicht still erweitern oder reduzieren, sondern den Konflikt im Arbeits-Issue sichtbar machen. Repo-weite Konflikte zusätzlich in #38 festhalten.

## Pflicht-Preflight vor nicht-trivialer Arbeit

Vor dem Ändern von Code oder gemeinsam genutzten Verträgen:

1. #38 einschließlich aktuellem Dashboard und relevanten neuen Kommentaren lesen.
2. Ziel-Issue vollständig lesen.
3. Offene Issues nach `<!-- coordination:claim:v2 -->` und offene Pull Requests auf überlappenden Umfang prüfen.
4. Prüfen, ob bestehende Modelle, APIs, Berechtigungsregeln oder fachliche Dokumente den Bereich bereits verbindlich definieren.
5. Bei Überschneidung **vor dem Codieren kommentieren** und Split, Abhängigkeit, gemeinsamen Vertrag, Merge-Reihenfolge oder Handoff vereinbaren. Stille Doppelimplementierung ist nicht zulässig.

Der Preflight ist nur eine Momentaufnahme. Bei wesentlicher Umfangserweiterung, vor Öffnen eines PRs und nach einem größeren Rebase auf einen aktiven `main` erneut prüfen.

## Claim-Protokoll

Nicht-triviale aktive Arbeit erhält genau einen kanonischen Claim als Kommentar im Arbeits-Issue. Der HTML-Marker muss exakt verwendet werden:

```md
<!-- coordination:claim:v2 -->
## Work claim
- Worker: @<login> (agent|human|agent-assisted)
- Phase: discovery | implementation | review | blocked
- Scope: <eine klar begrenzte Lieferung>
- Branch: <Branch oder `none` während discovery>
- PR: <#Nummer oder `none`>
- Touches: <Domänen, APIs, Migrationen, UI-Flächen, wahrscheinliche Pfade>
- Coordination keys: <kommagetrennte Schlüssel oder `none`>
- Contracts changed: <keine oder explizite Verträge>
- Depends on: #... | none
- Parallel-safe with: #... | <benachbarter Umfang> | none known
- Avoids / out of scope: ...
- Collision scan: #38 + offene Claims + offene PRs geprüft
```

Regeln:

- Ein Implementierungs-Branch hat genau ein kanonisches Liefer-Issue.
- `discovery` darf kurzzeitig ohne Branch/PR laufen; `implementation` braucht einen Branch; `review` braucht einen PR und friert den Umfang bis auf Review-/CI-Korrekturen ein.
- `blocked` nennt den Blocker sichtbar im Issue und reserviert nicht unbegrenzt einen breiten Bereich.
- Wenn Phase, Branch, Schlüssel oder materieller Umfang wechseln, den bestehenden kanonischen Claim aktualisieren statt konkurrierende Claims zu stapeln.
- Claims reservieren einen begrenzten Arbeitsumfang, keine gesamte Domäne.

## Coordination keys und Kollisionsregel

`Coordination keys` sind kurze maschinenlesbare Kennungen für gemeinsam veränderbare Verträge. Beispiele: `domain:decisions`, `model:Decision`, `api:meeting-live`, `ui:decision-detail`, `migration:core`, `policy:permissions`, `workflow:agent-coordination`. Keine unscharfen Schlüssel wie `domain:backend` oder `ui:frontend` verwenden. Wenn nichts kollidieren kann, ausdrücklich `none` schreiben.

Starke Kollisionssignale in absteigender Priorität:

1. gleicher aktiver Branch oder dasselbe kanonische Liefer-Issue;
2. identischer Coordination key für einen Vertrag, den beide Arbeiten verändern können;
3. exakte Dateiüberschneidung zwischen offenen PRs;
4. wahrscheinliche Pfad-/Oberflächenüberschneidung aus Claims;
5. während der Umsetzung entdeckte Abhängigkeits- oder Architekturüberschneidung.

Bei materieller Überschneidung nicht gegeneinander implementieren. Bevorzugt nach unabhängiger Schnittstelle/Schicht teilen, einen gemeinsamen Vertrag zuerst liefern, Merge/Rebase explizit sequenzieren oder einen Umfang übergeben/superseden. Sobald eine Änderung den Vertrag eines anderen aktiven Issues berührt, dort bzw. im PR sofort koordinieren.

## Handoff, Pause und Abschluss

Eine Übergabe muss ohne Rekonstruktion versteckten Kontexts fortsetzbar sein:

```md
<!-- coordination:handoff:v2 -->
## Handoff
- Disposition: continue | superseded | paused | abandoned | completed
- Successor: #... | @... | none
- Branch/PR: <Branch und/oder #PR>
- Completed: ...
- Remaining: ...
- Decisions / invariants: ...
- Tests run: ...
- Risks / open questions: ...
- Suggested next files/issues: ...
```

`continue` lässt den Umfang aktiv. `superseded`, `paused`, `abandoned` und `completed` beenden den bisherigen aktiven Claim, bis ein neuer Claim folgt. Das Dashboard in #38 ist ein Lagebild und eine Warnhilfe; Konfliktwarnungen erfordern menschliches/agentisches Urteil und sind kein automatischer Merge-Blocker.

## Pull Requests

Jeder nicht-triviale PR referenziert sein Arbeits-Issue mit einer eigenständigen Beziehungslinie (`Closes #123`, `Refs #123` oder `Part of #123`) und nutzt `.github/PULL_REQUEST_TEMPLATE.md`. Vor Merge:

- Claim auf `Phase: review` mit aktuellem Branch/PR bringen;
- Claims und offene PRs erneut auf Kollisionen prüfen;
- Tests, bekannte Grenzen, Sicherheits-/Berechtigungsauswirkungen und ggf. Migration/Rollback dokumentieren;
- bei verbleibender absichtlicher Überschneidung Merge-Reihenfolge und Handoff sichtbar festhalten.

## Bestehende fachliche und technische Vorgaben

- Grundlage sind README und docs/01 bis docs/10. Bestehende Anforderungen nicht still reduzieren.
- Jede Änderung über einen eigenen Branch und Pull Request; nach erfolgreichen relevanten Prüfungen mergen. Keine direkten Implementierungscommits auf main.
- Kein Merge bei fehlgeschlagenen relevanten Checks. Offene technische Grenzen im PR und Implementierungsstand dokumentieren.
- Serverseitige Rechte standardmäßig verweigern, aktiven Arbeitskontext und gültige Zuweisung prüfen. Technische Superuser erhalten keine impliziten Fachrechte.
- Öffentlicher Dienst erhält keine geschützten Daten und keine internen Zugangswege. Von außen initiierte Verbindung nach innen bleibt standardmäßig gesperrt.
- Aufnahme/Transkription/KI und Sitzungsgeld erst nach Kernabschluss entwickeln.
- Tests: `cd backend && ../.venv/bin/python manage.py test --settings=config.test_settings`.
- Migrationen einchecken; `makemigrations --check --dry-run` muss ohne Änderungen enden.
- Geheimnisse, Datenbanken und lokale Laufzeitdateien niemals committen.
