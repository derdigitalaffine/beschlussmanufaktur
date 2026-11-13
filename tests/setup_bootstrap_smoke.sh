#!/usr/bin/env bash
# Offline/CI-smoke: no Docker builds, migrations, DNS calls or secret output.
set -Eeuo pipefail
cd "$(dirname "$0")/.."
umask 077
workspace="$(mktemp -d)"
trap 'rm -rf "$workspace"' EXIT

bash -n setup.sh scripts/setup.sh
bash setup.sh --help > "$workspace/help.log"
grep -q -- '--stack internal' "$workspace/help.log"
grep -q -- '--stack external' "$workspace/help.log"
grep -q -- '--initial-user-only' "$workspace/help.log"

# Alle Fragen werden wie am Terminal beantwortet: leere Werte übernehmen Defaults.
printf '\n\n\nn\nn\n\n' |
  bash setup.sh --stack internal --env-file "$workspace/internal.env" --config-only > "$workspace/internal.log" 2>&1
printf '\n\n\nn\n\n' |
  bash setup.sh --stack external --env-file "$workspace/external.env" --config-only > "$workspace/external.log" 2>&1

python3 - "$workspace" <<'PY'
import base64,os,stat,sys
from pathlib import Path
root=Path(sys.argv[1])
def read(name):
    path=root/name
    assert stat.S_IMODE(path.stat().st_mode)==0o600, name
    result={}
    for line in path.read_text().splitlines():
        if '=' in line:
            key,val=line.split('=',1)
            result[key]=val.strip("'").replace("\\'","'")
    return result
i=read("internal.env");e=read("external.env")
assert i["BM_SETUP_STACK"]=="internal"
assert e["BM_SETUP_STACK"]=="external"
assert len(i["DJANGO_SECRET_KEY"])>=50
assert len(e["PROTECTED_SECRET_KEY"])>=50
assert len(e["PUBLIC_SECRET_KEY"])>=50
assert e["PROTECTED_SECRET_KEY"]!=e["PUBLIC_SECRET_KEY"]
assert e["PROTECTED_DB_PASSWORD"]!=e["PUBLIC_DB_PASSWORD"]
assert len(base64.urlsafe_b64decode(i["DATA_ENCRYPTION_KEY"]))==32
assert len(base64.urlsafe_b64decode(e["PROTECTED_DATA_ENCRYPTION_KEY"]))==32
assert i["APPLICATION_URL"]=="https://localhost"
assert e["PUBLIC_HOST"]=="info.localhost"
for value in (i["DJANGO_SECRET_KEY"],i["POSTGRES_PASSWORD"],e["PROTECTED_SECRET_KEY"],e["PUBLIC_DB_PASSWORD"]):
    for path in root.glob("*.log"):
        assert value not in path.read_text(), "Geheimnis in Setup-Ausgabe"
PY

before="$(sha256sum "$workspace/internal.env" | cut -d' ' -f1)"
bash setup.sh --stack internal --env-file "$workspace/internal.env" --config-only > "$workspace/reuse.log" 2>&1
after="$(sha256sum "$workspace/internal.env" | cut -d' ' -f1)"
[[ "$before" == "$after" ]] || { echo "Fehler: .env wurde überschrieben." >&2; exit 1; }

# Fehlkonfigurationen und Hostwechsel müssen vor jeder Docker-Aktion scheitern.
if bash setup.sh --stack external --env-file "$workspace/internal.env" --check > "$workspace/cross.log" 2>&1; then
  echo "Fehler: gemischte interne/externe Konfiguration akzeptiert." >&2; exit 1
fi
chmod 644 "$workspace/internal.env"
if bash setup.sh --stack internal --env-file "$workspace/internal.env" --check > "$workspace/perms.log" 2>&1; then
  echo "Fehler: offen lesbare .env akzeptiert." >&2; exit 1
fi
chmod 600 "$workspace/internal.env"

printf 'https://example.invalid/not-a-host\n' |
  { if bash setup.sh --stack internal --env-file "$workspace/bad.env" --config-only > "$workspace/host.log" 2>&1; then
      echo "Fehler: URL als Hostname akzeptiert." >&2; exit 1
    fi; }
[[ ! -f "$workspace/bad.env" ]] || { echo "Ungültige .env erstellt." >&2; exit 1; }

# Die Ein-Konto-Nachholung muss für den externen Stack, ohne TTY oder
# mit einem reinen Prüfmodus VOR dem Docker-Aufruf abbrechen.
if bash setup.sh --stack external --initial-user-only --env-file "$workspace/external.env" > "$workspace/role.log" 2>&1; then
  echo "Fehler: externer Host durfte Bootstrap-Konto anlegen." >&2; exit 1
fi
grep -q 'nur im internen Fachsystem' "$workspace/role.log"
if bash setup.sh --stack internal --initial-user-only --check --env-file "$workspace/internal.env" > "$workspace/options.log" 2>&1; then
  echo "Fehler: Bootstrap- und Prüflauf fälschlich gleichzeitig erlaubt." >&2; exit 1
fi
if bash setup.sh --stack internal --initial-user-only --env-file "$workspace/internal.env" > "$workspace/tty.log" 2>&1; then
  echo "Fehler: Erstkontoanlage ohne interaktives Terminal zugelassen." >&2; exit 1
fi
grep -q 'interaktives Terminal' "$workspace/tty.log"
[[ "$(sha256sum "$workspace/internal.env" | cut -d' ' -f1)" == "$after" ]] || {
  echo "Fehler: Nachholmodus änderte private Konfiguration." >&2; exit 1;
}

# End-to-end Operator-CLI-Vertrag auf Pseudo-TTY mit gefälschtem Docker:
# Nur die bestehende Django-Bootstrap-Funktion aufrufen, niemals Migration,
# Build oder Neustart. Der Test startet ausdrücklich keine echten Container.
if command -v script >/dev/null 2>&1; then
  mkdir -p "$workspace/mockbin"
  cat > "$workspace/mockbin/docker" <<'MOCK'
#!/usr/bin/env bash
set -euo pipefail
args="$*"
printf '%s\n' "$args" >> "$BM_MOCK_DOCKER_LOG"
if [[ "$args" == "compose version" || "$args" == "info" ]]; then exit 0; fi
if [[ "$args" == *" config --quiet" ]]; then exit 0; fi
if [[ "$args" == *" ps --status running --services" ]]; then printf 'db\n'; exit 0; fi
if [[ "$args" == *" python manage.py shell -c "* ]]; then
  printf 'BM_INITIAL_USER_EXISTS=%s\n' "${BM_MOCK_EXISTS:-no}"
  exit 0
fi
if [[ "$args" == *" python manage.py bootstrap" ]]; then
  printf 'Django-Bootstrap wurde über den Operator-Einstieg aufgerufen.\n'
  exit 0
fi
printf 'Unzulässige Docker-Aktion im Bootstrap-Only-Modus.\n' >&2
exit 61
MOCK
  chmod 700 "$workspace/mockbin/docker"
  export BM_MOCK_DOCKER_LOG="$workspace/mock-docker.log"
  export PATH="$workspace/mockbin:$PATH"
  script -qec "bash setup.sh --stack internal --initial-user-only --env-file '$workspace/internal.env'" /dev/null > "$workspace/mock-bootstrap.log" 2>&1
  [[ "$(grep -c 'python manage.py bootstrap' "$BM_MOCK_DOCKER_LOG")" == 1 ]] || {
    echo "Fehler: Django-Erstkonto-Kommando nicht genau einmal aufgerufen." >&2; exit 1;
  }
  if grep -Eq '( migrate | build | up | down )' "$BM_MOCK_DOCKER_LOG"; then
    echo "Fehler: Nachholmodus darf Build, Migration oder Dienststart nicht ausführen." >&2; exit 1
  fi
  : > "$BM_MOCK_DOCKER_LOG"
  BM_MOCK_EXISTS=yes script -qec "bash setup.sh --stack internal --initial-user-only --env-file '$workspace/internal.env'" /dev/null > "$workspace/mock-existing.log" 2>&1
  if grep -q 'python manage.py bootstrap' "$BM_MOCK_DOCKER_LOG"; then
    echo "Fehler: initiales Konto trotz bestehender Benutzer erneut angelegt." >&2; exit 1
  fi
  unset BM_MOCK_DOCKER_LOG BM_MOCK_EXISTS
fi

# Auch nach manuellem, fehlerhaftem Exchange-Teilsetup keine stille Freigabe.
printf "EXCHANGE_PROTECTED_KEY='unpaired-secret'\n" >> "$workspace/internal.env"
if bash setup.sh --stack internal --env-file "$workspace/internal.env" --check > "$workspace/exchange.log" 2>&1; then
  echo "Fehler: unvollständige Exchange-Konfiguration akzeptiert." >&2; exit 1
fi

# Duplicate keys are ambiguous to Compose and must be rejected even when values match.
printf "SMTP_STARTTLS='false'\\n" >> "$workspace/internal.env"
if bash setup.sh --stack internal --env-file "$workspace/internal.env" --check > "$workspace/duplicate.log" 2>&1; then
  echo "Fehler: doppelte Umgebungsvariable akzeptiert." >&2; exit 1
fi
grep -q 'Doppelte Konfigurationsvariable' "$workspace/duplicate.log"

echo "Setup-Smoketests: interne/externe Schlüssel, Re-Run, Secrets, Berechtigungen, First-Admin-Grenzen und Negativfälle bestanden."
