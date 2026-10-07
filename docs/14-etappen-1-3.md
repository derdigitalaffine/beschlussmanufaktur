# Umsetzung Etappen 1–3

Die Umsetzung erfolgt über kleine, einzeln geprüfte Pull Requests. Der Gesamtauftrag bleibt bis Abschluss von Etappe 3 offen.

## Organisation und Gremien

Körperschaften und Hauptzuordnung sind intern bearbeitbar; zusätzliche Beziehungen enthalten Zeitraum und verantwortliche Stelle, ohne Zugriffsrechte zu erteilen. Stammdaten umfassen Gremien, Legislaturperioden, Funktionen, Fraktionen, Organisationseinheiten, Räume und Personen ohne Konto. Mandate unterscheiden Konto/Person, Zeitraum, Stimmrecht, Funktion, Fraktion und Stellvertretung. Frühere Amtszeiten bleiben als abgeschlossene Datensätze erhalten. Änderungen erzeugen Audit-Snapshots; konkurrierende Änderungen werden abgewiesen. Organisation und Rolle bleiben der aktive Rechtekontext.

Die einfache/erweiterte Ansicht wird pro Konto gespeichert. Erweiterte Daten bleiben wirksam. Individuelle Amtszeiten dürfen von der Legislaturperiode abweichen. Stimmrecht in einem Mandat ist noch keine Freigabe einer konkreten Abstimmung.

## Sichere Servertrennung

`EXCHANGE_SOURCE` ist die gemeinsame Installations-UUID. Geschützter und öffentlicher Kanal besitzen unterschiedliche zufällige Schlüssel (mindestens 32 Zeichen), eigene feste HTTPS-Origins und getrennte Datenbanken. Leere Konfiguration deaktiviert die Übertragung. TLS-Prüfung bleibt aktiv; für die anfängliche lokale Caddy-CA wird die CA als PEM im internen Dateivolume hinterlegt und `EXCHANGE_CA_FILE` gesetzt. Umleitungen und System-Proxys werden für Transferrequests nicht verwendet.

Organisationen werden einzeln im internen Bereich „Datenbereitstellung“ freigegeben. Geschützt werden nur externe Rollen (Mandatsträger, Vorsitz, Sitzungsdienst und Bürgermeisterfunktionen), Stammdaten und ausdrücklich vergebene Rechte bereitgestellt. Passwort-Hashes werden ausschließlich im geschützten Kanal synchronisiert, niemals Klartextpasswörter. Der geschützte Dienst wird ohne lokale Benutzerverwaltung betrieben; lokale Konten können nicht durch einen Transfer ersetzt werden. Öffentlichkeit erhält nur Namen freigegebener Körperschaften/Gremien und später ausdrücklich veröffentlichte Vorlagenfassungen. Personen, Konten, interne Beschreibungen und geschützte Anlagen werden nicht öffentlich übertragen.

Der interne Compose-Worker erzeugt periodische Vollstände, überträgt sie und holt externe Vorschläge ab. Beim ersten Start Migrationen vor Start des Workers ausführen. Zusätzlich: `docker compose run --rm backend python manage.py exchange_worker --snapshot`. Jede Übertragung ist signiert, zeitlich begrenzt, gegen Wiederholung geschützt, revisionsgebunden und atomar. Rücknahmen entfernen die öffentlichen Kopien im nächsten erfolgreichen Transfer. Übertragungsfehler bleiben sichtbar; bei mehr als 24 Stunden ohne geschützten Transfer werden externe Arbeitskontexte gesperrt. Bereits abgeflossene oder offline gespeicherte Daten lassen sich durch Entzug nicht zurückholen.

Externe Schreibvorgänge sind Vorschläge mit Ausgangsversion, Urheber und Begründung. Der interne Worker holt und quittiert sie; erst die explizite interne Prüfung übernimmt einen Vorschlag. Dabei werden aktuelle Urheberrechte und Ausgangsversion erneut geprüft. Kein extern erreichbarer Endpunkt existiert auf dem internen Fachsystem. Host-Firewall/Netzsegmentierung muss Verbindungen von extern nach intern zusätzlich verhindern; Containertrennung schützt nicht gegen eine vollständige Hostkompromittierung.
