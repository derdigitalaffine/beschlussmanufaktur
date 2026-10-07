# Betrieb, Einrichtung und Aufbewahrung

Dieses Dokument beschreibt Anforderungen an die spätere Betriebsimplementierung, keine ausführbare Installationsanleitung. Es enthält bewusst keine Compose-Datei, Caddy-Konfiguration oder Shellskripte.

## Docker-Compose-Ziel

Profile für Einzelserver, internen und externen Server. Enthalten sein müssen die jeweiligen Backend-/Frontenddienste, Caddy, Datenbanken, Hintergrundprozesse und alle verpflichtenden Kernabhängigkeiten. Audio/KI/Abrechnung kommen später als separate optionale Pakete. Daten und Schlüssel leben in persistenten Volumes; temporäre Containerverluste dürfen sie nicht entfernen.

Dokumentierte Imageversionen, Gesundheitsprüfungen, Ressourcen-/Uploadgrenzen, Protokollierung und kontrollierte Start-/Wiederanlaufreihenfolge. Keine Standardpasswörter und kein dauerhaft öffentlich offener Einrichtungsmodus. Frisches Setup benötigt einen einmaligen abgesicherten Bootstrap, lokale Administration, Organisationseinrichtung, Domain-/TLS-Wahl, SMTP und Sicherungsziel.

Einrichtungsablauf: Repository/Release beziehen, geringe Zahl von Betriebsparametern setzen, Compose starten, im Browser geführt fertigstellen. Ohne öffentliche Vertrauenskette wird die Installation zunächst über vertrauenswürdig eingebundene lokale CA erreicht. Einrichtungsfehler müssen korrigierbar sein, ohne Daten zurückzusetzen.

## Testdaten

Wenige neutrale, künstliche Datensätze im Defaultsystem, eindeutig durch Herkunftsmarkierung und IDs gekennzeichnet. Keine echten Namen, Kundendaten oder fest eingebauten Gemeindelogos. Keine getrennte Demoanwendung.

Adminaktion „Testdaten löschen“ zeigt den Umfang und entfernt ausschließlich markierte Datensätze und deren Dateien/Abhängigkeiten. Verbindungen zu inzwischen produktiv genutzten Objekten werden geprüft; Konflikte verständlich auflösen statt produktive Daten mitzunehmen. Nach Entfernung keine erneute automatische Erzeugung beim Neustart/Update. Kein öffentliches Test-Administratorkonto.

## Caddy und TLS

Bestätigte Modi: lokale Caddy-CA zur Erstinbetriebnahme, Let's Encrypt nach administrativer Umstellung, hochgeladenes Zertifikat. Caddys interne CA besitzt eine selbstsignierte Wurzel und stellt signierte Serverzertifikate aus. Das ist präziser als pauschal „selfsigned Serverzertifikat“. Clients müssen der Wurzel vertrauen; ein Containerstart installiert dieses Vertrauen nicht automatisch auf Windows, Linux, iPad oder Telefon. Die Einrichtung dokumentiert diese Grenze ausdrücklich.

| Verwaltungsfunktion | Erwartetes Verhalten |
|---|---|
| Domain hinzufügen | Syntax, erlaubten Bereich, DNS-Auflösung und Erreichbarkeit prüfen; kein beliebiger Proxy zu internen Zielen |
| DNS prüfen | A/AAAA, Zielzuordnung, relevante CAA- und Challengeinformationen nach Modus prüfen; Split-DNS verständlich anzeigen |
| Let's Encrypt | Domainkontrolle über unterstützten ACME-Weg, Ausstellung und automatische Erneuerung |
| DNS-01 | Unterstützten Provideradapter und minimale DNS-Zugangsdaten konfigurieren; Challenge/Propagation prüfen |
| Zertifikat hochladen | PEM-Zertifikat, Kette und Schlüssel passend prüfen; Namen, Laufzeit und sichere Ablage |
| Status | Modus, Domains, Aussteller, Ablauf, letzte Prüfung/Erneuerung, verständlicher Fehler |
| Änderung anwenden | Vorschau/Validierung, kontrollierter Reload, Erreichbarkeitsprüfung und Rückweg |

Automatische Prüfung vorhandener DNS-Einstellungen ist nicht DNS-01. DNS-01 benötigt veränderbare Challenge-TXT-Einträge beziehungsweise Delegation und einen passenden Caddy-Provideradapter. HTTP-/TLS-Challenges brauchen dagegen ihren jeweiligen erreichbaren öffentlichen Port. Unterstützte Providerliste und DNS-01 als Standard gegenüber alternativem ACME-Verfahren sind noch offen.

Eigene Domain und administrierbare Einstellungen ersetzen die Mitwirkung des Domaininhabers nicht. Hochgeladene Zertifikate werden nicht automatisch durch Caddy erneuert; Ablaufwarnung und Ersatzablauf vorsehen. Keine Freigabe beliebiger On-Demand-Domains. Private Schlüssel nur mit restriktiven Rechten, nie per E-Mail verschicken. Caddy-Adminschnittstelle ausschließlich privat; ein begrenzter Betriebsagent setzt erlaubte Änderungen um.

Let's-Encrypt-Staging kann zur Ausstellungserprobung verwendet werden; das ist keine permanente fachliche Testinstallation. Bei fehlerhafter Umstellung darf die Administration sich nicht selbst aussperren; alter vertrauenswürdiger Zugang oder dokumentierter lokaler Rückweg bleibt verfügbar.

## E-Mail

Vorhandenes SMTP/IMAP, ein gemeinsamer Absender. SMTP mit TLS/Zertifikatsprüfung, Zugangsdaten geschützt. Testversand, dauerhafte Outbox, begrenzte Wiederholungen, Versandstatus und Fehlermeldungen an die Admingruppe. Versand von Anmeldecodes priorisiert gegenüber Masseneinladungen; keine Codes/Inhalte in Diagnosemails.

IMAP ist als vorhandene Anbindung genannt. Ob nur Rückläufer/Zustellprobleme oder auch fachliche Antworten importiert werden sollen, ist noch offen. Keine automatische Übernahme eingehender E-Mail als freigegebener Beschluss/Vorlage. Import benötigt Zuordnung, Größen-/Anlagenprüfung und Bearbeitungsstatus. Browser-Push entfällt.

## Sicherung und Wiederherstellung

Bestätigte Ausgangswerte: tägliche Sicherung, zusätzliche Sicherung vor jedem Update, 14 Tagesstände, 8 Wochenstände, 12 Monatsstände. Verschlüsselt auf getrenntem Sicherungsziel. Bis zu ungefähr einem Arbeitstag Datenverlust bei schwerem Ausfall ist zunächst akzeptiert; keine Hochverfügbarkeitszusage.

Sichern: konsistente Datenbank-/Dateistände, Konfiguration, notwendige Schlüssel, Caddy-/ACME-Zustand und Metadaten für Wiederherstellung. Beide Server einschließlich externer noch nicht intern übernommener Sitzungsereignisse berücksichtigen. Öffentliche Projektionen sind rekonstruierbar, externe unübertragene Fachereignisse nicht zwangsläufig.

Zeitplan/Ziel durch Administration einstellen, Fehlversuche melden, Vollständigkeit/Alter im Dashboard zeigen. Schlüsselwiederherstellung getrennt dokumentieren: verschlüsselte Sicherung ohne verfügbaren Schlüssel ist unbrauchbar. Backups enthalten selbst vertrauliche Daten und erhalten entsprechende Zugriffs-/Löschregeln.

Vor Livegang vollständige Wiederherstellung praktisch prüfen; danach regelmäßig, Intervall noch festzulegen. Dafür ist eine zeitweise isolierte Umgebung zulässig und notwendig, ohne permanente Testinstallation. Export einer Körperschaft dient Portabilität und ersetzt kein Systembackup. Ein isolierter Import darf fremde Referenzen oder Rechte nicht ungeprüft übernehmen.

## Updates

Bewusst administrativ starten, Version/Migrationshinweise prüfen, konsistent sichern, erforderlichen Wartungszustand herstellen, Dienste aktualisieren und kritische Wege prüfen. Laufende Sitzungen nicht ungeplant unterbrechen. Rückweg beschreibt Anwendung, Datenbank, Dateiformate und Synchronisierung; altes Image allein ist bei veränderter Datenbank kein vollständiger Rollback.

Keine automatische Aktualisierung auf ungeprüfte neueste Images. Keine permanente Testinstallation gewünscht. Entwicklerseitige automatisierte Prüfungen, Releaseprüfung und temporäre Restoretests bleiben bestehen. Gleichzeitige Versionswechsel der Server brauchen kompatible API-/Ereignisschemata oder einen kontrollierten gemeinsamen Wartungsablauf.

## Betriebskontrolle

Adminbereich zeigt Dienstgesundheit, Mail/Exportjobs, Sync-Verzug, Speicher, Sicherungsalter und Zertifikate. Kritische Fehler per E-Mail an konfigurierbare Admingruppe. Kein verpflichtender externer Monitoringanbieter, keine Telemetrie/externen Analyseskripte. Betriebslogs enthalten möglichst wenig personenbezogenen Fachinhalt; Auditdaten getrennt und mit eigenen Zugriffsrechten.

Internet ist für Images, Updates, Zertifikate und später Modelle erlaubt. Der Kern benötigt keine externe KI oder kostenpflichtige Pflichtdienste. SMTP, DNS und Zertifikatsdienste sind bewusst konfigurierte Betriebsabhängigkeiten. Kein impliziter VPN-Betrieb durch die Anwendung.

## Aufbewahrung, Löschung und Archive

Freigegebene Vorlagen, Beschlüsse und Niederschriften werden nicht pauschal automatisch gelöscht. Organisationen konfigurieren Aufbewahrungsregeln, Archivexport, Sperrvermerke und kontrollierte Löschverfahren. Arbeitsdaten, persönliche Notizen, Fraktionsdokumente, Benachrichtigungen und später Audio/Transkripte erhalten eigene Regeln.

Fristablauf erzeugt zunächst einen prüfbaren Löschvorschlag. Vorschau umfasst Daten, Dateien, Suchindex, Exporte, externe Projektionen und Referenzen. Löschung erfordert Berechtigung und protokolliert den Vorgang ohne den gelöschten Inhalt erneut dauerhaft zu speichern. Backupstände werden nicht still nachträglich umgeschrieben; dokumentierter Ablauf verhindert Wiederbelebung gelöschter Veröffentlichungen nach Restore.

Konkrete fachlich/rechtlich zulässige Fristen sind offen. Normale tägliche Backups ersetzen keine rechtlich geprüfte Langzeitarchivierung. Rechtliche Freigabe, Archivformate und Zuständigkeiten bleiben vor Einsatz zu bestimmen.
