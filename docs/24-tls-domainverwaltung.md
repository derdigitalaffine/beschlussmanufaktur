# Domain- und TLS-Verwaltung

Unter `/betrieb/tls/` bereitet die ausdrücklich zugewiesene technische Betriebsrolle einen prüfbaren Umstellungsauftrag vor. Lokale Caddy-CA ist Standard; alternativ Let's Encrypt über HTTP-/TLS-ACME oder importierte PEM-Zertifikatskette mit passendem privatem Schlüssel. Kein frei eingegebener Caddycode und kein Docker-Socket. Der öffentliche und geschützte Fachprozess besitzen weder Agentenschlüssel noch Caddy-Administrationssocket.

Der separate Host-Agent verwendet ausschließlich einen privaten Unix-Socket zum transaktionalen Caddy-Neuladen. Er akzeptiert zeitgebundene HMAC-Aufträge, feste Dienstrollen/Upstreams, validierte Domains und begrenztes Zertifikatsmaterial. Wiederholungen sind idempotent. Abgewiesene Konfiguration ersetzt den letzten akzeptierten Stand nicht. Nach Neustart stellt der Agent den letzten akzeptierten gewünschten Stand aus seinem privaten Laufzeitvolume wieder her.

## Einrichtung

1. Eigene Laufzeitgeheimnisse `TLS_INTERNAL_AGENT_KEY` und `TLS_EXTERNAL_AGENT_KEY` setzen (je mindestens 32 zufällige Zeichen). Der interne Fachdienst/Betriebsworker bekommt beide; jeder Host-Agent ausschließlich seinen eigenen. Keine Agentenschlüssel in `public`/`protected`.
2. Zertifikatimport braucht `DATA_ENCRYPTION_KEY`. Der private Upload wird verschlüsselt gespeichert, erst beim signierten Transfer entschlüsselt und im Agentenvolume mit restriktiven Dateirechten abgelegt.
3. Origins/Hosts vorbereiten. Die interne Anwendung bleibt intern/VPN. Geschützter Origin braucht passende `DJANGO_ALLOWED_HOSTS`/CSRF-Origins und gegebenenfalls Dienstneustart. Öffentliche zusätzliche Domains stammen ausschließlich aus der signierten Portalzuordnung; `PublicHostMiddleware` prüft sie vor Umleitung/Rendering. Ohne Freigabe wird ein fremder Host abgewiesen.
4. Externe Übertragung läuft intern initiiert über den öffentlichen HTTPS-Origin und `/betrieb/tls-agent/plan`. Interner Agent ist ausschließlich über das Compose-Netz erreichbar. Lokale CA über `EXCHANGE_CA_FILE` vertrauen; Vertrauensprüfung niemals abschalten.

## Let's Encrypt und DNS

Auftrag erzeugt einen TXT-Besitznachweis `_beschlussmanufaktur.DOMAIN`. Automatische Prüfung über zwei öffentliche Resolver verlangt übereinstimmende A/AAAA-Adressen aus der ausdrücklich angegebenen öffentlichen Zielmenge und den TXT-Wert. Vor Anwendung wird erneut geprüft. Die Webfreigabe verfällt nach 20 Minuten; höchstens zehn Versuche, danach bewusst erneut anstoßen.

DNS-Prüfung ist **keine DNS-01-Challenge**. Der implementierte Standard verwendet Caddys HTTP-/TLS-ACME, benötigt öffentlich erreichbare Ports 80/443 und gültige DNS-Einträge. Ein ausschließlich internes Netz verwendet weiter lokale CA oder passenden Zertifikatimport. Providerabhängiges DNS-01 bleibt ein später auswählbarer Adapter, da bisher kein DNS-Provider festgelegt wurde. Caddy erneuert ausgestellte ACME-Zertifikate automatisch. Agentstatus `applied` bestätigt die akzeptierte Konfiguration, nicht die asynchrone erfolgreiche Zertifikatsausstellung; Zertifikats-/Erreichbarkeitsprüfung folgt im Betriebsmonitor und in der Produktivabnahme.

## Zertifikatimport und Rückweg

SAN-Domain, Schlüsselübereinstimmung, Stärke, zeitliche Gültigkeit und die mitgelieferte Kette werden geprüft. Kommunale private CAs sind erlaubt; Vertrauen muss auf den Geräten eingerichtet werden. Kein Import beliebiger Dateipfade. Bei Domainwechsel zuerst Passkey-/Faktorwiederherstellung vorbereiten.

Agentenvolume `tls_runtime`, Caddyvolume `caddy_data` und deren private Dateien sichern. Lokaler Rückweg: Worker stoppen, letzten gültigen Laufzeitstand wiederherstellen und Caddy/Agent kontrolliert starten. Keine produktiven Zertifikate oder DNS-Einstellungen wurden für die Entwicklung verändert.

CI prüft echten signierten Agentenauftrag, Caddy-Neuladen, Wiederholung, abgewiesene Hostinjection und HTTPS gegen die ausdrücklich vertraute Test-CA. Grundlage: https://caddyserver.com/docs/api und https://caddyserver.com/docs/caddyfile/directives/tls .
