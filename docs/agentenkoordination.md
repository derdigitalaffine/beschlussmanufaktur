# Agentenkoordination

Diese Anleitung konkretisiert den Koordinationsvertrag aus `AGENTS.md`. Das Prinzip ist bewusst dezentral: Es gibt keinen Agenten-Orchestrator, der Arbeit im Verborgenen verteilt. Menschen und Agenten organisieren sich über denselben sichtbaren GitHub-Zustand.

## Grundmodell

- **#38 ist das gemeinsame Lagebild.** Repo-weite Abhängigkeiten und Architekturkonflikte werden dort sichtbar.
- **Ein Arbeits-Issue ist die Einheit der Arbeit.** Dort stehen Ziel, Abnahmekriterien, Claim und Handoffs.
- **Ein Branch ist die Einheit der Implementierung.** Ein Branch gehört zu genau einem kanonischen Liefer-Issue.
- **Ein Pull Request ist die Einheit der Lieferung und des Reviews.** Er referenziert das Arbeits-Issue deklarativ.
- **Coordination keys beschreiben gemeinsam veränderbare Verträge.** Sie erlauben Kollisionserkennung auch dann, wenn zwei Arbeiten noch keine identischen Dateien anfassen.

Das Dashboard ist absichtlich nur beratend. Es ersetzt keine fachliche Entscheidung und keine Code-Review.

## Ablauf für einen Worker

### 1. Discovery / Preflight

Vor aktiver Arbeit:

1. #38 und das Ziel-Issue lesen.
2. Andere offene Claims und Pull Requests prüfen.
3. Relevante fachliche Vorgaben und bestehende Modelle/APIs identifizieren.
4. Kollisionsschlüssel und voraussichtliche Pfade bestimmen.
5. Bei Überschneidungen zuerst öffentlich abstimmen.

Für kurze Discovery darf der Claim `Branch: none` enthalten. Sobald Code geändert wird, ist ein Branch Pflicht.

### 2. Arbeit claimen

Diesen Block als Kommentar im Arbeits-Issue verwenden und aktuell halten:

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

Der exakte HTML-Marker ist Teil des Maschinenvertrags. Freitext wie `coordination:claim:v2` ohne Marker wird nicht als gültiger Claim behandelt.

### 3. Coordination keys wählen

Schlüssel sollen den kleinsten stabilen gemeinsamen Vertrag benennen, der wirklich verändert werden kann. Geeignete Namensräume sind zum Beispiel:

| Namespace | Zweck | Beispiele |
| --- | --- | --- |
| `domain:` | fachliche Domäne | `domain:decisions`, `domain:meetings` |
| `model:` | stabiles Modell/Aggregat | `model:Decision`, `model:Meeting` |
| `api:` | API-/Payload-Vertrag | `api:meeting-live`, `api:decision-export` |
| `ui:` | gemeinsam genutzte Oberfläche | `ui:decision-detail`, `ui:meeting-live` |
| `migration:` | Schema-/Datenmigration | `migration:core` |
| `policy:` | Querschnittsregel | `policy:permissions`, `policy:public-boundary` |
| `workflow:` | Entwicklungsautomation | `workflow:agent-coordination` |

Breite Schlüssel wie `domain:backend`, `ui:frontend` oder `model:all` sind keine sinnvolle Reservierung. Wenn kein geteilter Vertrag betroffen ist, `none` verwenden.

### 4. Bei Kollision koordinieren

Das Dashboard und der Preflight betrachten insbesondere:

1. denselben Branch bzw. dasselbe Liefer-Issue;
2. identische Coordination keys;
3. identische geänderte Dateien offener PRs;
4. deklarierte Pfad-/Oberflächenüberschneidung;
5. später entdeckte Architektur-/Abhängigkeitskollisionen.

Eine Kollision bedeutet nicht automatisch „Stop“. Sie bedeutet: sichtbar entscheiden. Gute Lösungen sind ein Split nach Schnittstelle oder Schicht, ein zuerst veröffentlichter gemeinsamer Vertrag, eine explizite Merge-Reihenfolge oder ein Handoff. Zwei Agenten sollen nicht schweigend dieselbe Lösung gegeneinander bauen.

### 5. PR öffnen und Claim auf Review stellen

Der PR nutzt `.github/PULL_REQUEST_TEMPLATE.md` und enthält eine eigenständige Beziehungslinie:

```md
Closes #123
```

wenn er das Issue vollständig abschließt, oder beispielsweise:

```md
Refs #123
```

für einen Teilumfang. Narrative Sätze wie „does not close #123“ sind kein verlässlicher Maschinenvertrag und sollen vermieden werden.

Danach den bestehenden Claim aktualisieren:

```md
- Phase: review
- Branch: <branch>
- PR: #<nummer>
```

Vor Merge den Kollisionsscan wiederholen, besonders nach Rebase oder wenn sich der Umfang geändert hat.

### 6. Handoff / Pause / Abschluss

Diesen Block verwenden, wenn ein anderer Worker ohne versteckten Kontext übernehmen können soll oder der aktive Umfang endet:

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

`continue` hält den Umfang aktiv. `superseded`, `paused`, `abandoned` und `completed` beenden den bisherigen Claim, sofern danach kein neuerer Claim folgt. Ein späterer Worker eröffnet keinen parallelen Privatplan, sondern setzt mit einem neuen/aktualisierten sichtbaren Claim fort.

## Dashboard in #38

`.github/workflows/coordination-dashboard.yml` reagiert auf Issue-, Kommentar- und PR-Änderungen sowie regelmäßig per Zeitplan. Es erzeugt genau einen markierten Dashboard-Kommentar in #38 und zeigt unter anderem:

- aktive Claims mit Phase, Branch, Keys und verknüpften PRs;
- doppelte Branch-Reservierungen;
- gemeinsame Coordination keys;
- Dateiüberschneidungen zwischen offenen PRs;
- veraltete Claims und Claims mit unvollständigen Metadaten.

Öffentliche Issue-/PR-Texte werden vor dem Einbetten in den privilegierten Dashboard-Kommentar escaped. Nur Claims/Handoffs vertrauenswürdiger Repository-Mitglieder werden als Steuerdaten gewertet.

## Was dieses System ausdrücklich nicht tut

Es verteilt keine Aufgaben automatisch, entscheidet nicht fachlich über Prioritäten und sperrt Dateien nicht pessimistisch. Selbstorganisation entsteht dadurch, dass alle Worker denselben aktuellen Zustand sehen, kleine Bereiche explizit claimen, Kollisionen früh erkennen und Übergaben maschinenlesbar dokumentieren.
