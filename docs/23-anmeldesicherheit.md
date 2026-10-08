# Anmeldesicherheit und Wiederherstellung

E-Mail-Code bleibt der Standard für alle Konten einschließlich Administration. Optional kann jede Person in einer frisch vollständig bestätigten Sitzung und mit aktuellem Passwort TOTP einrichten. Der neue Faktor wird erst nach einem gültigen Code aktiviert. Geheimnisse sind mit dem hosteigenen `DATA_ENCRYPTION_KEY` verschlüsselt. Der öffentliche Dienst erhält keine Faktoren; interner und geschützter Arbeitsplatz verwalten eigene Faktoren für ihren jeweiligen Origin.

TOTP akzeptiert ein begrenztes Zeitfenster, aber jeden Zähler nur einmal. Rate-Limits schützen Konto und Clientadresse. Bei aktiviertem TOTP fällt die Passwortanmeldung nicht automatisch auf E-Mail zurück. Einmalige, getrennt aufzubewahrende Wiederherstellungscodes sind nur beim Erzeugen sichtbar und gehasht gespeichert. Sie ersetzen zusammen mit dem Passwort den zweiten Faktor. Faktorenwechsel brauchen zusätzlich den aktuell gewählten Faktor oder einen Wiederherstellungscode. Änderungen erhöhen die Faktorversion und beenden andere Sitzungen. Sicherheitsänderungen werden auditiert und neutral per E-Mail gemeldet.

Die Einrichtung gilt fünf Minuten; verlorene Codes/Authenticator erfordern den dokumentierten administrativen Wiederherstellungsweg. Ein verlorener Datenverschlüsselungsschlüssel kann nicht aus dem Datenbankbackup rekonstruiert werden.
