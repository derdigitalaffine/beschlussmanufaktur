# Installation des Entwicklungsstands

Voraussetzungen: Linux, Docker Engine mit Compose v2, DNS/Hostauflösung für die gewählten Domains, administrativer Hostzugriff und funktionierender SMTP-Versand. Die folgenden Schritte betreffen den Entwicklungsstand, nicht eine bereits abgenommene Produktivinstallation.

## Intern / Einzelserver

1. Repository klonen und `.env.example` nach `.env` kopieren.
2. `DJANGO_SECRET_KEY` mit mindestens 50 zufälligen Zeichen und `POSTGRES_PASSWORD` setzen. Zum Generieren separat `python -c "import secrets; print(secrets.token_urlsafe(64))"` verwenden. Werte nicht committen.
3. `SITE_ADDRESS`, `DJANGO_ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` und `APPLICATION_URL` passend setzen, beispielsweise `ris.intern.example`, `ris.intern.example`, `https://ris.intern.example` und `https://ris.intern.example`. Bei abweichendem HTTPS-Port den Origin inklusive Port setzen. `APPLICATION_URL` ist die vertrauenswürdige Basis der Einladungslinks und wird niemals aus einem Request-Host übernommen.
4. SMTP-Host, Port, Benutzer, Passwort und den einen Absender einstellen. STARTTLS und implizites SSL nicht gleichzeitig aktivieren. Kein Konsolen-Mailbackend: Anmeldecodes gehören nicht in Containerlogs.
5. Installation prüfen, Image bauen, Datenbank migrieren und erstes Konto interaktiv einrichten:

```sh
docker compose config --quiet
docker compose build
docker compose up -d db
docker compose run --rm backend python manage.py migrate
docker compose run --rm backend python manage.py bootstrap
docker compose up -d
```

Bootstrap fragt E-Mail, Verbundname und Passwort ab. Es erzeugt ausdrücklich eine Organisationsverwaltungsrolle und ist bei vorhandenen Konten gesperrt. Keine voreingestellten Zugangsdaten. Anmeldung erfolgt mit Passwort und anschließendem E-Mail-Code. Domain muss auf den Host zeigen; internes Verwaltungssystem nicht unkontrolliert ins öffentliche Internet exponieren.

Weitere Nutzer werden unter „Menschen und Rollen“ des ausgewählten Organisationskontexts eingeladen. Rollenverwaltung und Einladung sind im aktuellen Stand ausschließlich intern erreichbar. Details: [Konten und Rollen bedienen](13-konten-rollen.md).

## TLS-Vertrauen

Caddy erstellt eine lokale CA. Deren öffentliches Wurzelzertifikat liegt im Caddy-Datenvolume unter `caddy/pki/authorities/local/root.crt`. Über die Hostadministration auslesen und auf den vorgesehenen Endgeräten vertrauenswürdig installieren. Den privaten CA-Schlüssel niemals verteilen. Browserwarnungen nicht als dauerhaften Betriebsweg übergehen. Die spätere Umstellung auf Let's Encrypt im Adminbereich ist noch nicht implementiert.

## Externer Server

Separater Host, eigene `.env`, getrennte `PROTECTED_SECRET_KEY`/`PUBLIC_SECRET_KEY` und `PROTECTED_DB_PASSWORD`/`PUBLIC_DB_PASSWORD`, Domains `PROTECTED_HOST` und `PUBLIC_HOST`. Diese Dateien verwenden keine interne Datenbankadresse und öffnen keine Verbindung ins interne Netz.

```sh
docker compose -f compose.external.yaml config --quiet
docker compose -f compose.external.yaml build
docker compose -f compose.external.yaml up -d protected-db public-db
docker compose -f compose.external.yaml run --rm protected python manage.py migrate
docker compose -f compose.external.yaml run --rm public python manage.py migrate
docker compose -f compose.external.yaml up -d
```

Konten und Rechte werden intern verwaltet und geschützt provisioniert. Keinen externen Bootstrap öffnen und keine Passwortkopien improvisieren. Der öffentliche Dienst zeigt ausschließlich ausdrücklich freigegebene Daten. Für Datenaustausch auf beiden Hosts dieselbe Installations-UUID in `EXCHANGE_SOURCE` setzen; für jeden Kanal einen eigenen zufälligen Schlüssel (mindestens 32 Zeichen) erzeugen. Der interne Host erhält beide Schlüssel, der geschützte Dienst nur `EXCHANGE_PROTECTED_KEY`, der öffentliche Dienst nur `EXCHANGE_PUBLIC_KEY`. Interne Origins `EXCHANGE_PROTECTED_URL`/`EXCHANGE_PUBLIC_URL` als feste HTTPS-Origins ohne Pfad konfigurieren.

Bei lokaler externer Caddy-CA deren öffentliches Root-PEM sicher zum internen Host kopieren, im internen Dateivolume beispielsweise unter `/app/data/exchange-ca.pem` ablegen und `EXCHANGE_CA_FILE` entsprechend setzen. Niemals TLS-Prüfung abschalten oder private CA-Schlüssel kopieren. Dieses CA-Zertifikat muss außerdem auf den vorgesehenen Endgeräten vertrauenswürdig installiert sein, damit Offline-Funktionen einen sicheren Browserkontext haben.

Intern „Datenbereitstellung“ je Körperschaft ausdrücklich konfigurieren. Nach Migrationen Worker starten und den ersten Transfer prüfen:

```sh
docker compose run --rm backend python manage.py exchange_worker --snapshot
```

Der regelmäßige Worker überträgt freigegebene Metadaten/Dateien und holt externe Vorschläge und Sitzungsrückgaben ab. Beim Transferfehler wird erneut versucht; nach 24 Stunden ohne frischen geschützten Rechtebestand sind externe Arbeitskontexte gesperrt. Details: docs/14–16. Das externe Netz darf keinen initiierbaren Zugang zum internen Host bekommen; Host-Firewall/VLAN-Regeln sind zusätzlich erforderlich.

Für externe Sitzungsführung intern Einladung ausgeben, führenden Dienst aktivieren und erfolgreiche Bereitstellung prüfen. Extern Schriftführung übernehmen und Besetzung vorbereiten. Nach Abschluss Sitzung/Niederschrift über „Kontrollierte Rückgabe“ einfrieren. Intern das abgeholte Journal prüfen und genehmigen. Erst die folgende Übertragung macht die externe Fassung zur internen Lesekopie. Offline-Arbeit: docs/19.

## Betriebshinweise

Keine Datenbankports sind veröffentlicht. Caddy ist der einzige veröffentlichte Eingang. `/health/live/` prüft Prozessantwort, `/health/ready/` die Datenbankverbindung; Bereitschaft ersetzt keine Prüfung bereits erfolgter Migrationen. Volumes sind persistent. `docker compose down -v` löscht Daten und ist kein normaler Neustartbefehl.

Die Compose-Dienste vertrauen Caddys Forwarded-Clientadresse ausdrücklich, damit Anmelde-/Einladungslimits nicht alle Nutzer hinter dem Proxy gemeinsam treffen. `TRUST_PROXY_HEADERS=true` ist nur bei diesem privaten, ausschließlich über Caddy erreichbaren Backend zulässig; bei direktem Backendzugang deaktivieren. Caddy muss eingehende Forwarded-Header weiterhin aus nicht vertrauenswürdigen Quellen überschreiben.

Backup/Restore und TLS-/Domainverwaltung sind noch nicht automatisiert. Containerimages verwenden zurzeit Major-Tags; geprüfte Digest-Pins folgen im Releaseprozess. Vor öffentlichem Produktiveinsatz müssen die im Anforderungskatalog beschriebenen Kernfunktionen und Abnahmen abgeschlossen sein.


## Aktualisierung dieses Entwicklungsstands

Alle Worker vor Schema-/Vertragsänderungen anhalten. Neue Images auf beiden Hosts bauen, Datenbankbackup anlegen, Migrationen intern sowie geschützt/öffentlich ausführen und erst danach Dienste/Worker wieder starten. Kompatible Codeversionen auf beiden Hosts verwenden; nicht einzelne alte Transferdienste mit einem neuen Vertrag weiterbetreiben. Migration 0022 entfernt ausschließlich hostlokale Stimm-/Befangenheitsnummern aus wartenden Austauschverträgen; Fachwerte und dauerhafte Stimm-IDs bleiben erhalten. Rollback nach Fachänderungen benötigt einen konsistenten Restore, nicht nur ein älteres Image. Automatisierte Update-/Restoreverwaltung folgt später.
