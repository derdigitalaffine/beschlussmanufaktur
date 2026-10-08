#!/usr/bin/env bash
set -euo pipefail
ci_prefix="bm-tls-ci-${GITHUB_RUN_ID:-local}"
ci_work=$(mktemp -d)
cleanup() {
  if [[ $? != 0 ]]; then docker logs "$ci_prefix-caddy"; docker logs "$ci_prefix-agent"; fi
  docker rm -f "$ci_prefix-caddy" "$ci_prefix-agent" >/dev/null 2>&1 || true
  docker volume rm "$ci_prefix-runtime" "$ci_prefix-data" >/dev/null 2>&1 || true
  docker network rm "$ci_prefix-network" >/dev/null 2>&1 || true
  rm -rf "$ci_work"
}
trap cleanup EXIT
docker network create "$ci_prefix-network" >/dev/null
docker volume create "$ci_prefix-runtime" >/dev/null
docker volume create "$ci_prefix-data" >/dev/null
docker run -d --name "$ci_prefix-caddy" --network "$ci_prefix-network" --network-alias caddy -p 127.0.0.1:18443:443 -v "$PWD/deploy/Caddyfile:/etc/caddy/Caddyfile:ro" -v "$PWD/backend/static:/srv/static:ro" -v "$ci_prefix-runtime:/runtime" -v "$ci_prefix-data:/data" caddy:2-alpine >/dev/null
docker run -d --name "$ci_prefix-agent" --network "$ci_prefix-network" --network-alias tls-agent -p 127.0.0.1:18070:8070 -e TLS_AGENT_KEY=ci-only-agent-key-at-least-thirty-two-characters -e SITE_ADDRESS=localhost -v "$ci_prefix-runtime:/runtime" beschlussmanufaktur-tls-agent >/dev/null
for attempt in $(seq 1 30); do
  if curl -fsS http://127.0.0.1:18070/health >/dev/null; then break; fi
  sleep 1
done
python - <<'PY'
import json,time,uuid,hmac,hashlib,urllib.request,urllib.error
key=b'ci-only-agent-key-at-least-thirty-two-characters'
data={'id':str(uuid.uuid4()),'issued_at':int(time.time()),'role':'internal','hostname':'localhost','mode':'internal','proof':'','expected_ips':[],'contact':'','certificate':'','private_key':''}
def request(value,signed=True):
    raw=json.dumps(value).encode();headers={'Content-Type':'application/json'}
    if signed:headers['X-BM-TLS-Signature']=hmac.new(key,raw,hashlib.sha256).hexdigest()
    try:
        with urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:18070/plan',data=raw,headers=headers),timeout=30) as r:return r.status,json.load(r)
    except urllib.error.HTTPError as e:return e.code,{}
assert request(data,False)[0]==400
assert request(data)==(200,{'status':'applied','id':data['id']})
assert request(data)[0]==200
assert request(dict(data,id=str(uuid.uuid4()),hostname='localhost\n{'))[0]==400
print('Signed isolated agent: real Caddy reload, replay and rejection passed.')
PY
docker cp "$ci_prefix-caddy:/data/caddy/pki/authorities/local/root.crt" "$ci_work/root.crt" >/dev/null
curl --cacert "$ci_work/root.crt" -fsS https://localhost:18443/static/app.css -o /dev/null
