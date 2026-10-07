# Live-Sitzung und Führerschaft

Sitzungsdienst aktiviert eine eingeladene Sitzung für genau einen führenden Dienst. Interne Führung erlaubt Bearbeitung im internen Netz/VPN; externe Führung erlaubt Schriftführung/Vorsitz auf dem geschützten Server. Öffentliche Dienste besitzen keine Live-Schreibwege. Bei externer Führung ist vor Beginn die erfolgreiche Bereitstellung zu prüfen. Die interne Sitzung kann währenddessen nicht gleichzeitig geführt werden.

Es gibt eine aktive Schriftführung mit geräte-/kontextgebundener Sitzungshoheit, Epoche und kurzer Verlängerung. Vorsitz kann mit Begründung übernehmen; die vorherige Epoche verliert Schreibrecht. Ein verlorener Heartbeat beendet zentrale Schreibberechtigung. Ungesicherte Texte bleiben im Formular, dürfen aber nicht ungeprüft einen geänderten zentralen Stand überschreiben. Ein Browser mit mehreren Tabs teilt die Gerätekennung; die Versionsprüfung verhindert verlorene Änderungen zwischen Tabs.

Besetzung wird für den Sitzungstag aus Mandaten vorbereitet. Teilnehmende melden sich nicht selbst an. Eintritt/Austritt erhält fachliche Uhrzeit und aktuellen TOP-Bezug; Befangenheit wird separat je TOP mit Feststellung/Grund dokumentiert. Vertretung zählt nicht zusätzlich, wenn das vertretene stimmberechtigte Mandat anwesend ist. Die Schriftführung erfasst Feststellungen des Vorsitzes; Berechnungen sind Hinweise, keine rechtliche Entscheidung.

Beschlussfähigkeitsprofile sind ausdrücklich konfiguriert: Mehrheit der gesetzlichen Zahl, Mehrheit nach dokumentierten Ausschlüssen, Wiederholungsmindestzahl oder manuelle Feststellung. Sondervoraussetzungen sind vor Aktivierung fachlich zu prüfen. Ereignisse, Anträge und Protokolltexte werden unveränderlich historisiert; Korrekturen erfolgen als neue Ereignisse. Wiederholung derselben Ereignis-ID mit gleichem Inhalt ist idempotent, anderer Inhalt wird abgewiesen.

## Kontrollierte Rückgabe

Der externe führende Dienst legt eine abgeschlossene Sitzung als feste Rückgabe vor und friert sie ein. Der interne Worker holt diese über seinen bestehenden signierten HTTPS-Kanal ab; Eingang allein verändert keine Fachakte. Schriftführung/Sitzungsdienst prüft das vollständige Journal und genehmigt die Rückgabe mit Grund. Führerschaft und Aktivierungsbasis müssen unverändert sein. Fremde Sitzungsreferenzen und widersprechende unveränderliche Ereignisse/Stimmen werden abgewiesen. Aktuelle Rechte der Ereignisakteure werden bei Genehmigung erneut geprüft. Danach ist der interne Dienst führend und überträgt den genehmigten Stand. Bis zu dieser Übertragung bleibt die externe Sitzung eingefroren. Bei Rechteentzug ist manuelle fachliche Klärung erforderlich, kein ungeprüftes Wiederherstellen früherer Rechte.

Interne Live-Sitzungen übertragen das Journal als geschützte Lesekopie; öffentliche Dienste erhalten es nicht. Offene Abstimmungen werden auch bei Pause, TOP-Wechsel und neuer Besetzung abgebrochen.
