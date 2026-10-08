# Bürgerportal und Integrationsvertrag

Der öffentliche Dienst bietet Volltextsuche in veröffentlichten Titeln und Markdown, Filter nach Körperschaft, Gremium, Art und lokalem Sitzungstag, paginierte Ergebnisse, sichere Markdown-Detailansichten und einen ICS-Kalender. Es werden ausschließlich `PublicRecord` und freigegebene Anlagen gelesen. Eine zurückgenommene Veröffentlichung verschwindet beim nächsten erfolgreichen internen Abgleich aus Suche und Export. Private Originaltitel, Protokollentwürfe und Audio gelangen nicht in diesen Vertrag. PDF-Anlagen werden zunächst nicht als eigener Volltextindex verarbeitet.

`GET /api/v1/veroeffentlichungen/` ist ein versionierter, paginierter, ausschließlich lesender JSON-Vertrag mit denselben Filtern wie das Portal. Er hat keine Anmeldung und keine Schreiboperationen. Kalenderdateien umfassen höchstens 1.000 Termine pro Auswahl; engere Datumsfilter verwenden. Die API dient als Integrationsgrundlage; sie behauptet keine OParl-Konformität. OParl und DMS bleiben vorbereitete spätere Adapter, keine generische Fernzugriffsschnittstelle.

Neue Terminmetadaten enthalten ausschließlich Terminbeginn/-ende, öffentlichen Ort und Gremien-ID. Zeitangaben benötigen eine Zeitzone. Empfänger akzeptieren ältere öffentliche Stände ohne Metadaten weiterhin; diese erscheinen in der Suche, aber nicht im Kalender. Öffentliche Niederschriften sind jetzt ausdrücklich im Empfangsvertrag zugelassen.

Tests prüfen Filterkombinationen, ungültige IDs/Datumsangaben, Zeitzonen und ICS-Injection sowie die öffentliche Feldfreigabe. Die getrennten Serverrollen bleiben Bestandteil der CI.

## Eigene Portale, CI und Einbettung

Unter „Bürgerportal und CI“ verwaltet die interne Organisationsadministration Portalname, Einleitung, eine kontrastgeprüfte Hauptfarbe, exakte Domainnamen und HTTPS-Origins für iframe. In einem Portal können ausschließlich Körperschaften ausgewählt werden, für die die Person ausdrücklich eine aktuell gültige Organisationsverwaltungsrolle besitzt. Daten bleiben zentral; die Portalzuordnung ist eine Darstellung öffentlicher Daten, kein Vertraulichkeitsrecht. Unzugeordnete erlaubte Hosts zeigen das gemeinsame Portal.

Domainzuordnung im Fachsystem allein ändert weder DNS noch Caddy oder `DJANGO_ALLOWED_HOSTS`. Diese Betriebsfreigaben werden separat eingerichtet. Kein beliebiges HTML, CSS, JavaScript, SVG oder Logo-Upload. iframe gilt nur für öffentliche Übersichten/Detailseiten; Transfer-, Authentifizierungs- und geschützte Routen bleiben gesperrt. Zulässige Frame-Origins sind exakt, HTTPS und ohne Pfad/Port/Platzhalter. Für iFrames werden keine Benutzerkonten oder Drittanbieter-Cookies benötigt. Fremde Skripte und Analytics werden nicht geladen.

## Personenfreigaben

Personenprofile sind je Körperschaft verwaltet und optional einem vorhandenen Konto zugeordnet. Name, Funktion, Fraktion, Amtszeitbeginn/-ende, separat eingegebener Kontakt und Foto werden einzeln ausgewählt; zusätzlich ist die ausdrückliche Veröffentlichung erforderlich. Die Account-E-Mail wird niemals automatisch übernommen. Fotos werden lokal auf höchstens 600×600 Pixel verkleinert und als JPEG ohne Originalmetadaten gespeichert; SVG und ausführbare Bildinhalte sind nicht zugelassen. Die Veröffentlichung lässt sich ohne Löschen der internen Person widerrufen. Konto- und Mandatsrechte ändern sich dadurch nicht.
