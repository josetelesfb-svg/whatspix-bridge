# Gera e publica "Ouro Bridge - Números no ar (TikTok)".
# A cada 2 min lê no Leona (MCP list_connections) quais números estão conectados e guarda no staticData.
# GET /webhook/numeros-no-ar responde {ok:[telefones conectados], em:<iso>} com CORS, pra página sortear só entre eles.
# Uso: python3 build_numeros.py   (lê ~/.config/ouro-bridge/n8n_key e leona_mcp_token_n8n; o token vai só pra credencial do n8n)
import json, uuid, os, urllib.request

BASE = "https://n8n.srv1661587.hstgr.cloud/api/v1"
CFG = os.path.expanduser("~/.config/ouro-bridge/")
KEY = open(CFG + "n8n_key").read().strip()
NOME = "Ouro Bridge - Números no ar (TikTok)"
PATH = "numeros-no-ar"

def api(method, path, body=None):
    req = urllib.request.Request(BASE + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"X-N8N-API-KEY": KEY, "Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=60))

def node(name, typ, ver, pos, params, **kw): return {"id": str(uuid.uuid5(uuid.NAMESPACE_URL, name)), "name": name, "type": typ, "typeVersion": ver, "position": pos, "parameters": params, **kw}

def credencial():
    f = CFG + "cred_leona_mcp_n8n"
    if os.path.exists(f): return open(f).read().strip()
    tok = open(CFG + "leona_mcp_token_n8n").read().strip()
    c = api("POST", "/credentials", {"name": "Leona MCP - números no ar", "type": "httpHeaderAuth", "data": {"name": "Authorization", "value": "Bearer " + tok}})
    open(f, "w").write(c["id"]); os.chmod(f, 0o600)
    return c["id"]

def workflow(cred):
    LE = node("A cada 2 min", "n8n-nodes-base.scheduleTrigger", 1.2, [0, 0], {"rule": {"interval": [{"field": "minutes", "minutesInterval": 2}]}})
    MCP = node("Leona: conexões", "n8n-nodes-base.httpRequest", 4.2, [220, 0], {
        "method": "POST", "url": "https://apiaws.leonasolutions.io/mcp", "authentication": "genericCredentialType", "genericAuthType": "httpHeaderAuth",
        "sendHeaders": True, "headerParameters": {"parameters": [{"name": "Accept", "value": "application/json, text/event-stream"}]},
        "sendBody": True, "specifyBody": "json",
        "jsonBody": json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "list_connections", "arguments": {"limit": 100}}}),
        "options": {"timeout": 30000}}, credentials={"httpHeaderAuth": {"id": cred, "name": "Leona MCP - números no ar"}})
    GUARDA = node("Guarda no ar", "n8n-nodes-base.code", 2, [440, 0], {"jsCode": r"""
const d = $input.first().json;
const conns = JSON.parse(d.result.content[0].text).connections;
if (!conns || !conns.length) throw new Error('Leona devolveu 0 conexões');
const ok = conns.filter(c => c.status === 'connected' && c.active).map(c => c.phone_number);
const st = $getWorkflowStaticData('global');
const antes = st.ok || [];
st.ok = ok; st.em = new Date().toISOString();
return [{ json: { ok: ok.length, caiu: antes.filter(n => !ok.includes(n)), voltou: ok.filter(n => antes.length && !antes.includes(n)) } }];
"""})
    WH = node("GET numeros-no-ar", "n8n-nodes-base.webhook", 2.1, [0, 260], {"httpMethod": "GET", "path": PATH, "responseMode": "responseNode", "options": {}},
              webhookId=str(uuid.uuid5(uuid.NAMESPACE_URL, PATH)))
    LER = node("Lê cache", "n8n-nodes-base.code", 2, [220, 260], {"jsCode": r"""
const st = $getWorkflowStaticData('global');
// cache velho (>10 min) = não confiar: a página usa a lista fixa
const fresco = st.em && (Date.now() - Date.parse(st.em)) < 10 * 60 * 1000;
return [{ json: { ok: fresco ? st.ok : null, em: st.em || null } }];
"""})
    RESP = node("Responde", "n8n-nodes-base.respondToWebhook", 1.1, [440, 260], {"respondWith": "json", "responseBody": "={{ JSON.stringify($json) }}",
        "options": {"responseHeaders": {"entries": [{"name": "Access-Control-Allow-Origin", "value": "*"}, {"name": "Cache-Control", "value": "no-store"}]}}})
    con = {"A cada 2 min": {"main": [[{"node": "Leona: conexões", "type": "main", "index": 0}]]},
           "Leona: conexões": {"main": [[{"node": "Guarda no ar", "type": "main", "index": 0}]]},
           "GET numeros-no-ar": {"main": [[{"node": "Lê cache", "type": "main", "index": 0}]]},
           "Lê cache": {"main": [[{"node": "Responde", "type": "main", "index": 0}]]}}
    return {"name": NOME, "nodes": [LE, MCP, GUARDA, WH, LER, RESP], "connections": con, "settings": {"executionOrder": "v1", "saveDataSuccessExecution": "none"}}

if __name__ == "__main__":
    wf = workflow(credencial())
    ex = [w for w in api("GET", "/workflows?limit=250")["data"] if w["name"] == NOME]
    wid = ex[0]["id"] if ex else api("POST", "/workflows", wf)["id"]
    if ex: api("PUT", f"/workflows/{wid}", wf)
    api("POST", f"/workflows/{wid}/activate")
    print(wid)
