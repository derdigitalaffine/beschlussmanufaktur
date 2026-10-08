"""Isolated host agent. No database, Docker socket, shell execution or arbitrary Caddyfile."""
import hashlib,hmac,http.client,json,os,socket,time,uuid
from pathlib import Path
from http.server import BaseHTTPRequestHandler,HTTPServer
from tls_material import hostname,certificate,dns_preflight

ROOT=Path(os.environ.get('TLS_RUNTIME','/runtime'))
KEY=os.environ.get('TLS_AGENT_KEY','').encode()

class UnixConnection(http.client.HTTPConnection):
    def connect(self):
        self.sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);self.sock.settimeout(20);self.sock.connect(str(ROOT/'admin.sock'))

def caddy(path,body,content_type):
    conn=UnixConnection('localhost')
    try:
        conn.request('POST',path,body,{'Content-Type':content_type,'Host':'localhost'});r=conn.getresponse();raw=r.read(1_000_000)
        if r.status>=300:raise ValueError('Caddy-Konfiguration abgewiesen.')
        return json.loads(raw) if raw else {}
    finally:conn.close()

def initial():
    if os.environ.get('TLS_AGENT_ROLE','internal')=='internal':return {hostname(os.environ.get('SITE_ADDRESS','localhost')):{'role':'internal','mode':'internal'}}
    return {hostname(os.environ.get('PROTECTED_HOST','gremien.localhost')):{'role':'protected','mode':'internal'},hostname(os.environ.get('PUBLIC_HOST','info.localhost')):{'role':'public','mode':'internal'}}

def render(sites):
    text='{\n admin unix//runtime/admin.sock {\n  origins localhost\n }\n}\n'
    upstreams={'internal':'backend:8000','protected':'protected:8000','public':'public:8000'}
    for host,plan in sorted(sites.items()):
        hostname(host);upstream=upstreams[plan['role']];mode=plan['mode']
        tls='tls internal'
        if mode=='import':tls='tls '+plan['cert_path']+' '+plan['key_path']
        elif mode=='letsencrypt':tls='tls {\n issuer acme {\n  ca https://acme-v02.api.letsencrypt.org/directory\n  email '+plan['contact']+'\n }\n}'
        text+=host+' {\n '+tls+'\n encode zstd gzip\n handle_path /betrieb/tls-agent/* {\n  reverse_proxy tls-agent:8070\n }\n handle_path /static/* {\n  root * /srv/static\n  file_server\n }\n handle {\n  reverse_proxy '+upstream+'\n }\n}\n'
    return text

def load_state():return json.loads((ROOT/'state.json').read_text()) if (ROOT/'state.json').exists() else {'sites':initial(),'applied':{}}

def apply(data):
    required={'id','issued_at','role','hostname','mode','proof','expected_ips','contact','certificate','private_key'}
    if not isinstance(data,dict) or set(data)!=required:raise ValueError('Ungültiger Vertrag.')
    identifier=str(uuid.UUID(data['id']));host=hostname(data['hostname'])
    if abs(time.time()-data['issued_at'])>300:raise ValueError('Auftrag abgelaufen.')
    allowed={'internal'} if os.environ.get('TLS_AGENT_ROLE','internal')=='internal' else {'public','protected'}
    if data['role'] not in allowed or data['mode'] not in ('internal','letsencrypt','import'):raise ValueError('Unzulässiger Zielbereich.')
    stable={k:v for k,v in data.items() if k!='issued_at'};digest=hashlib.sha256(json.dumps(stable,sort_keys=True).encode()).hexdigest();state=load_state()
    if identifier in state['applied']:
        if state['applied'][identifier]!=digest:raise ValueError('Auftrag widersprüchlich.')
        return {'status':'applied','id':identifier}
    plan={'role':data['role'],'mode':data['mode']}
    if host in state['sites'] and state['sites'][host]['role']!=data['role']:raise ValueError('Bestehendes Routing darf nicht einem anderen Dienst zugeordnet werden.')
    if data['mode']=='letsencrypt':
        import re
        if not re.fullmatch(r'[A-Za-z0-9_.+-]+@[A-Za-z0-9.-]+',data['contact']):raise ValueError('ACME-Kontakt ungültig.')
        dns_preflight(host,data['proof'],data['expected_ips']);plan['contact']=data['contact']
    elif data['mode']=='import':
        certificate(data['certificate'],data['private_key'],host)
        for name,value in [('cert',data['certificate']),('key',data['private_key'])]:
            path=ROOT/(name+'-'+identifier+'.pem');path.write_text(value);path.chmod(0o600);plan[name+'_path']=str(path)
    elif data['certificate'] or data['private_key']:raise ValueError('Unerwartetes Schlüsselmaterial.')
    sites={**state['sites'],host:plan};config=render(sites);adapted=caddy('/adapt',config.encode(),'text/caddyfile');caddy('/load',json.dumps(adapted['config']).encode(),'application/json')
    state['sites']=sites;state['applied'][identifier]=digest
    # Retain a bounded idempotency ledger; timestamps prohibit old unsigned replay.
    state['applied']=dict(list(state['applied'].items())[-500:])
    temp=ROOT/'state.new';temp.write_text(json.dumps(state));temp.chmod(0o600);temp.replace(ROOT/'state.json')
    (ROOT/'last-good.Caddyfile').write_text(config)
    return {'status':'applied','id':identifier}

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def reply(self,status,value):
        raw=json.dumps(value).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    def do_GET(self):self.reply(200 if self.path=='/health' else 404,{'status':'ready'})
    def do_POST(self):
        try:
            length=int(self.headers.get('Content-Length','0'))
            if self.path!='/plan' or len(KEY)<32 or not 0<length<=250000:raise ValueError
            raw=self.rfile.read(length)
            if not hmac.compare_digest(hmac.new(KEY,raw,hashlib.sha256).hexdigest(),self.headers.get('X-BM-TLS-Signature','')):raise ValueError
            self.reply(200,apply(json.loads(raw)))
        except Exception:self.reply(400,{'error':'Auftrag abgewiesen; vorherige Caddy-Konfiguration bleibt erhalten.'})

if __name__=='__main__':
    ROOT.mkdir(parents=True,exist_ok=True)
    # Recover the last accepted desired state after a host restart.
    if (ROOT/'state.json').exists():
        for attempt in range(30):
            try:
                adapted=caddy('/adapt',render(load_state()['sites']).encode(),'text/caddyfile');caddy('/load',json.dumps(adapted['config']).encode(),'application/json');break
            except (OSError,ValueError):time.sleep(2)
    HTTPServer(('0.0.0.0',8070),Handler).serve_forever()
