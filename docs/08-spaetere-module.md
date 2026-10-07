# Spätere Module und Erweiterungsgrenzen

## Phasenabgrenzung

| Bereich | Status | Vor dem ersten Livegang |
|---|---|---|
| Aufnahme und geschützte Audioablage | SPÄTER | Schnittstellen/Schutzmodell dokumentieren, keine Aufnahmefunktion implementieren |
| Whisper/WhisperX und SpeechMind | SPÄTER | Adaptervertrag und Aktivierungskonzept dokumentieren |
| KI-Protokollvorschläge | SPÄTER | Trennung von Transkription, Vorschlag und fachlich bestätigtem Text vorbereiten |
| Sitzungsgeld/Entschädigungen | SPÄTER | Fachliche Datenbezüge und Exportgrenze dokumentieren |
| OParl | VORBEREITET | Zuordnung von Personen, Organisationen, Sitzungen, TOPs, Vorlagen und Dateien festhalten; noch keine vollständige Schnittstelle |
| DMS | VORBEREITET | Metadaten-/Dokumentexport und Adaptergrenze; kein bestimmtes Produkt festgelegt |
| Vollständige Barrierefreiheit | SPÄTER | Anforderungen und offene Einsatzprüfung dokumentieren |

Keine Dummy-Endpunkte oder halbfertigen Module als angeblich fertige Funktion ausliefern. Phase 1 darf ohne KI, Audio, Sitzungsgeld, GPU oder Anbieterzugang lauffähig sein. Dauerhafte Modulverträge sollen zunächst Datenverantwortung und Sicherheitsgrenzen festlegen, ohne heute schon ein beliebiges Plugin-Ausführungssystem einzubauen.

## Aufnahme und Audio

Browseraufnahme oder späterer Upload. Mikrofontest, Start/Pause/Ende, sichtbare Aufnahme und Fehlerhinweise. Erweitert Gerätewahl, Pegelanzeige, Aufnahmeabschnitte und Diagnose. Abschnittsweise lokale Sicherung/Übertragung ist gegen Langzeitsitzungen und Gerätesperren zu erproben; keine Garantie unter allen Browserzuständen.

Öffentlicher und nichtöffentlicher Teil bekommen getrennte Aufnahmeabschnitte. Beim Wechsel Aufnahme beenden und nächsten Abschnitt ausdrücklich starten. Pausen nicht aufzeichnen. TOP-Wechsel setzt Zeitmarke. Auch Audio des öffentlichen Sitzungsteils bleibt geschützt und wird niemals im Bürgerportal, OParl, öffentlichen Download oder Saalstream veröffentlicht.

Gemischte Uploads zunächst eingeschränkt behandeln; Schriftführung ordnet Sitzungsteil und Zeitbereiche zu. Original und abgeleitete Fassungen mit Herkunft/Prüfsumme verbinden. Anhören/Download eigener Berechtigung unterstellen, standardmäßig zuständige Schriftführung/Vorsitz, weitere Personen nur ausdrücklich freigeben.

Organisatorische/rechtliche Voraussetzungen der Aufnahme, Information der Beteiligten, erlaubte Fälle und Aufbewahrung vor Aktivierung prüfen. Nach Abschluss der Niederschrift Audio/Rohtranskript zur Löschung vormerken; konkrete Frist nicht vorweg festlegen. Kein Audio in allgemeinen Log-/Monitoringdaten.

## Transkription

Nach der Sitzung als Standard, sitzungsbegleitend optional. Aufnahme und Live-Schriftführung funktionieren unabhängig von Ausfall/Überlast eines Transkriptionsdienstes. Wiederholbare Jobs mit Status, Fehler, Modell-/Anbieterversion und Herkunft. Kein Dienstwechsel mit stillem Versand bereits geschützter Daten an einen neuen Empfänger.

Whisper/WhisperX selbst betrieben als möglicher Adapter, SpeechMind als ausdrücklich aktivierbarer externer Adapter. Je Organisation aktivieren; externe Verarbeitung nichtöffentlicher Inhalte gesondert erlauben. Modellbedingungen, zusätzliche Diarisierungsmodelle, Hardware, Anbieter-API und Vertragsvoraussetzungen zum Umsetzungszeitpunkt prüfen.

Zeitmarken, Suche, Klick auf Textstelle zum Anhören und korrigierbare Sprecherzuordnung. Stimmen zunächst „Sprecher 1/2 …“; Personenzuordnung fachlich bestätigen. Keine dauerhaften biometrischen Stimmprofile als Default. Fachwörterbuch mit kommunalen Begriffen konfigurierbar; Wirkung gegen echte Aufnahmen prüfen. Gleichzeitige Stimmen, schlechte Akustik und Dialekte können Fehler verursachen.

## KI-Protokollunterstützung

Transkription und Textgenerierung sind unterschiedliche Dienste. Whisper/WhisperX allein erstellen kein fachlich geprüftes Ergebnisprotokoll. Optionales Generierungsmodul nutzt Transkript, TO und erlaubte Notizen für Vorschläge, mit nachvollziehbaren Text-/Zeitbezügen. Strukturierte bestätigte Anwesenheit, Beschlüsse und Abstimmungsergebnisse haben Vorrang und werden nicht überschrieben.

Automatischer Inhalt bleibt ungeprüfter Entwurf. Übernahme, Bearbeitung und Prüfung protokollieren; keine direkte Veröffentlichung oder automatische Beschlussfassung. Transkript-/Dokumentinhalte als Daten behandeln, nicht als ausführbare Anweisungen für Werkzeuge. Keine ungeprüften externen Aktionen durch ein KI-Modul.

## Sitzungsgeld

Spätere eigenständige Umsetzung. Offen halten: Sitzungsgeld, Pauschalen, Fahrtkosten, Verdienstausfall, weitere Entschädigungen, Sätze je Körperschaft/Funktion/Zeitraum, komplexe Bedingungen, Korrekturen und Jahresübersichten. Datenbasis: historische Mandate, Funktionen und Anwesenheitszeiten, nicht nur aktueller Personenstand.

Berechnung → fachliche Prüfung → Freigabe → Export an Finanzverfahren. Individuelle PDF-Abrechnung im geschützten Portal erst nach Implementierung dieses Moduls. Bank-/Steuer-/Abrechnungsdaten separat berechtigen, niemals öffentlich. Keine automatische Auszahlung aus dem Kern und kein konkretes Finanzprodukt bereits festgelegt.

## OParl, DMS und APIs

OParl erhält ausschließlich ausdrücklich veröffentlichte Daten. Stabile IDs/Links, Organisationen, Gremien, Besetzungen, Personen, Sitzungen, TO, Vorlagen und Dateien sind schon im Datenmodell zuzuordnen. Spezifikationsversion und vollständige Prüfungen erst vor Implementierung festlegen. „Vorbereitet“ ist keine OParl-Konformitätsbehauptung.

DMS-Adapter dokumentiert Versionen, Metadaten, Aktenbezug, Exportquittung und Wiederholung. Norm-/Produktspezifikationen, etwa DokuFIS, sind später gesondert zu prüfen. Allgemeine APIs erhalten versionierte Verträge, Dienstrechte und Audit; keine allgemeine Vollzugriffs-API als Nebenprodukt der Erweiterbarkeit.
