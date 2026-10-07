# Umsetzung Etappen 1–3

Die Umsetzung erfolgt über kleine, einzeln geprüfte Pull Requests. Diese Etappen wurden gemergt; der aktuelle Auftrag wurde bis einschließlich Etappe 7 erweitert. Der aktuelle Gesamtstand steht in docs/11 und docs/20.

## Organisation und Gremien

Körperschaften und Hauptzuordnung sind intern bearbeitbar; zusätzliche Beziehungen enthalten Zeitraum und verantwortliche Stelle, ohne Zugriffsrechte zu erteilen. Stammdaten umfassen Gremien, Legislaturperioden, Funktionen, Fraktionen, Organisationseinheiten, Räume und Personen ohne Konto. Mandate unterscheiden Konto/Person, Zeitraum, Stimmrecht, Funktion, Fraktion und Stellvertretung. Frühere Amtszeiten bleiben als abgeschlossene Datensätze erhalten. Änderungen erzeugen Audit-Snapshots; konkurrierende Änderungen werden abgewiesen. Organisation und Rolle bleiben der aktive Rechtekontext.

Die einfache/erweiterte Ansicht wird pro Konto gespeichert. Erweiterte Daten bleiben wirksam. Individuelle Amtszeiten dürfen von der Legislaturperiode abweichen. Stimmrecht in einem Mandat ist noch keine Freigabe einer konkreten Abstimmung.

## Sichere Servertrennung

`EXCHANGE_SOURCE` ist die gemeinsame Installations-UUID. Geschützter und öffentlicher Kanal besitzen unterschiedliche zufällige Schlüssel (mindestens 32 Zeichen), eigene feste HTTPS-Origins und getrennte Datenbanken. Leere Konfiguration deaktiviert die Übertragung. TLS-Prüfung bleibt aktiv; für die anfängliche lokale Caddy-CA wird die CA als PEM im internen Dateivolume hinterlegt und `EXCHANGE_CA_FILE` gesetzt. Umleitungen und System-Proxys werden für Transferrequests nicht verwendet.

Organisationen werden einzeln im internen Bereich „Datenbereitstellung“ freigegeben. Geschützt werden nur externe Rollen (Mandatsträger, Vorsitz, Sitzungsdienst und Bürgermeisterfunktionen), Stammdaten und ausdrücklich vergebene Rechte bereitgestellt. Passwort-Hashes werden ausschließlich im geschützten Kanal synchronisiert, niemals Klartextpasswörter. Der geschützte Dienst wird ohne lokale Benutzerverwaltung betrieben; lokale Konten können nicht durch einen Transfer ersetzt werden. Öffentlichkeit erhält nur Namen freigegebener Körperschaften/Gremien und später ausdrücklich veröffentlichte Vorlagenfassungen. Personen, Konten, interne Beschreibungen und geschützte Anlagen werden nicht öffentlich übertragen.

Der interne Compose-Worker erzeugt periodische Vollstände, überträgt sie und holt externe Vorschläge ab. Beim ersten Start Migrationen vor Start des Workers ausführen. Zusätzlich: `docker compose run --rm backend python manage.py exchange_worker --snapshot`. Jede Übertragung ist signiert, zeitlich begrenzt, gegen Wiederholung geschützt, revisionsgebunden und atomar. Rücknahmen entfernen die öffentlichen Kopien im nächsten erfolgreichen Transfer. Übertragungsfehler bleiben sichtbar; bei mehr als 24 Stunden ohne geschützten Transfer werden externe Arbeitskontexte gesperrt. Bereits abgeflossene oder offline gespeicherte Daten lassen sich durch Entzug nicht zurückholen.

Externe Schreibvorgänge sind Vorschläge mit Ausgangsversion, Urheber und Begründung. Der interne Worker holt und quittiert sie; erst die explizite interne Prüfung übernimmt einen Vorschlag. Dabei werden aktuelle Urheberrechte und Ausgangsversion erneut geprüft. Kein extern erreichbarer Endpunkt existiert auf dem internen Fachsystem. Host-Firewall/Netzsegmentierung muss Verbindungen von extern nach intern zusätzlich verhindern; Containertrennung schützt nicht gegen eine vollständige Hostkompromittierung.

## Vorlagen: Editor und Versionen

Beschlussvorlage, Mitteilung, Antrag, Anfrage, Einwohnerfrage, Dringlichkeits-, Änderungs- und Tischvorlage stehen bereit. Texte sind kanonisches Markdown, mit formatierter Bearbeitung, Quellansicht und serverseitig bereinigter Vorschau. Tabellen, Listen, Überschriften und Fußnoten können in der Quelle geführt werden. Die formatierte Oberfläche normalisiert die Darstellung; komplexe Fußnoten bitte in der Quelle bearbeiten. Kein Laden fremder Bilder/URLs aus Text oder Export.

Jede gespeicherte Fassung enthält Texte, Zusatzfelder, Empfängerkreis und Anlagen-/Beratungsbezüge mit SHA-256. Archivfassungen sind unveränderlich. Parallele Bearbeitung wird angezeigt; beim Speichern prüft der Server die Ausgangsversion, statt Änderungen unbemerkt zu überschreiben. Konflikttexte bleiben im Formular. Vergleich zeigt Textunterschiede und vollständige archivierte Metadaten.

Anlagen werden privat unter zufälligen Dateinamen abgelegt, in Größe/Dateikennung begrenzt und zunächst als ungeprüft geführt. Downloads prüfen Rechte erneut und liefern Dateien als Download statt ausführbarer Webinhalte. Eine Kennungsprüfung ist kein Malware-Nachweis; vor Bereitstellung ist eine Inhaltsprüfung erforderlich. Virenscanner-Anbindung bleibt im Betriebs-Härtungsschritt zu konfigurieren.

## Zusammenarbeit, Prüfung und Exporte

Autor und Sitzungsdienst können Beteiligte mit konkreten eigenen vergebbaren Rechten hinzufügen. Zuweisung gilt nur für die Vorlage und den gewählten Arbeitskontext. Kommentare und Aufgaben sind versionsbezogen. Portalhinweise bleiben gespeichert; der interne Notification-Worker versendet neutrale E-Mail-Digests ohne Betreff/Inhalt vertraulicher Vorlagen. Fehler führen zu erneuten Versandversuchen. SMTP muss vor Aktivierung konfiguriert werden.

Einfacher Prüfweg: Sachbearbeitung erstellt → Fachbereichsleitung prüft → Sitzungsdienst stellt intern bereit. Erweiterte Konfiguration unterstützt Prüfgruppen (parallel innerhalb gleicher Gruppe), Feldbedingungen, Vertretungsrollen und manuell ausgewählte Prüfer. Eine laufende Prüfung erteilt genau für diesen Vorlagenstand Lesen/Prüfen, keine allgemeinen Dokumentrechte. Rückgabe erfordert Begründung. Fachliche Änderungen machen den laufenden Stand ungültig. Das optionale Vieraugenprinzip verhindert Freigabe durch den Autor sowie wiederholte Freigabe verschiedener Stufen durch dieselbe Person.

Interne Bereitstellung prüft alle Schritte und Anlagen; die Nummer wird transaktionssicher je Körperschaft/Jahr vergeben und bleibt bei späterer Änderung/Rücknahme erhalten. Veröffentlichung ist ein weiterer ausdrücklicher Schritt und verwendet die gesonderte öffentliche Textfassung und geprüften Betreff. Eine spätere Entwurfsänderung überschreibt die bereits veröffentlichte Fassung nicht.

Beratungsfolgen unterscheiden Vorberatung/Entscheidung, Reihenfolge, öffentlich/nichtöffentlich und ausdrücklich erlaubte lokale Ergänzungen. Weitere Körperschaften benötigen Zuständigkeit; lokale Ergänzungen besitzen eigenen Textstand und überschreiben die Ausgangsvorlage nicht. Verknüpfungen zu früheren Vorlagen werden nur bei Leserecht erlaubt.

PDF und DOCX werden lokal aus einer konkreten Archivfassung erzeugt. Sie enthalten Text, Überschriften, Listen, Tabellen und Anlagenverzeichnis mit Prüfsummen; keine Wordvorlagen oder extern geladenen Assets. Amtliche Gesamtsitzungsmappen folgen im Sitzungsplanungsmodul.

## Freigegebene Vorlagen außerhalb des internen Netzes

Geschützte Vorlagekopien enthalten nur intern bereitgestellte Stände und die ausdrücklich berechneten Rechte je übertragenem Arbeitskontext. Vorlagenänderungen bleiben externe Vorschläge; die interne Prüfung kontrolliert den ursprünglichen Arbeitskontext, aktuelle Rechte und die Ausgangsversion. Der geschützte Dienst besitzt keine Vorlagenadministration oder direkte Schreibverbindung ins interne System.

Dateien werden nach dem Metadatenstand separat übertragen. Der Empfänger akzeptiert nur bereits referenzierte IDs/Prüfsummen; öffentliche Dateien müssen in der konkreten veröffentlichten Archivfassung als geprüft und öffentlich vorgesehen markiert sein. Geschützte und öffentliche Dateien liegen in ihren getrennten Datenbanken. Downloads kontrollieren die aktuelle Manifestzugehörigkeit und Rechte; nicht mehr referenzierte Kopien werden beim nächsten Transfer gelöscht. Fehlende Dateien liefern keinen Ersatz oder internen Zugriff, sondern bleiben bis erfolgreicher Übertragung nicht verfügbar.
