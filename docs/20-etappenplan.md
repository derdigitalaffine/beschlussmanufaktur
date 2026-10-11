# Implementierungsfolge

Der aktuelle Arbeitsauftrag umfasst die Entwicklungsfunktionen bis einschließlich Etappe 10. Die Produktivabnahme in Etappe 11 folgt separat. Kleine Branches/PRs werden nach erfolgreichen relevanten Prüfungen gemergt. Entwicklungsstand bedeutet keine fachliche oder rechtliche Produktivabnahme; verbleibende Teilanforderungen werden ausdrücklich ausgewiesen.

Diese Etappentabelle bleibt die historische/fachliche Grobfolge. Die **aktuelle Priorisierung** der offenen Arbeit wird ab jetzt dynamisch über `docs/22-dynamische-roadmap.md` und das Portfolio-Issue #41 geführt. Damit können UX-, Security-, Architektur- oder Betriebsrisiken die Reihenfolge begründet verändern, ohne die bestätigten KERN-Anforderungen zu reduzieren.

| Etappe | Umfang | Stand |
|---|---|---|
| 1 | Organisationsstruktur, Stammdaten, Mandate und ausdrückliche Kontextrechte | Implementiert; PRs 3–4 |
| 2 | Getrennte Dienste, geschützte Provisionierung und signierter intern initiierter Austausch | Implementiert; PR 5 und modulbezogene Ergänzungen |
| 3 | Vorlagen, Markdown-Editor, Zusammenarbeit, Freigaben, Fassungen und PDF/DOCX | Implementiert; PRs 6–8 |
| 4 | Sitzungsplanung, Tagesordnung, Einladungen, kontrollierte Nachträge und PDF-Gesamtmappen | Implementiert; PRs 9–11 |
| 5 | Führender Sitzungsdienst, Live-Schriftführung, Anwesenheit/Befangenheit, Abstimmungen, Rückgabe | Implementiert für namentlich digital und Papier; PRs 12–14. Digitale geheime Verfahren bleiben offen |
| 6 | Niederschriften, getrennte Prüfung, Berichtigung, Veröffentlichung und Beschlusskontrolle | Implementiert; PRs 15–16 |
| 7 | Persönlicher Arbeitsbereich, Notizen, Favoriten, verschlüsselte Offline-Mappen und geprüfte Offline-Schriftführung | Implementiert; PRs 17–19, abschließendes Review in PRs 20–23 |
| 8 | Ausbau Bürgerportal: Suche/Kalender, Domain/CI, iframe und Integrationsgrenzen | Offen; als Roadmap-Outcome zu schneiden und mit UX-/Security-Gates zu validieren |
| 9 | Weitergehende Administration/CI, konfigurierbare Komfort- und Importfunktionen | Offen; mit Identitäts-/Rechte-UX und sicherem Recovery zu koordinieren |
| 10 | TLS-/Domainverwaltung, TOTP/Passkeys, Notfallzugriff, Betriebs-/Backupfunktionen | Offen; Security- und Restore-Gates sind vor Freigabe nachzuweisen |
| 11 | Vollständiger Kern-/Geräte-/Rechts-/Sicherheits-/Restore- und Lasttest, Freigabereife | Offen; `release-gate` im dynamischen Portfolio |

## Qualitätsorientierte Restreihenfolge

Die offene Arbeit wird nicht mehr allein nach Modulnummer abgearbeitet. Als Startpunkt gilt:

1. **NOW:** UX-/Designsystem und repräsentative Nutzerreisen, Frontend-Architekturentscheidung per Prototyp sowie Security-Baseline/Threat Model.
2. **NEXT:** Bürgerportal/CI/Suche, sichere Identität/Admin-Komfortfunktionen und Betrieb/Backup/Restore.
3. **LATER:** digitale geheime Verfahren erst nach fachlicher/rechtlicher Klärung, Protokollentwurf und unabhängiger Sicherheitsprüfung.
4. **RELEASE GATE:** vollständige Fachanwender-, Geräte-, Accessibility-, Last-, Zweiserver-, Restore- und Security-Abnahme.

Die konkreten Issues, Prioritäten, Risiken, Abhängigkeiten und offenen Entscheidungsfragen sind in #41 maßgeblich. Der Hauptagent darf die Reihenfolge ändern, muss die Begründung und betroffenen Abhängigkeiten dort sichtbar halten.

Aufnahme/Transkription/KI und Sitzungsgeld folgen separat nach Abschluss des übrigen Kerns. Die Details der noch offenen Etappen werden vor deren Umsetzung in kleine prüfbare PRs zerlegt; diese Tabelle ist der grobe Plan, kein Terminversprechen.
