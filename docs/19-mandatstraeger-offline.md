# Persönlicher Arbeitsbereich und Offline

Der Arbeitsbereich zeigt nur im ausdrücklich gewählten Kontext freigegebene Sitzungen und Vorlagen. Suche, Favoriten und zuletzt geöffnete Vorgänge werden erst nach aktueller Berechtigungsprüfung dargestellt. Persönliche Notizen sind nach Konto, Arbeitskontext und Sitzung getrennt. Auch Schriftführung, Vorsitz und technische Admins erhalten über die Anwendung keinen Zugriff auf fremde persönliche Notizen. Notizen werden weder in öffentliche Projektionen noch in Sitzungsrückgaben übernommen. Sie sind keine Protokolltexte. Gleichzeitige Notizänderungen erzeugen einen sichtbaren Versionskonflikt.

Offline-Mappen und Offline-Schriftführung werden im nächsten separaten PR ergänzt.

## Abgleichvertrag für Offline-Schriftführung

Die Vorbereitung wird ausdrücklich online angefordert und erhält eine signierte, konto-/kontext-/sitzungs-/gerätegebundene Freigabe für maximal sieben Tage, begrenzt durch das Rollenende. Offline kann die Oberfläche bereits gespeicherte Unterlagen anzeigen und Ereignisse vorbereiten; sie verlängert keine Serverrechte. Abgleich ist eine ausdrückliche Aktion nach erneutem Anmelden im passenden Kontext. Aktuelle Fachrechte, führender Dienst, Zentralversion und ursprüngliche Sitzungsepoche müssen passen. Eine abgelaufene Sitzungshoheit darf nur bei unverändertem Stand/gleicher Epoche erneut übernommen werden. Übernahme durch Vorsitz oder andere Änderungen führen zu einem sichtbaren Konflikt. Kein automatisches Zusammenführen.

Ereignisse werden als ganzer Stapel atomar geprüft und übernommen. Ein Fehler lässt alle zentralen Daten unverändert. Feste Stapel- und Ereignis-IDs verhindern doppelte Wirkung bei erneuter Übermittlung. Lokale fachliche Zeitpunkte bleiben erhalten. Digitale Stimmen, Veröffentlichungen und Niederschriftsfreigaben sind vom Offline-Abgleich ausgeschlossen. Persönliche Notizen verwenden einen eigenen versionsgeprüften Weg; fremde Konten und Kontexte werden abgewiesen.
