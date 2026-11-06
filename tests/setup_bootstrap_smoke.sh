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

# Auch nach manuellem, fehlerhaftem Exchange-Teilsetup keine stille Freigabe.
printf "EXCHANGE_PROTECTED_KEY='unpaired-secret'\n" >> "$workspace/internal.env"
if bash setup.sh --stack internal --env-file "$workspace/internal.env" --check > "$workspace/exchange.log" 2>&1; then
  echo "Fehler: unvollständige Exchange-Konfiguration akzeptiert." >&2; exit 1
fi

echo "Setup-Smoketests: interne/externe Schlüssel, Re-Run, Secrets, Berechtigungen und Negativfälle bestanden."
