# Bürgerportal und Integrationsvertrag

Der öffentliche Dienst bietet Volltextsuche in veröffentlichten Titeln und Markdown, Filter nach Körperschaft, Gremium, Art und lokalem Sitzungstag, paginierte Ergebnisse, sichere Markdown-Detailansichten und einen ICS-Kalender. Es werden ausschließlich `PublicRecord` und freigegebene Anlagen gelesen. Eine zurückgenommene Veröffentlichung verschwindet beim nächsten erfolgreichen internen Abgleich aus Suche und Export. Private Originaltitel, Protokollentwürfe und Audio gelangen nicht in diesen Vertrag. PDF-Anlagen werden zunächst nicht als eigener Volltextindex verarbeitet.

`GET /api/v1/veroeffentlichungen/` ist ein versionierter, paginierter, ausschließlich lesender JSON-Vertrag mit denselben Filtern wie das Portal. Er hat keine Anmeldung und keine Schreiboperationen. Kalenderdateien umfassen höchstens 1.000 Termine pro Auswahl; engere Datumsfilter verwenden. Die API dient als Integrationsgrundlage; sie behauptet keine OParl-Konformität. OParl und DMS bleiben vorbereitete spätere Adapter, keine generische Fernzugriffsschnittstelle.

Neue Terminmetadaten enthalten ausschließlich Terminbeginn/-ende, öffentlichen Ort und Gremien-ID. Zeitangaben benötigen eine Zeitzone. Empfänger akzeptieren ältere öffentliche Stände ohne Metadaten weiterhin; diese erscheinen in der Suche, aber nicht im Kalender. Öffentliche Niederschriften sind jetzt ausdrücklich im Empfangsvertrag zugelassen.

Tests prüfen Filterkombinationen, ungültige IDs/Datumsangaben, Zeitzonen und ICS-Injection sowie die öffentliche Feldfreigabe. Die getrennten Serverrollen bleiben Bestandteil der CI.
