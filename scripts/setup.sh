#!/usr/bin/env bash
# Geführte Erstinstallation. Kein Upgrade-, Restore- oder Produktionsfreigabewerkzeug.
set -Eeuo pipefail
umask 077

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
STACK=""
ENV_FILE="$ROOT/.env"
CONFIG_ONLY=0
CHECK_ONLY=0
CURRENT_STEP="Start"
TMP_ENV=""
BACKUP_TARGET=""
BACKUP_KEY_FILE=""
COMPOSE_FILE=""

say() { printf '\n%s\n' "$*" >&2; }
warn() { printf 'HINWEIS: %s\n' "$*" >&2; }
die() { printf 'FEHLER [%s]: %s\n' "$CURRENT_STEP" "$*" >&2; exit 1; }
cleanup() {
  local status=$?
  if [[ -n "$TMP_ENV" && -e "$TMP_ENV" ]]; then rm -f -- "$TMP_ENV"; fi
  if (( status != 0 )); then
    warn "Abbruch ohne Löschen von Datenvolumes. Ursache beheben und Setup erneut ausführen."
  fi
}
trap cleanup EXIT

usage() {
  cat <<'HELP'
Beschlussmanufaktur – geführtes Erstinstallations-Setup

  bash setup.sh --stack internal
  bash setup.sh --stack external
  bash setup.sh --stack internal --config-only
  bash setup.sh --stack external --check

Optionen:
  --stack internal|external   interner bzw. getrennter externer Host
  --env-file DATEI           private Compose-Umgebungsdatei (Standard: .env)
  --config-only              nur .env anlegen und prüfen; kein Docker benötigt
  --check                    bestehende .env prüfen, keine Änderungen
  --help                     diese Hilfe

WICHTIG: Extern und intern auf ZWEI getrennten Hosts ausführen.
Kein automatisches Update, keine Root-CA-Installation, kein Firewall-Setup
und keine Freigabe zum produktiven Einsatz. Niemals 'docker compose down -v'.
HELP
}

while (( $# > 0 )); do
  case "$1" in
    --stack) (( $# >= 2 )) || die "--stack erwartet internal oder external"; STACK="$2"; shift 2 ;;
    --env-file) (( $# >= 2 )) || die "--env-file benötigt einen Pfad"; ENV_FILE="$2"; shift 2 ;;
    --config-only) CONFIG_ONLY=1; shift ;;
    --check) CHECK_ONLY=1; shift ;;
    --help|-h) usage; exit 0 ;;
    *) die "Unbekannte Option: $1 (siehe --help)" ;;
  esac
done
(( ! (CONFIG_ONLY && CHECK_ONLY) )) || die "--config-only und --check schließen sich aus."
[[ -n "$STACK" ]] || die "Bitte --stack internal oder --stack external angeben."
[[ "$STACK" == internal || "$STACK" == external ]] || die "Ungültiger Stack."
[[ "$ENV_FILE" = /* ]] || ENV_FILE="$PWD/$ENV_FILE"
COMPOSE_FILE="$ROOT/compose.yaml"
[[ "$STACK" == external ]] && COMPOSE_FILE="$ROOT/compose.external.yaml"

command -v python3 >/dev/null 2>&1 || die "Python 3 fehlt (wird zum Erzeugen sicherer Schlüssel benötigt)."
[[ -f "$COMPOSE_FILE" ]] || die "Compose-Datei fehlt: $COMPOSE_FILE"

prompt() {
  local __name="$1" label="$2" default="$3" answer=""
  if [[ -n "$default" ]]; then
    printf '%s [%s]: ' "$label" "$default" >&2
  else
    printf '%s: ' "$label" >&2
  fi
  IFS= read -r answer || die "Eingabe abgebrochen."
  printf -v "$__name" '%s' "${answer:-$default}"
}
secret_prompt() {
  local __name="$1" label="$2" answer=""
  printf '%s (verdeckt): ' "$label" >&2
  IFS= read -rs answer || die "Eingabe abgebrochen."
  printf '\n' >&2
  printf -v "$__name" '%s' "$answer"
}
confirm() {
  local reply=""
  prompt reply "$1 [j/N]" "n"
  [[ "$reply" == j || "$reply" == J || "$reply" == ja || "$reply" == JA ]]
}
random_token() {
  python3 -c 'import secrets; print(secrets.token_urlsafe(64))'
}
fernet_token() {
  python3 -c 'import base64,os; print(base64.urlsafe_b64encode(os.urandom(32)).decode("ascii"))'
}
new_uuid() {
  python3 -c 'import uuid; print(uuid.uuid4())'
}
valid_hostname() {
  [[ "$1" =~ ^[[:alnum:]]([[:alnum:].-]{0,251}[[:alnum:]])?$ ]] &&
  [[ "$1" != *..* && "$1" != *--* && "$1" != *"_"* && "$1" != .* && "$1" != *"." ]]
}
valid_origin() {
  python3 - "$1" <<'PY'
import sys
from urllib.parse import urlsplit
try:
    u = urlsplit(sys.argv[1])
    assert u.scheme == "https" and u.hostname and not u.username and not u.password
    assert not u.path and not u.query and not u.fragment
    assert u.port is None or 1 <= u.port <= 65535
except (AssertionError, ValueError):
    sys.exit(1)
PY
}
require_hostname() {
  valid_hostname "$2" || die "$1: nur ein Hostname ohne Protokoll/Port/Pfad, keine Wildcards."
}
require_origin() {
  valid_origin "$2" || die "$1: vollständiger HTTPS-Origin ohne Pfad erforderlich."
}
# Kompatibel mit Compose-dotenv: einfache Quotes verhindern '$'-Interpolation.
# Keine Zugangsdaten in Prozessargumenten, Debug-Traces oder auf stdout.
write_env() {
  local key="$1" value="$2"
  [[ "$value" != *$'\n'* && "$value" != *$'\r'* ]] || die "Mehrzeilige Werte für $key sind nicht zulässig."
  value="${value//\'/\\\'}"
  printf "%s='%s'\n" "$key" "$value" >> "$TMP_ENV"
}
require_private_env() {
  [[ -f "$ENV_FILE" && ! -L "$ENV_FILE" ]] || die "Konfigurationsdatei fehlt oder ist ein Symlink: $ENV_FILE"
  python3 - "$ENV_FILE" "$STACK" <<'PY'
import base64,os,re,stat,sys,uuid
from pathlib import Path
from urllib.parse import urlsplit
p=Path(sys.argv[1])
mode=stat.S_IMODE(p.stat().st_mode)
if mode & 0o077:
    sys.exit("FEHLER: .env muss ausschließlich für den Eigentümer lesbar sein (chmod 600).")
values={}
for line in p.read_text(encoding="utf-8").splitlines():
    line=line.strip()
    if not line or line.startswith("#"):
        continue
    if "=" not in line:
        sys.exit("FEHLER: Ungültige Zeile in .env.")
    key,val=line.split("=",1)
    key=key.strip()
    if not re.fullmatch(r"[A-Z][A-Z0-9_]*",key):
        sys.exit("FEHLER: Ungültiger Variablenname in .env.")
    val=val.strip()
    if val.startswith("'") and val.endswith("'"):
        val=val[1:-1].replace("\\'","'")
    elif val.startswith('"') and val.endswith('"'):
        val=val[1:-1]
    values[key]=val
stack=sys.argv[2]
if values.get("BM_SETUP_STACK") not in ("",stack):
    sys.exit("FEHLER: .env gehört zu einem anderen Stack. Getrennte Hosts/Konfigurationsdateien nutzen.")
def required(key,n=1):
    if len(values.get(key,"")) < n:
        sys.exit("FEHLER: Wert fehlt oder ist zu kurz: "+key)
def host(key):
    required(key)
    v=values[key]
    if len(v)>253 or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.-]*[A-Za-z0-9]",v) and v!="localhost":
        sys.exit("FEHLER: Ungültiger Hostname: "+key)
    if ".." in v or v.endswith("."):
        sys.exit("FEHLER: Ungültiger Hostname: "+key)
def origin(key):
    required(key)
    u=urlsplit(values[key])
    if u.scheme!="https" or not u.hostname or u.username or u.password or u.path or u.query or u.fragment:
        sys.exit("FEHLER: Unsicherer HTTPS-Origin: "+key)
    try: u.port
    except ValueError: sys.exit("FEHLER: Ungültiger Port: "+key)
def fernet(key):
    required(key)
    try: valid=base64.urlsafe_b64decode(values[key].encode())
    except Exception: valid=b""
    if len(valid)!=32: sys.exit("FEHLER: Ungültiger 256-Bit-Schlüssel: "+key)
if stack=="internal":
    for key in ("DJANGO_SECRET_KEY",): required(key,50)
    required("POSTGRES_PASSWORD",32)
    fernet("DATA_ENCRYPTION_KEY")
    host("SITE_ADDRESS")
    origin("APPLICATION_URL")
    origin("CSRF_TRUSTED_ORIGINS")
    required("TLS_INTERNAL_AGENT_KEY",32)
else:
    for key in ("PROTECTED_SECRET_KEY","PUBLIC_SECRET_KEY"): required(key,50)
    if values["PROTECTED_SECRET_KEY"]==values["PUBLIC_SECRET_KEY"]:
        sys.exit("FEHLER: Verschiedene interne Schlüssel für protected/public erforderlich.")
    for key in ("PROTECTED_DB_PASSWORD","PUBLIC_DB_PASSWORD"): required(key,32)
    if values["PROTECTED_DB_PASSWORD"]==values["PUBLIC_DB_PASSWORD"]:
        sys.exit("FEHLER: Die beiden Datenbanken brauchen verschiedene Passwörter.")
    fernet("PROTECTED_DATA_ENCRYPTION_KEY")
    host("PROTECTED_HOST")
    host("PUBLIC_HOST")
    if values["PROTECTED_HOST"]==values["PUBLIC_HOST"]:
        sys.exit("FEHLER: Geschütztes und öffentliches Portal brauchen verschiedene Hosts.")
    required("TLS_EXTERNAL_AGENT_KEY",32)
if values.get("SMTP_STARTTLS")=="true" and values.get("SMTP_SSL")=="true":
    sys.exit("FEHLER: SMTP STARTTLS und SSL dürfen nicht beide aktiv sein.")
if values.get("EXCHANGE_SOURCE"):
    try: uuid.UUID(values["EXCHANGE_SOURCE"])
    except ValueError: sys.exit("FEHLER: EXCHANGE_SOURCE muss eine UUID sein.")
    if stack=="internal":
        for key in ("EXCHANGE_PROTECTED_KEY","EXCHANGE_PUBLIC_KEY"):required(key,32)
        for key in ("EXCHANGE_PROTECTED_URL","EXCHANGE_PUBLIC_URL"):origin(key)
    else:
        for key in ("EXCHANGE_PROTECTED_KEY","EXCHANGE_PUBLIC_KEY"):required(key,32)
else:
    for key in ("EXCHANGE_PROTECTED_KEY","EXCHANGE_PUBLIC_KEY","EXCHANGE_PROTECTED_URL","EXCHANGE_PUBLIC_URL"):
        if values.get(key):
            sys.exit("FEHLER: Exchange-Konfiguration unvollständig: EXCHANGE_SOURCE fehlt.")
print("Konfiguration geprüft; Schlüssel und Passwörter wurden nicht ausgegeben.")
PY
}
read_value() {
  python3 - "$ENV_FILE" "$1" <<'PY'
import sys
from pathlib import Path
for raw in Path(sys.argv[1]).read_text().splitlines():
    if raw.startswith(sys.argv[2]+"="):
        value=raw.split("=",1)[1]
        if len(value)>=2 and value[0]==value[-1]=="'":
            value=value[1:-1].replace("\\'","'")
        print(value)
        break
PY
}
compose() {
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}
check_compose() {
  command -v docker >/dev/null 2>&1 || die "Docker CLI fehlt; Anleitung: https://docs.docker.com/engine/install/"
  docker compose version >/dev/null 2>&1 || die "Docker Compose v2 fehlt."
  docker info >/dev/null 2>&1 || die "Docker Engine nicht erreichbar oder Benutzer hat keinen Zugriff."
  compose config --quiet || die "Docker Compose-Konfiguration ungültig."
}
dns_hint() {
  local hostname="$1"
  [[ "$hostname" != localhost && "$hostname" != *.localhost ]] || return 0
  if command -v getent >/dev/null 2>&1; then
    if getent ahosts "$hostname" >/dev/null 2>&1; then
      say "DNS: $hostname ist auf diesem Host auflösbar. Zieladresse und Split-DNS zusätzlich prüfen."
    else
      warn "$hostname ist auf diesem Host nicht auflösbar; DNS vor Nutzung korrekt setzen."
    fi
  fi
}
check_existing_services() {
  local running=""
  running="$(compose ps --status running --services 2>/dev/null || true)"
  while IFS= read -r svc; do
    [[ -n "$svc" ]] || continue
    case "$svc" in
      db|protected-db|public-db) ;;
      *) die "Dienste laufen bereits ($svc). Dieses Skript ist NUR für Erstinstallationen; Updates nach docs/12-installation.md." ;;
    esac
  done <<< "$running"
}
backup_key() {
  local file="$1"
  [[ "$file" == /* ]] || die "Schlüsselpfad muss absolut sein."
  [[ "$file" != "$ROOT/"* ]] || die "Backup-Schlüssel außerhalb des Repositorys speichern."
  if [[ -e "$file" || -L "$file" ]]; then
    python3 - "$file" <<'PY'
import os,stat,sys
p=sys.argv[1]
if not os.path.isfile(p) or stat.S_IMODE(os.stat(p).st_mode)&0o077:
    sys.exit("FEHLER: Vorhandener Backup-Schlüssel muss eine reguläre Datei mit 0600 sein.")
PY
    return 0
  fi
  python3 - "$file" <<'PY'
import base64,os,pathlib,sys
p=pathlib.Path(sys.argv[1])
p.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
with os.fdopen(fd,"wb") as file:
    file.write(base64.urlsafe_b64encode(os.urandom(32))+b"\n")
PY
  say "Backup-Schlüssel privat erstellt; an einem getrennten sicheren Ort hinterlegen."
}

CURRENT_STEP="Konfiguration"
say "Beschlussmanufaktur – geführte Erstinstallation ($STACK)"
warn "Entwicklungsstand, noch nicht produktiv freigegeben. Caddy nutzt aktuell eine lokale CA (tls internal)."
if [[ "$STACK" == external ]]; then
  warn "Externe und interne Instanz brauchen getrennte Hosts und Datenbanken; nie gemeinsam deployen."
fi

if (( ! CHECK_ONLY )); then
  if [[ -f "$ENV_FILE" ]]; then
    require_private_env
    if (( CONFIG_ONLY )); then
      say "Vorhandene private Konfiguration unverändert übernommen: $ENV_FILE"
      exit 0
    fi
    confirm "Vorhandene .env weiterverwenden? Es werden keine Schlüssel überschrieben." || die "Nichts verändert."
  else
    [[ ! -e "$ENV_FILE" && ! -L "$ENV_FILE" ]] || die "Unsichere oder unzugängliche Konfigurationsdatei."
    mkdir -p -- "$(dirname "$ENV_FILE")"
    TMP_ENV="$(mktemp "$(dirname "$ENV_FILE")/.bm-setup.XXXXXX")"
    chmod 600 "$TMP_ENV"
    write_env BM_SETUP_STACK "$STACK"
    write_env HTTP_PORT 80
    write_env HTTPS_PORT 443

    if [[ "$STACK" == internal ]]; then
      prompt site "DNS-/Host-Name des internen Fachsystems (ohne Schema)" "localhost"
      require_hostname SITE_ADDRESS "$site"
      prompt port "Externer HTTPS-Port" "443"
      [[ "$port" =~ ^[0-9]+$ ]] && (( port>=1 && port<=65535 )) || die "Ungültiger HTTPS-Port."
      origin="https://$site"
      if [[ "$port" != 443 ]]; then origin="$origin:$port"; fi
      write_env SITE_ADDRESS "$site"
      write_env HTTPS_PORT "$port"
      write_env APPLICATION_URL "$origin"
      write_env DJANGO_ALLOWED_HOSTS "$site,localhost,127.0.0.1"
      write_env CSRF_TRUSTED_ORIGINS "$origin"
      write_env DJANGO_SECRET_KEY "$(random_token)"
      write_env POSTGRES_PASSWORD "$(random_token)"
      write_env DATA_ENCRYPTION_KEY "$(fernet_token)"
      write_env TLS_INTERNAL_AGENT_KEY "$(random_token)"
    else
      prompt protected "Hostname des geschützten Mandatsträgerportals" "gremien.localhost"
      prompt public "Hostname des öffentlichen Bürgerportals" "info.localhost"
      require_hostname PROTECTED_HOST "$protected"
      require_hostname PUBLIC_HOST "$public"
      [[ "$protected" != "$public" ]] || die "Öffentliches und geschütztes Portal müssen getrennte Hosts erhalten."
      write_env PROTECTED_HOST "$protected"
      write_env PUBLIC_HOST "$public"
      write_env PROTECTED_SECRET_KEY "$(random_token)"
      write_env PUBLIC_SECRET_KEY "$(random_token)"
      write_env PROTECTED_DB_PASSWORD "$(random_token)"
      write_env PUBLIC_DB_PASSWORD "$(random_token)"
      write_env PROTECTED_DATA_ENCRYPTION_KEY "$(fernet_token)"
      write_env TLS_EXTERNAL_AGENT_KEY "$(random_token)"
    fi

    say "SMTP wird für Anmeldecodes benötigt. Kein Logging von Codes oder Passwörtern."
    prompt smtp_host "SMTP-Server (leer = nur vorbereiten, kein Deploy)" ""
    write_env SMTP_HOST "$smtp_host"
    if [[ -n "$smtp_host" ]]; then
      prompt smtp_mode "Transport (starttls oder ssl)" "starttls"
      [[ "$smtp_mode" == starttls || "$smtp_mode" == ssl ]] || die "SMTP nur mit STARTTLS oder TLS/SSL."
      default_port=587
      [[ "$smtp_mode" == ssl ]] && default_port=465
      prompt smtp_port "SMTP-Port" "$default_port"
      [[ "$smtp_port" =~ ^[0-9]+$ ]] && (( smtp_port>=1 && smtp_port<=65535 )) || die "SMTP-Port ungültig."
      prompt smtp_user "SMTP-Benutzer" ""
      secret_prompt smtp_password "SMTP-Passwort"
      prompt smtp_from "Absenderadresse (E-Mail)" ""
      [[ "$smtp_from" == *"@"* && "$smtp_from" != *" "* ]] || die "Gültige SMTP-Absenderadresse erforderlich."
      write_env SMTP_PORT "$smtp_port"
      write_env SMTP_USER "$smtp_user"
      write_env SMTP_PASSWORD "$smtp_password"
      write_env SMTP_FROM "$smtp_from"
      if [[ "$smtp_mode" == ssl ]]; then
        write_env SMTP_STARTTLS false
        write_env SMTP_SSL true
      else
        write_env SMTP_STARTTLS true
        write_env SMTP_SSL false
      fi
      unset smtp_password
    fi

    if [[ "$STACK" == internal ]] && confirm "Optionalen IMAP-Rücklauf-Posteingang einrichten?"; then
      prompt imap_host "IMAP-Server" ""
      prompt imap_user "IMAP-Benutzer" ""
      secret_prompt imap_password "IMAP-Passwort"
      prompt imap_org "Organisations-ID (optional, später im Adminbereich)" ""
      write_env IMAP_HOST "$imap_host"
      write_env IMAP_PORT 993
      write_env IMAP_USER "$imap_user"
      write_env IMAP_PASSWORD "$imap_password"
      write_env IMAP_FOLDER INBOX
      write_env IMAP_ORGANIZATION "$imap_org"
      unset imap_password
    fi

    if confirm "Abgesicherten Austausch zwischen INTERNEM und EXTERNEM Host konfigurieren?"; then
      warn "UUID und zwei verschiedene Kanalschlüssel müssen auf BEIDEN Hosts übereinstimmen. Nur über sicheren Administrationsweg übertragen."
      if [[ "$STACK" == internal ]]; then
        write_env EXCHANGE_SOURCE "$(new_uuid)"
        write_env EXCHANGE_PROTECTED_KEY "$(random_token)"
        write_env EXCHANGE_PUBLIC_KEY "$(random_token)"
        prompt transfer_protected "HTTPS-Origin des geschützten Portals" "https://gremien.localhost"
        prompt transfer_public "HTTPS-Origin des öffentlichen Portals" "https://info.localhost"
        require_origin EXCHANGE_PROTECTED_URL "$transfer_protected"
        require_origin EXCHANGE_PUBLIC_URL "$transfer_public"
        write_env EXCHANGE_PROTECTED_URL "$transfer_protected"
        write_env EXCHANGE_PUBLIC_URL "$transfer_public"
        prompt exchange_ca "Vertrauenswürdiges CA-Zertifikat im internen Container (optional)" ""
        write_env EXCHANGE_CA_FILE "$exchange_ca"
      else
        prompt exchange_source "EXCHANGE_SOURCE UUID vom internen Host" ""
        secret_prompt exchange_protected "EXCHANGE_PROTECTED_KEY vom internen Host"
        secret_prompt exchange_public "EXCHANGE_PUBLIC_KEY vom internen Host"
        write_env EXCHANGE_SOURCE "$exchange_source"
        write_env EXCHANGE_PROTECTED_KEY "$exchange_protected"
        write_env EXCHANGE_PUBLIC_KEY "$exchange_public"
        unset exchange_protected exchange_public
      fi
    else
      warn "Datenaustausch ist deaktiviert; externe Portale erhalten ohne spätere Freigabe/Transfer keine Fachdaten."
    fi

    say "Sicherung nach bestehendem AES-256-GCM-Backupverfahren (separates Ziel, getrennter Schlüssel)."
    prompt BACKUP_TARGET "Absolutes Backupziel auf separatem Datenträger/Mount (leer = später)" ""
    if [[ -n "$BACKUP_TARGET" ]]; then
      [[ "$BACKUP_TARGET" == /* && "$BACKUP_TARGET" != "$ROOT" && "$BACKUP_TARGET" != "$ROOT/"* ]] || die "Separates absolutes Backupziel außerhalb des Repositorys wählen."
      prompt BACKUP_KEY_FILE "Absoluter Backup-Schlüsselpfad außerhalb des Repositorys" ""
      [[ "$BACKUP_KEY_FILE" == /* && "$BACKUP_KEY_FILE" != "$ROOT/"* ]] || die "Backup-Schlüsselpfad separat und absolut wählen."
      [[ "$BACKUP_KEY_FILE" != "$BACKUP_TARGET" && "$BACKUP_KEY_FILE" != "$BACKUP_TARGET/"* ]] || die "Sicherungsschlüssel nicht im Sicherungsziel aufbewahren."
      write_env BM_BACKUP_TARGET "$BACKUP_TARGET"
      write_env BM_BACKUP_KEY_FILE "$BACKUP_KEY_FILE"
    else
      warn "Ohne getrennte Sicherung ist keine Betriebsfreigabe möglich."
    fi

    # No-clobber: selbst parallele Setups dürfen keine vorhandene .env ersetzen.
    if (set -C; cat "$TMP_ENV" > "$ENV_FILE"); then
      chmod 600 "$ENV_FILE"
      rm -f "$TMP_ENV"; TMP_ENV=""
      say "Private Konfiguration neu erstellt: $ENV_FILE (0600). Keine Zugangsdaten angezeigt."
    else
      die "Eine .env existiert bereits. Keine Schlüssel überschrieben."
    fi
  fi
fi

CURRENT_STEP="Konfigurationsprüfung"
require_private_env
if (( CONFIG_ONLY )); then
  say "Konfiguration erstellt. Nach Prüfung: bash setup.sh --stack $STACK"
  exit 0
fi
if (( CHECK_ONLY )); then
  if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    compose config --quiet || die "Compose-Konfiguration fehlerhaft."
    say "Compose-Konfiguration gültig."
  else
    warn "Docker/Compose nicht vorhanden. Compose-Prüfung ausgelassen."
  fi
  exit 0
fi

CURRENT_STEP="Docker- und Betriebsprüfung"
check_compose
check_existing_services
if [[ -z "$(read_value SMTP_HOST)" || -z "$(read_value SMTP_FROM)" ]]; then
  die "Vor echtem Deploy SMTP_HOST und SMTP_FROM in .env setzen: ohne Mailversand keine sichere Anmeldung."
fi
if [[ "$STACK" == internal ]]; then
  dns_hint "$(read_value SITE_ADDRESS)"
else
  dns_hint "$(read_value PROTECTED_HOST)"
  dns_hint "$(read_value PUBLIC_HOST)"
fi
warn "Caddy nutzt im ausgelieferten Caddyfile 'tls internal'. Private Root-CA vor Browserverwendung auf Endgeräten vertrauenswürdig installieren."
warn "DNS, Firewall, ausgehenden SMTP-Zugang und Port 80/443 auf dem Host kontrollieren."
confirm "Erstinstallation ausführen? Datenbanken werden angelegt/migriert, Images gebaut." || die "Deployment nicht gestartet."

CURRENT_STEP="Build"
say "Baue Anwendung und benötigte Images."
if [[ "$STACK" == internal ]]; then
  compose build backend tls-agent backup-tools
else
  compose build protected public tls-agent backup-tools
fi

CURRENT_STEP="Datenbank"
if [[ "$STACK" == internal ]]; then
  compose up -d --wait db
  CURRENT_STEP="Datenbankschema intern"
  compose run --rm -T --no-deps backend python manage.py migrate --noinput
  CURRENT_STEP="Erstkonto und Verwaltungsverbund"
  already_setup="$(compose run --rm -T --no-deps backend python manage.py shell -c 'from core.models import User; print(User.objects.exists())' | tail -n 1)"
  case "$already_setup" in
    True) say "Einrichtungs-Konto existiert bereits; einmaliger Bootstrap wird nicht wiederholt." ;;
    False)
      [[ -t 0 && -t 1 ]] || die "Für den einmaligen Django-Bootstrap ist ein interaktives Terminal erforderlich."
      say "Erste Verwaltungsidentität einrichten; Passwort wird vom Django-Bootstrap verdeckt abgefragt."
      compose run --rm --no-deps backend python manage.py bootstrap ;;
    *) die "Einrichtungsstatus konnte nicht sicher ermittelt werden." ;;
  esac
else
  compose up -d --wait protected-db public-db
  CURRENT_STEP="Datenbankschema extern"
  compose run --rm -T --no-deps protected python manage.py migrate --noinput
  compose run --rm -T --no-deps public python manage.py migrate --noinput
  say "Externe Konten werden nicht lokal gebootstrapped; Provisionierung erfolgt ausschließlich intern."
fi

CURRENT_STEP="Dienststart"
compose up -d --wait

CURRENT_STEP="Readiness"
apps=(backend)
[[ "$STACK" == external ]] && apps=(protected public)
for app in "${apps[@]}"; do
  compose exec -T "$app" python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready/',timeout=10)"
  say "Bereit: $app (interne Django-DB-Bereitschaft)."
done

BACKUP_TARGET="$(read_value BM_BACKUP_TARGET)"
BACKUP_KEY_FILE="$(read_value BM_BACKUP_KEY_FILE)"
if [[ -n "$BACKUP_TARGET" && -n "$BACKUP_KEY_FILE" ]]; then
  CURRENT_STEP="Schlüssel zur verschlüsselten Sicherung"
  backup_key "$BACKUP_KEY_FILE"
  if [[ "$ENV_FILE" != "$ROOT/.env" ]]; then
    warn "Backup-Helfer liest .env im Repo. Mit --env-file abweichende Konfiguration: Erstbackup nur nach gesonderter Operator-Konfiguration."
  elif python3 -c "import cryptography" >/dev/null 2>&1; then
    if confirm "Jetzt eine erste verschlüsselte Sicherung mit dem vorhandenen Backup-Werkzeug ausführen?"; then
      CURRENT_STEP="Erstsicherung"
      python3 "$ROOT/ops/backup.py" backup --stack "$STACK" --target "$BACKUP_TARGET" --key-file "$BACKUP_KEY_FILE"
    fi
  else
    warn "Python-Paket cryptography fehlt auf dem Host. Backup-Werkzeug nach Installation der Ops-Abhängigkeit ausführen; kein Backup behauptet."
  fi
else
  warn "Sicherungsziel/Schlüssel fehlen. Vor echtem Einsatz getrennt konfigurieren und einen Restore praktisch erproben."
fi

say "Erstinstallation des Stacks '$STACK' erfolgreich gestartet; HTTP-Container-Readiness wurde geprüft."
warn "Dies ist KEINE Produktiv-, TLS-, Datenschutz-, Restore- oder Fachabnahme."
say "Nächste Schritte: Root-CA sicher exportieren, Browser-/DNS-/SMTP-Login prüfen, ggf. Datenaustausch und Backup/Restore testen."
say "Caddy-CA exportieren (nur öffentliches Zertifikat, NICHT den privaten Schlüssel):"
printf '  docker compose --env-file %q -f %q exec -T caddy cat /data/caddy/pki/authorities/local/root.crt > caddy-local-root.crt\n' "$ENV_FILE" "$COMPOSE_FILE" >&2
say "Betriebs- und Wiederherstellungsanleitung: docs/12-installation.md, docs/07-betrieb.md"
