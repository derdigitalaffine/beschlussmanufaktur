# Konten und Rollen bedienen

Stand 0.7. Benutzerverwaltung und Einladungen stehen im internen Fachsystem zur Verfügung. Geschützter externer Dienst und Bürgerportal haben keine Benutzerverwaltungs- oder Einladungsrouten. Der interne Worker provisioniert Konten und explizite Rollen geschützt; öffentliche Dienste erhalten keine Konten. Konfiguration: docs/12 und docs/14.

## Einladen

Als Organisationsverwaltung im Arbeitsplatz die passende Organisation/Rolle wählen, dann „Menschen und Rollen“ öffnen. E-Mail-Adresse, Rolle und optional Beginn/Ende eingeben. Ohne Beginn gilt die Rolle ab Annahme sofort; bei geplantem Beginn erst ab diesem Zeitpunkt. Die Einladung ist sieben Tage verwendbar und erzeugt noch kein Konto oder Zugriffsrecht. Ein Versandfehler hinterlässt keine gültige Einladung.

Link oder Einladungscode vertraulich behandeln. Neue Personen legen Vor-/Nachname und ein eigenes gültiges Passwort fest und melden sich anschließend mit Passwort und E-Mail-Code an. Bestehende Konten melden sich zur Annahme an; ihr Passwort, Name und ihre Rollen anderer Organisationen werden nicht verändert. Keine freie Selbstregistrierung und keine administrativ versendeten Klartextpasswörter.

Einladungen haben nur Rechte in der Organisation, aus der sie versendet wurden. Zusätzliche Rollen benötigen weitere Einladungen. Die gleiche bereits zugewiesene, noch nicht beendete Rolle kann nicht parallel erneut vergeben werden. Stattdessen vorhandene Zuweisung bearbeiten. Endgültig entzogene Rollen werden nicht reaktiviert: neue Einladung verwenden.

Der Link transportiert sein Geheimnis im URL-Fragment. Das kleine lokale Skript entfernt das Fragment aus der Adresszeile und übergibt den Code per CSRF-geschütztem POST. Ohne JavaScript den Code aus der Mail in das Eingabefeld kopieren. Nur ein HMAC-Digest wird dauerhaft gespeichert; Geheimnisse stehen weder im Audit noch in normalen Anfragepfaden. Dritte Mail-/Browserprogramme können den Link trotzdem kennen; er ist kein öffentlich teilbarer Link.

Bei Annahme werden Ablauf, Rücknahme und weiterhin bestehende Organisationsverwaltungsberechtigung des Einladenden erneut geprüft. Entfällt dessen Berechtigung, kann die alte Einladung nicht angenommen werden. Eine andere zuständige Administration muss sie neu versenden.

## Rollen verwalten

Die Übersicht zeigt ausschließlich Personen mit Zuweisung in der aktiven Organisation sowie deren letzte 20 Einladungen. Suche bleibt auf diesen Bereich begrenzt. Bearbeiten erlaubt Rolle und Gültigkeitszeitraum mit Begründung. Vergangene oder zukünftige Zuweisungen sind als solche erkennbar. Der Zugriff prüft Zeitgrenzen unmittelbar bei jeder Anfrage, ohne erst einen Hintergrundjob abzuwarten.

Konkurrierende Rollenänderungen werden über die Organisationssperre und einen Versionsstand kontrolliert. Bei veraltetem Formular neu laden, aktuellen Stand prüfen und erst dann erneut bearbeiten. Audit speichert Urheber, Grund und Vorher-/Nachherstand; es ist im aktuellen Stand noch keine vollständige Audit-Weboberfläche vorhanden.

„Zugriff entziehen“ verlangt Bestätigung mit Begründung. Nur diese Zuweisung wird entzogen; Konto und andere Organisationsrollen bleiben erhalten. Bestehende Sitzungen verlieren die entsprechenden Verwaltungsrechte bei der nächsten Anfrage. Eine offene Einladung lässt sich ebenfalls begründet zurückziehen.

Die letzte momentan aktive Organisationsverwaltung darf nicht entfernt oder auf eine andere Rolle umgestellt werden. Zuerst eine weitere aktive Verwaltung zuweisen. Dieser Schutz ersetzt keine Planung für zukünftige Ablaufdaten: sicherstellen, dass auch nach befristeten Amtszeiten eine zuständige Verwaltung vorhanden ist. Technische Superuser erhalten durch ihren Superuserstatus weiterhin keine Fachrechte.

## Grenzen

Noch kein Import, keine Selbstverwaltung von E-Mail-Adressen, keine Passwortwiederherstellung, TOTP/Passkeys oder frei konfigurierbaren Einzelrechte. Neue Konten entstehen bei Annahme, nicht durch ein separates Adminformular. Einladung muss im internen Netz beziehungsweise über das außerhalb der Anwendung betriebene VPN erreichbar sein. Für externe Mandatsträgerprovisionierung wird später ein eigener abgestimmter Ablauf ergänzt.
