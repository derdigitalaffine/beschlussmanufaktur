# Anmeldesicherheit und Wiederherstellung

E-Mail-Code bleibt der Standard für alle Konten einschließlich Administration. Optional kann jede Person in einer frisch vollständig bestätigten Sitzung und mit aktuellem Passwort TOTP einrichten. Der neue Faktor wird erst nach einem gültigen Code aktiviert. Geheimnisse sind mit dem hosteigenen `DATA_ENCRYPTION_KEY` verschlüsselt. Der öffentliche Dienst erhält keine Faktoren; interner und geschützter Arbeitsplatz verwalten eigene Faktoren für ihren jeweiligen Origin.

TOTP akzeptiert ein begrenztes Zeitfenster, aber jeden Zähler nur einmal. Rate-Limits schützen Konto und Clientadresse. Bei aktiviertem TOTP fällt die Passwortanmeldung nicht automatisch auf E-Mail zurück. Einmalige, getrennt aufzubewahrende Wiederherstellungscodes sind nur beim Erzeugen sichtbar und gehasht gespeichert. Sie ersetzen zusammen mit dem Passwort den zweiten Faktor. Faktorenwechsel brauchen zusätzlich den aktuell gewählten Faktor oder einen Wiederherstellungscode. Änderungen erhöhen die Faktorversion und beenden andere Sitzungen. Sicherheitsänderungen werden auditiert und neutral per E-Mail gemeldet.

Die Einrichtung gilt fünf Minuten; verlorene Codes/Authenticator erfordern den dokumentierten administrativen Wiederherstellungsweg. Ein verlorener Datenverschlüsselungsschlüssel kann nicht aus dem Datenbankbackup rekonstruiert werden.

## Passkeys

Browsergestützte Registrierung verlangt eine aktuelle vollständige Anmeldung, Passwort und gegebenenfalls bestehenden Faktor. Der Server prüft Origin, RP-ID, die sitzungsgebundene einmalige Challenge, Ablauf und Benutzerbestätigung (UV). Discoverable/resident Passkeys ermöglichen danach Anmeldung ohne Passwort; es werden vorab keine Konten oder Credentiallisten preisgegeben. Ein Passkey bestätigt bei Bedarf eine erneute Sicherheitsaktion. Höchstens zehn Geräte; der letzte aktive Passkey kann erst nach bestätigtem Wechsel auf einen anderen Faktor entfernt werden. Wiederherstellungscodes funktionieren alternativ zusammen mit dem Passwort.

Interner und geschützter Dienst haben getrennte Origins und Registrierungen. Domainänderungen benötigen deshalb vorab einen kontrollierten Faktorwechsel oder geeignete Wiederherstellung. Die CI prüft echte Registrierung und kryptografische Anmeldung mit einem virtuellen Chromium-Authenticator, zusätzlich zu Ablehnung falscher Sitzungen, fehlender Berechtigung und wiederholter Challenges. Reale iPad-/Firefox-/Windows-Hello-Geräte bleiben Teil der praktischen Abnahme.

Verifikation durch die etablierte Bibliothek `py_webauthn`, keine selbst geschriebene WebAuthn-Kryptografie: https://duo-labs.github.io/py_webauthn/registration.html und https://duo-labs.github.io/py_webauthn/authentication.html .

## Technischer Betrieb und Notfallzugriff

Die ausdrücklich zugewiesene technische Betriebsrolle ist getrennt von Fachrollen. Bootstrap weist sie dem Betreiber zu; spätere Änderungen benötigen den lokalen Befehl `manage.py operator EMAIL [--revoke]`. Superuserstatus oder kommunale Organisationsverwaltung ersetzen diese Rolle nicht. Betriebsaktionen benötigen eine frische vollständige Anmeldung.

Notfallzugriff benötigt benanntes Objekt (Vorlage oder Sitzung), Zweck, maximal zwei Stunden und vorherige Freigabe durch eine andere Organisationsadministration. Freigabe erzeugt einen eigenen ausdrücklich auszuwählenden Notfallkontext mit ausschließlich lesendem Zugriff/Export auf dieses Objekt. Keine Mandats-, Schreib-, Freigabe- oder Administrationsrechte. Die technische Rolle selbst enthält keine Inhalte. Ablauf, Entzug der Betriebsrolle und fehlende Freigabe sperren den Kontext. Antrag/Freigabe und Zweck werden auditiert; die Admingruppe der betroffenen Körperschaft erhält neutrale Hinweise. Notfallkontexte werden nicht extern repliziert.

## Kontrollierte Passwort-/Faktorwiederherstellung

Die Passwortwiederherstellung bestätigt einen zufälligen, nur gehasht gespeicherten E-Mail-Code (eine Stunde). Sie verändert bestehende TOTP-/Passkey-Faktoren nicht automatisch. Passwortvalidierung und PBKDF2-Hashing erfolgen serverseitig. Ein Code ist an Konto, aktuellen Passwortstand und weiterhin gültigen Kontext gebunden und nur einmal verwendbar. Öffentliche Anforderungsantworten geben keinen Kontobestand preis.

Der interne Dienst kann den bestätigten Passwortwechsel übernehmen. Anfragen/Nachweise vom geschützten Dienst werden hingegen ausschließlich intern abgeholt, geprüft und ausdrücklich genehmigt. Bis zur Zustimmung und anschließenden signierten Bereitstellung gelten die bisherigen Zugangsdaten. Nachweise sind verschlüsselt, enthalten den tatsächlichen E-Mail-Code als Besitznachweis und werden nie als generische Rechte-/Kontenänderung behandelt.

Organisationsadministration kann nach dokumentierter Identitätsprüfung eine Wiederherstellung anstoßen. Verlust aller Faktoren benötigt zusätzlich die technische Betriebsrolle und die ausdrückliche Faktorreset-Option. Reset und Passwortwechsel sind keine neue Rollenzuweisung. Auf dem geschützten Dienst wird ein genehmigter Reset genau einmal angewendet. Die zuständige Administration unterstützt Personen ohne verfügbaren Faktor; es gibt keinen stillen E-Mail-Fallback. Einladungsworker sendet Wiederherstellungslinks erst nach erfolgreicher Bereitstellung des nötigen externen Stands.
