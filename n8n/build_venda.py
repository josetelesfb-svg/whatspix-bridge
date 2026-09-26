# Monta a CÓPIA "Rafael NFE - TikTok" a partir do original (lido do n8n e guardado FORA do repo,
# porque o original contém tokens). Saída também fica fora do repo. Rodar: python3 n8n/build_venda.py
import json, os, re, uuid, copy, sys
PRIV = os.path.expanduser("~/.config/ouro-bridge/privado")
# Base = VERSÃO PUBLICADA do "Rafael NFE Teste" (é o que o chatbot de pães usa; o rascunho dele está com
# a ligação Utmify -> Code desconectada, por isso NÃO usar os nodes/connections do rascunho).
_base = json.loads(open(f"{PRIV}/rafael_nfe_teste.json").read(), strict=False)
orig = {"name": _base["name"], "settings": _base["settings"],
        "nodes": _base["activeVersion"]["nodes"], "connections": _base["activeVersion"]["connections"]}
PIXEL = "DAJ8RVRC77U250DBPJ3G"
CLIQUES = {"__rl": True, "mode": "id", "value": "3HxLTtbOps3mWweq", "cachedResultName": "ouro_bridge_cliques"}
VENDAS = {"__rl": True, "mode": "id", "value": "m97cJYWpMzidJT1e", "cachedResultName": "ouro_bridge_vendas"}
CRED = {"httpHeaderAuth": {"id": "RuEJBMyXZeLbum8u", "name": "TikTok Events API - jota-digital-tiktok"}}
TEST_EVENT_CODE = sys.argv[1] if len(sys.argv) > 1 else ""
TT_TOKEN_PADRAO = open(os.path.expanduser("~/.config/ouro-bridge/tiktok_token")).read().strip()

# função sha256 pura (a mesma do fluxo original, que não usa require)
code_orig = next(n for n in orig["nodes"] if n["name"] == "Code in JavaScript")["parameters"]["jsCode"]
sha = code_orig[:code_orig.index("const phone =")].strip()

montar = sha + r"""

// ===== Monta o evento CompletePayment pro TikTok Events API =====
const TEST_EVENT_CODE = '__TEST__'; // vazio = produção; com código = aparece só em "Eventos de teste"
const hookQ = $('Webhook').first().json.query || {};
const PIXEL = hookQ.tt_pixel || '__PIXEL__';           // &tt_pixel= na URL da integração (opcional)
const TOKEN = hookQ.tt_token || '__TOKEN__';           // &tt_token= na URL da integração (opcional)
let primeiro = null;
try { primeiro = $('TikTok: buscar clique').first().json; } catch (e) {}
const clique = primeiro && primeiro.id_curto ? primeiro : null; // linha da tabela de cliques (ou nada)
const hook = $('Webhook').first().json;
const tel = String((hook.body.contact && hook.body.contact.number) || '').replace(/\D/g, '');
const ia = JSON.parse($('Message a model').first().json.content[0].text.replace(/```json|```/g, '').trim());
const valor = Number(ia.valor) || 0;
const produto = (clique && clique.produto) || (hook.query && hook.query.name) || 'ebook';
let orderId = '';
try { orderId = $('Edit Fields').first().json.orderId || ''; } catch (e) {}
const eventId = orderId || ('venda_' + tel + '_' + Date.now()); // mesmo nº de pedido da Utmify

const user = { phone: sha256('+' + tel), external_id: sha256(tel) };
if (clique) {
  if (clique.ttclid) user.ttclid = clique.ttclid;
  if (clique.ip) user.ip = clique.ip;
  if (clique.user_agent) user.user_agent = clique.user_agent;
}
const body = {
  event_source: 'web',
  event_source_id: PIXEL,
  data: [{
    event: 'CompletePayment',
    event_time: Math.floor(Date.now() / 1000),
    event_id: eventId,
    user,
    properties: {
      currency: 'BRL',
      value: valor,
      content_type: 'product',
      contents: [{ content_id: produto, content_name: (hook.query && hook.query.name) || produto, quantity: 1, price: valor }],
    },
    page: { url: 'https://josetelesfb-svg.github.io/whatspix-bridge/go.html' },
  }],
};
if (TEST_EVENT_CODE) body.test_event_code = TEST_EVENT_CODE;

return [{ json: { body, token: TOKEN, log: {
  venda_em: new Date().toISOString(), telefone: tel,
  id_curto: clique ? clique.id_curto : '', ttclid: clique ? (clique.ttclid || '') : '',
  ad: clique ? (clique.ad || '') : '', produto, valor: String(valor),
  casado_por: clique ? (clique.casado_por || '') : 'sem_clique',
  event_id: eventId, teste: TEST_EVENT_CODE ? 'sim' : 'nao',
} } }];"""
montar = montar.replace("__TEST__", TEST_EVENT_CODE).replace("__PIXEL__", PIXEL).replace("__TOKEN__", TT_TOKEN_PADRAO)

def schema(cols): return [{"id":c,"displayName":c,"required":False,"defaultMatch":False,"display":True,"type":"string","canBeUsedToMatch":True} for c in cols]
def nid(n): return str(uuid.uuid5(uuid.NAMESPACE_URL, "tiktok-venda/" + n))
TEL = "={{ String(($('Webhook').first().json.body.contact || {}).number || '').replace(/\\D/g, '') }}"
LOGC = ["venda_em","telefone","id_curto","ttclid","ad","produto","valor","casado_por","event_id","teste"]
tiktok = [
 {"id":nid("buscar"),"name":"TikTok: buscar clique","type":"n8n-nodes-base.dataTable","typeVersion":1.1,"position":[0,0],
  "alwaysOutputData":True,"onError":"continueRegularOutput",
  "parameters":{"resource":"row","operation":"get","dataTableId":CLIQUES,"matchType":"allConditions",
    "filters":{"conditions":[{"keyName":"telefone","condition":"eq","keyValue":TEL}]},
    "limit":1,"orderBy":True,"orderByColumn":"lead_em","orderByDirection":"DESC","options":{}}},
 {"id":nid("montar"),"name":"TikTok: montar evento","type":"n8n-nodes-base.code","typeVersion":2,"position":[220,0],
  "onError":"continueRegularOutput","parameters":{"jsCode":montar}},
 {"id":nid("enviar"),"name":"TikTok: enviar CompletePayment","type":"n8n-nodes-base.httpRequest","typeVersion":4.2,"position":[440,0],
  "onError":"continueRegularOutput",
  "parameters":{"method":"POST","url":"https://business-api.tiktok.com/open_api/v1.3/event/track/",
    "sendHeaders":True,"headerParameters":{"parameters":[{"name":"Access-Token","value":"={{ $json.token }}"}]},
    "sendBody":True,"specifyBody":"json","jsonBody":"={{ JSON.stringify($json.body) }}","options":{}}},
 {"id":nid("registrar"),"name":"TikTok: registrar venda","type":"n8n-nodes-base.dataTable","typeVersion":1.1,"position":[660,0],
  "onError":"continueRegularOutput",
  "parameters":{"resource":"row","operation":"insert","dataTableId":VENDAS,
    "columns":{"mappingMode":"defineBelow","value":{**{c:"={{ $('TikTok: montar evento').first().json.log."+c+" }}" for c in LOGC},
       "tiktok_code":"={{ String($json.code ?? '') }}","tiktok_msg":"={{ String($json.message ?? $json.error?.message ?? '').slice(0, 300) }}"},
      "matchingColumns":[],"schema":schema(LOGC+["tiktok_code","tiktok_msg"]),"attemptToConvertTypes":False,"convertFieldsToString":False},
    "options":{}}},
]
def link(conn, a, b):
    conn.setdefault(a, {"main":[[]]})["main"][0].append({"node":b,"type":"main","index":0})

def build_copia():
    wf = copy.deepcopy(orig)
    # tira o envio pra Meta (lead do TikTok não conta venda pra Meta) e liga Code -> planilha direto
    wf["nodes"] = [n for n in wf["nodes"] if n["name"] != "HTTP Request2"]
    conn = wf["connections"]; conn.pop("HTTP Request2", None)
    conn["Code in JavaScript"] = {"main":[[{"node":"Append row in sheet","type":"main","index":0}]]}
    # webhook próprio da cópia
    for n in wf["nodes"]:
        if n["name"] == "Webhook":
            n["parameters"]["path"] = str(uuid.uuid5(uuid.NAMESPACE_URL, "rafael-nfe-tiktok"))
            n["webhookId"] = str(uuid.uuid5(uuid.NAMESPACE_URL, "rafael-nfe-tiktok-hook"))
            base = n["position"]
    # ramo TikTok em paralelo, saindo do Code (depois da Utmify)
    cx, cy = next(n for n in wf["nodes"] if n["name"] == "Code in JavaScript")["position"]
    for i, t in enumerate(copy.deepcopy(tiktok)):
        t["position"] = [cx + 220 * (i + 1), cy + 260]; wf["nodes"].append(t)
    # If (comprovante válido) -> TikTok: buscar clique -> If1 (resto igual ao original)
    main_if = conn["If"]["main"]
    assert [c["node"] for c in main_if[0]] == ["If1"], main_if
    main_if[0] = [{"node":"TikTok: buscar clique","type":"main","index":0}]
    link(conn, "TikTok: buscar clique", "If1")
    link(conn, "Code in JavaScript", "TikTok: montar evento")
    nomes = [t["name"] for t in tiktok][1:]
    for a, b in zip(nomes, nomes[1:]): link(conn, a, b)
    # Utmify: trackingParameters com as UTMs do anúncio guardadas no clique
    utm = next(n for n in wf["nodes"] if n["name"] == "HTTP Request1")
    body = utm["parameters"]["jsonBody"]
    i = body.index('"trackingParameters"'); j = body.index("\n  }", i) + len("\n  }")  # fecha o objeto (tem {{ }} dentro)
    utm["parameters"]["jsonBody"] = body[:i] + (
      '"trackingParameters": {{ JSON.stringify((() => { let c = {}; '
      "try { c = $('TikTok: buscar clique').first().json || {}; } catch (e) {} "
      "const v = x => (x ? String(x) : null); "
      "return { src: null, sck: null, utm_source: v(c.utm_source) || 'tiktok', utm_campaign: v(c.utm_campaign), "
      "utm_medium: v(c.utm_medium), utm_content: v(c.utm_content), utm_term: v(c.utm_term) }; })()) }}") + body[j:]
    return {"name": "Leona - Valida Comprovante - Rafael NFE - TikTok", "nodes": wf["nodes"],
            "connections": conn, "settings": {k: v for k, v in orig["settings"].items() if k in ("executionOrder",)}}

def build_teste():
    # Fluxo de TESTE isolado: simula Webhook + resposta do Claude, e roda só o ramo TikTok.
    fake = [
     {"id":nid("t-hook"),"name":"Webhook","type":"n8n-nodes-base.webhook","typeVersion":2.1,"position":[-440,0],
      "webhookId":str(uuid.uuid5(uuid.NAMESPACE_URL,"teste-venda-tiktok")),
      "parameters":{"httpMethod":"POST","path":"ouro-bridge-teste-venda","responseMode":"lastNode","options":{}}},
     {"id":nid("t-ia"),"name":"Message a model","type":"n8n-nodes-base.code","typeVersion":2,"position":[-220,0],
      "parameters":{"jsCode":"const v = $('Webhook').first().json.body.valor || '19.90';\nreturn [{ json: { content: [{ text: JSON.stringify({ valido: true, valor: Number(v) }) }] } }];"}},
    ]
    conn = {}
    link(conn, "Webhook", "Message a model"); link(conn, "Message a model", "TikTok: buscar clique")
    nomes = [t["name"] for t in tiktok]
    for a, b in zip(nomes, nomes[1:]): link(conn, a, b)
    return {"name": "Ouro Bridge - TESTE venda TikTok (apagar depois)", "nodes": fake + copy.deepcopy(tiktok),
            "connections": conn, "settings": {"executionOrder": "v1"}}

json.dump(build_copia(), open(f"{PRIV}/rafael_nfe_tiktok.json","w"), ensure_ascii=False, indent=2)
json.dump(build_teste(), open(f"{PRIV}/teste_venda_tiktok.json","w"), ensure_ascii=False, indent=2)
print("ok  test_event_code =", repr(TEST_EVENT_CODE))
