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
