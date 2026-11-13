# Abnahme und Umsetzungsreihenfolge

## Freigabeprinzip

Der gesamte bestätigte Kernumfang muss vor Produktivbetrieb fertig und praktisch geprüft sein. Keine implizite Reduktion auf einen kleinen MVP. Entwicklungsabschnitte sind intern schrittweise möglich; die verschobenen Module sind keine Livegangblocker. Es gibt noch keinen verbindlichen Termin, Aufwand oder Hardwareplan.

## Prüfszenarien

| ID | Bezug | Abnahmeszenario und erwartetes Ergebnis |
|---|---|---|
| A-01 | ORG-01–04 | VG, mehrere Gemeinden und übergreifenden Zweckverband anlegen; Baum und Mehrfachbeziehungen korrekt, ohne automatische Fremdrechte |
| A-02 | IAM-01–03 | Eine Person mit drei Rollen wechselt Kontext; nur passende Inhalte/Aktionen, Kontext stets sichtbar |
| A-03 | IAM-04–06 | Einladung, Import, E-Mail-Code, TOTP/Passkey, Wiederherstellung und Mandatsende; abgelaufene Rechte an API/Downloads/Sync wirksam |
| A-04 | IAM-07, SEC-02 | Technischer Admin kann standardmäßig keine Fachakte lesen; Notfallzugriff begründet, befristet und gemeldet |
| A-05 | VOR-01–04 | Standard-/eigene Vorlagenart mit Pflichtfeldern, Markdown, Anlagen und Finanzangaben erstellen und exportieren |
| A-06 | VOR-05 | Zwei gleichzeitige Bereitstellungen erhalten unterschiedliche richtige Jahresnummern; Rückzug verwendet keine Nummer wieder |
| A-07 | VOR-07–10 | Parallelbearbeitung, Rückgabe und Änderung nach Freigabe; keine verlorene Bearbeitung, richtige Freigaben invalidiert |
| A-08 | VOR-11 | Eine Vorlage in drei Gremien/zwei Körperschaften beraten; lokale Änderungen und Beschlüsse getrennt nachvollziehbar |
| A-09 | SIT-01–06 | Fristen, Einladung und Nachtrag durchspielen; Originalstand unverändert, richtige Empfänger und Änderungsanzeige |
| A-10 | SIT-07–09 | Mappe/Druckpaket/PDF/DOCX mit CI, langen Texten, Tabellen und Anlagen; lesbar, vollständig, keine unberechtigte Anlage |
| A-11 | PUB-01–03 | Öffentlicher TOP mit geschützter Anlage/geschwärzter Fassung; öffentlich weder Originaltext noch sensible Metadaten auffindbar |
| A-12 | LIVE-01–06 | Sitzung mit Ein-/Austritten, Befangenheit, Anträgen und Übernahme führen; Uhrzeit/TOP, aktuelle Beschlussfähigkeit und Historie stimmen |
| A-13 | LIVE-07–08 | Offene/namentliche Abstimmung mit konkurrierenden Klicks und Schließen; genau eine wirksame Stimme pro berechtigter Person |
| A-14 | LIVE-07–09 | Geheime Wahl/mehrere Wahlgänge gesondert prüfen; Teilnahme-/Stimmwerttrennung auch in Logs/Exports, korrekter Abschluss |
| A-15 | LIVE-09 | Verbindungsabbruch während digitaler Abstimmung; sichtbarer Abbruch, vollständiger manueller Neudurchlauf ohne Ergebnisvermischung |
| A-16 | LIVE-10 | Vorbereitete Sitzung offline auf Tablet bearbeiten, online abgleichen; Wiederholungen/Konflikte/entzogene Rechte korrekt behandelt |
| A-17 | PRO-01–04 | Niederschrift erzeugen, Schriftführung/Vorsitz prüfen, Einwendung in Folgesitzung berichtigen; alte Fassung erhalten |
| A-18 | BES-01–06, ANT-01 | Kenntnisnahme ohne Aufgabe, umsetzbarer Beschluss mit Aufgabe, Teilfortschritt und Bestätigung; Freigaben von Sachständen korrekt |
| A-19 | POR-01–04 | Mandatsträger-/Fraktionsdaten getrennt; Bürger ohne Konto findet nur veröffentlichte Inhalte und erlaubte Personendaten |
| A-20 | POR-05, INT-03 | Zwei Portaldomains mit eigener CI und gemeinsamer Körperschaft; iframe nur von erlaubter Domain, geschützte Ansichten nicht einbettbar |
| A-21 | POR-06, SEC-01 | Suche/PDF-Volltext mit unterschiedlichen Rollen; keine geschützten Treffer, Titel, Snippets oder Zähler verraten |
| A-22 | INT-01–02 | SMTP-Ausfall/Neustart/Wiederholung, Kalenderlink und Export; kein Mehrfachversand durch bloße Wiederholung, Rechte und Status korrekt |
| A-23 | OPS-01, SEC-01 | Frische Einzel-/Zweiserverinstallation; nur freigegebene Netzwerkports/Dienste erreichbar |
| A-24 | OPS-02 | Lokale CA, LE-Ausstellung/-Erneuerung, fehlerhafte DNS-Einstellung und Cert-Upload; Prüfung, verständlicher Fehler und Rückweg |
| A-25 | OPS-04 | Internen Server trennen: Bürgerportal bleibt lesbar; externe Sitzung arbeitet am führenden Dienst, Sync-Verzug sichtbar |
| A-26 | OPS-04, SEC-01 | Ereignisse doppelt, verzögert, manipuliert und in falscher Reihenfolge liefern; keine doppelte Fachwirkung/Rechteausweitung |
| A-27 | OPS-05 | Beide Server aus Backup wiederherstellen, einschließlich unübertragener Sitzungsereignisse; Dateien/Rechte/Schlüssel konsistent |
| A-28 | OPS-05 | Update mit Datenmigration/Rückweg erproben; nicht nur Image zurücksetzen, keine alten Ereignisse erneut wirksam machen |
| A-29 | OPS-06 | Testdaten löschen, nach Neustart prüfen; produktive Daten erhalten, Testdateien/-einträge vollständig entfernt |
| A-30 | SEC-02 | Rechte-/Freigabe-/Notfall-/Schutzobjektzugriffe nachvollziehbar; Logs ohne Codes, Schlüssel oder geheime Stimmwerte |
| A-31 | UX-01–02 | Fachanwender erledigen Routineabläufe auf Laptop/Tablet; Hilfebedarf, Fehlhandlungen und Nacharbeit dokumentiert |
| A-32 | OPS-03–05 | Große Dateien/Exportlast/Speicherknappheit und Jobfehler; begrenzte Ressourcen, kontrollierte Fehler, Adminhinweis |

Zu jedem Szenario werden Umgebung, Version, Datenfall, Ergebnis, verantwortliche Prüfer und offene Fehler festgehalten. Automatisierte Tests für Rechte, Synchronisierung, Nummern und Abstimmungen ergänzen die fachliche Abnahme. Geheime Verfahren benötigen eine gezielte unabhängige beziehungsweise qualifizierte Sicherheitsprüfung; Ausgestaltung noch offen.

## Umsetzungsschritte: Vorschlag

1. Offene Architektur-/Rechtsfragen schließen, Bedrohungsmodell und Regelprofile definieren; Editor-/Dokumentlayout und Rollenwechsel prototypisieren.
2. Organisationen, Personen, Rechte, Anmeldung, Audit und neutrale Administration.
3. Vorlagen, Zusammenarbeit, Freigaben, Dokumentexport und Einladungsstände.
4. Veröffentlichungsprojektion, Bürger-/Mandatsträgerportale, Suche und E-Mail.
5. Live-Sitzung, führender externer Sitzungsdienst, Synchronisierung und Offlinekonflikte.
6. Digitale Abstimmungen, Wahlen und gesonderte Geheimheitsprüfung; kontrollierter manueller Ersatzweg.
7. Niederschriften, Berichtigungen, Anträge und Beschlusskontrolle.
8. Betrieb, TLS-Verwaltung, Backups/Restore, Papier-/Geräteabnahme und vollständiger Kerndurchlauf.
9. Nach Kernabschluss Aufnahme/Transkription/KI, Sitzungsgeld und weitere Schnittstellen separat entwickeln.

Rechte, Betriebssicherheit und Synchronisierung werden während aller Schritte mitgeprüft, nicht erst am Ende ergänzt. Keine Entwickleranweisung in dieser Phase legt Anwendungscode an; diese Reihenfolge ist der spätere Entwicklungsplan.

## Noch zu vereinbarende Messwerte

Maximale gleichzeitige Nutzer und Abstimmende, Dokument-/Mappegrößen, Speicherwachstum, akzeptable Lade-/Suchzeiten, Sync-Intervall, Rechtefrischegrenze, Wiederherstellungsdauer, Browsermindestversionen und Restoreprüfintervall. Keine erfundenen SLA. Das akzeptierte Backupziel beträgt zunächst ungefähr einen Arbeitstag möglichen Datenverlust.

## Voraussetzungen vor produktivem Einsatz

Alle KERN-Szenarien erfolgreich; Fachanwender bestätigen Arbeitsabläufe. RLP-Regelprofile einschließlich Geschäftsordnungen, digitale/geheime Wahlverfahren, Veröffentlichungs-/Aufbewahrungsregeln und tatsächlich geltende Barrierefreiheitsanforderungen sind geprüft. Rollen/Zuständigkeiten, Sicherungsziel, TLS-Vertrauen, SMTP, Domains, Adminmeldungen und Wiederherstellung sind eingerichtet. Verschobene Module sind deaktiviert und werden nicht als verfügbare Funktion dargestellt.


## Zusätzliche verpflichtende Nachweise: Recht, Veröffentlichung und durchgängige UX (Stand 2026-11-13)

Diese Nachweise ergänzen A-01–A-32 und **ersetzen keine fachliche Freigabe**. Die konkret anwendbaren Normen und lokalen Satzungen müssen von der zuständigen Stelle auf aktuellem Stand bestätigt werden. Verweise: #128 (Rechts-/Datenmatrix), #129 (UX-/Geräte-Audit), #124 (PDF/UA), #46 (Bürgerportal), #50 (Produktiv-Gate).

| ID | Prüfgegenstand | Positivfall | Negativfall / Freigabekriterium | Nachweis |
|---|---|---|---|---|
| A-33 | Öffentlichkeitsgrenze | Freigegebene Sitzung mit freigegebenen Dokumentfassungen sichtbar | Nichtöffentlicher TOP und nicht freigegebene Anlagen sind auch in Suche, Zählern, URLs, Cache, API, Replikat und Export unsichtbar | Rollen-/Tenant-Matrix, HTTP- und UI-Tests |
| A-34 | Veröffentlichungsentscheidung | Berechtigte Person prüft Fassung, Anlagen, Schwärzungen und erteilt dokumentierte Freigabe | Sitzungstyp allein publiziert nichts; Entzug entfernt öffentliche Suchtreffer und Downloads nachvollziehbar | Auditereignis, End-to-End-Test |
| A-35 | Personenbezug/Metadaten | Zulässige Angaben erscheinen nur in genehmigter Fassung | Vertrauliche Namen, Betreffzeilen, Dateinamen, PDF-Metadaten, Snippets und Link-Previews bleiben verborgen | Leak-Testkorpus, PDF-Inspektion |
| A-36 | Einladung/TO/Niederschrift | Zuständigkeit, Frist, Bekanntmachung, Berichtigung und Versionsstand nach lokalem Regelprofil | Kein generischer Automatismus behauptet Frist- oder Unterschriftskonformität für jede Körperschaft | Normenstand, Geschäftsordnung, Fachfreigabe |
| A-37 | Barrierefreiheit der Fachoberflächen | Kritische Aufgabe nur mit Tastatur und Screenreader erfolgreich; Status verständlich, Fokus nachvollziehbar | 200–400% Zoom, 320-CSS-px-Reflow, Fehlermeldungen, Dialoge und Touch ohne Funktionsverlust | Geräte-/AT-Matrix, manuelle Prüfung |
| A-38 | Dokumentzugänglichkeit | Einladung, Beschlussauszug, Niederschrift mit korrekter Lesereihenfolge und Semantik | Visuell schönes PDF gilt nicht als PDF/UA; fehlende Tags/Alternativtexte blockieren Freigabe | PDF-Validator und manuelle Lesereihenfolge |
| A-39 | UX je Rolle | Verwaltung, Vorsitz, Schriftführung, Ratsmitglied, Bürger und Admin erledigen mindestens fünf typische Aufgaben | Unverständliche Aktion, verlorene Suche, unbemerkte Doppelaktion und Sackgassen werden als Befund erfasst | Erfolg, Dauer, Fehlversuche, Hilfe, Abbruch |
| A-40 | Offline und Rechteentzug | Berechtigtes Mitglied erkennt Download-/Syncstatus und kann kontrolliert synchronisieren | Entzogene Berechtigung, verlorene Sitzungshoheit oder Offline-Zustand erlauben keine unbemerkte Aktion oder erneute Veröffentlichung | Geräte-/Race-/Replay-Tests |

### Nachweisprotokoll pro Testlauf

Für **jede** ID A-01–A-40 erfassen: Build/Commit, Testumgebung, Datum, Organisation/Mandant, Testrolle, Datenklasse, Eingabedaten, erwartetes Ergebnis, tatsächliches Ergebnis, Belege (Screenshot/Log ohne vertrauliche Daten), Ticket, verantwortliche prüfende Person und Entscheidung **bestanden / fehlgeschlagen / blockiert**. Ungeprüft ist nicht bestanden. Automatisierte Tests ersetzen weder juristische Prüfung noch fachliche und assistive manuelle Tests.

### Reihenfolge und Freigaberegel

1. #128: verbindliche Matrix Rechtsgrundlage → fachliche Regel → Datenklasse → Oberfläche/Export → Negativtest, einschließlich lokaler Hauptsatzung und Geschäftsordnung.
2. #129: vollständiges Inventar der Seiten, Rollen und kritischen Aufgaben, Messung mit realen Nutzenden.
3. #46/#124: Veröffentlichungsgrenzen und barrierefreie Dokumentausgabe umsetzen, anschließend A-33–A-38 wiederholen.
4. #50: Sicherheits-, Restore-, Last-, Geräte-, Rechts- und Fachabnahme konsolidieren; offene P0-Befunde sperren Produktivfreigabe.

Die experimentellen Draft-PRs #73/#74 bleiben bis zur Architekturentscheidung #44 **außerhalb** des Produktiv-Merges.
