# Gera os JSONs dos workflows do Ouro Bridge (n8n 2.19.x). Rodar: python3 n8n/build.py
import json, uuid, os, sys
TT_TEST = os.environ.get("TT_TEST", "")  # código de "Eventos de teste" do TikTok; vazio = produção
T={"__rl":True,"mode":"id","value":"3HxLTtbOps3mWweq","cachedResultName":"ouro_bridge_cliques"}
def schema(cols): return [{"id":c,"displayName":c,"required":False,"defaultMatch":False,"display":True,"type":"string","canBeUsedToMatch":True} for c in cols]
def mapping(vals): return {"mappingMode":"defineBelow","value":vals,"matchingColumns":[],"schema":schema(list(vals)),"attemptToConvertTypes":False,"convertFieldsToString":False}
def node(name,typ,ver,pos,params,**kw): return {"id":str(uuid.uuid5(uuid.NAMESPACE_URL,name)),"name":name,"type":typ,"typeVersion":ver,"position":pos,"parameters":params,**kw}
def hook(name,path): return node(name,"n8n-nodes-base.webhook",2.1,[0,0],{"httpMethod":"POST","path":path,"responseMode":"onReceived","options":{}},webhookId=str(uuid.uuid5(uuid.NAMESPACE_URL,path)))
def dt(name,pos,op,**p): return node(name,"n8n-nodes-base.dataTable",1.1,pos,{"resource":"row","operation":op,"dataTableId":T,**p,"options":{}})
def by_id(expr): return {"matchType":"allConditions","filters":{"conditions":[{"keyName":"id_curto","condition":"eq","keyValue":expr}]}}
def chain(*names): return {a:{"main":[[{"node":b,"type":"main","index":0}]]} for a,b in zip(names,names[1:])}
def s(v): return "={{ "+v+" }}"
B="$json.body"
IP=("(() => { const ip = (($json.headers['x-real-ip'] || $json.headers['x-forwarded-for'] || '') + '').split(',')[0].trim(); "
    "return /^(10\\.|127\\.|192\\.168\\.|172\\.(1[6-9]|2\\d|3[01])\\.|::1|fc|fd|fe80)/i.test(ip) ? '' : ip; })()")
ID=s(f"({B}.id_curto || '').toString().toLowerCase().slice(0, 32)")
def txt(f,n): return s(f"({B}.{f} || '').toString().slice(0, {n})")

# 1) Página carregou -> grava/atualiza o clique (upsert por id_curto)
wf1={"name":"Ouro Bridge - Captura de Clique (TikTok)",
 "nodes":[hook("Clique na bridge page","ouro-bridge-clique"),
   dt("Salvar clique",[260,0],"upsert",**by_id(ID),columns=mapping({
     "id_curto":ID,"ttclid":txt("ttclid",500),"ad":txt("ad",100),"produto":txt("produto",100),
     "timestamp_clique":s(f"{B}.timestamp || new Date().toISOString()"),
     "user_agent":s("($json.headers['user-agent'] || '').toString().slice(0, 500)"),"ip":s(IP),
     "pagina":txt("pagina",20),
     **{u:txt(u,300) for u in ["utm_source","utm_medium","utm_campaign","utm_content","utm_term"]}}))],
 "connections":chain("Clique na bridge page","Salvar clique"),
 "settings":{"executionOrder":"v1","saveDataSuccessExecution":"none","saveDataErrorExecution":"all"}}

# 2) Tocou no botão do WhatsApp -> marca whatsapp_em (hora do servidor, UTC)
wf3={"name":"Ouro Bridge - Toque no Botão WhatsApp (TikTok)",
 "nodes":[hook("Toque no botão","ouro-bridge-cta"),
   dt("Marcar hora do toque",[260,0],"upsert",**by_id(ID),columns=mapping({
     "id_curto":ID,"ttclid":txt("ttclid",500),"ad":txt("ad",100),"produto":txt("produto",100),
     "whatsapp_em":s("new Date().toISOString()")}))],
 "connections":chain("Toque no botão","Marcar hora do toque"),
 "settings":{"executionOrder":"v1","saveDataSuccessExecution":"none","saveDataErrorExecution":"all"}}

# 3) Leona avisa: lead mandou a 1a mensagem (com telefone) -> casa com o toque mais recente sem dono
prep=r"""// Chamado pela integração no início do fluxo da Leona: "telefone" ({phone_number}) e "mensagem" (1ª mensagem, via Manipulador).
const b = $input.first().json.body || {};
const telefone = String(b.telefone ?? (b.contact && b.contact.number) ?? '').replace(/\D/g, '');
if (!telefone) return [];
const agora = Date.now();
const JANELA_MIN = 10; // procura toques no botão nos últimos X minutos
const m = String(b.mensagem ?? '').match(/(?:\[ID:|c[oó]digo de atendimento:?\s*)([a-z0-9]{6,16})/i);
return [{ json: {
  telefone,
  codigo: m ? m[1].toLowerCase() : '',
  agora: new Date(agora).toISOString(),
  desde: new Date(agora - JANELA_MIN * 60 * 1000).toISOString(),
} }];"""
pick=r"""// 1º: se a mensagem trouxe o código de atendimento -> casamento EXATO por id_curto (qualquer horário).
// 2º: senão, entre os toques no botão sem telefone na janela, escolhe o mais recente.
const p = $('Preparar').first().json;
const todos = $input.all().map(i => i.json).filter(r => r.id_curto);
let escolhido = p.codigo ? todos.find(r => r.id_curto === p.codigo) : null;
let via = 'codigo';
if (!escolhido) {
  const rows = todos.filter(r => !r.telefone && r.whatsapp_em && r.whatsapp_em >= p.desde && r.whatsapp_em <= p.agora);
  if (!rows.length) return [];
  rows.sort((a, b) => (a.whatsapp_em < b.whatsapp_em ? 1 : -1));
  escolhido = rows[0];
  via = rows.length === 1 ? 'horario' : 'horario_' + rows.length + '_candidatos';
}
return [{ json: { id_curto: escolhido.id_curto, telefone: p.telefone, lead_em: p.agora, casado_por: via } }];"""
# ===== Evento "Contato" pro TikTok quando o lead é ligado ao clique =====
_priv = os.path.expanduser("~/.config/ouro-bridge/privado/rafael_nfe_teste.json")
_code = json.loads(open(_priv).read(), strict=False)["activeVersion"]["nodes"]
_sha = next(n for n in _code if n["name"] == "Code in JavaScript")["parameters"]["jsCode"]
SHA = _sha[:_sha.index("const phone =")].strip()   # sha256 puro (sem require), mesmo do fluxo de vendas
contato = SHA + r"""

// Lead do WhatsApp ligado a um clique do anúncio -> evento Contact no TikTok (Events API).
const TEST_EVENT_CODE = '__TT_TEST__'; // vazio = produção
const PIXEL = 'DAJ8RVRC77U250DBPJ3G';
const esc = $('Escolher clique').first().json;          // id_curto, telefone, casado_por
const row = ($input.first() && $input.first().json) || {}; // linha atualizada (ttclid, ip, ua...)
const tel = String(esc.telefone || '').replace(/\D/g, '');
if (!tel) return [];
const user = { phone: sha256('+' + tel), external_id: sha256(tel) };
if (row.ttclid) user.ttclid = row.ttclid;
if (row.ip) user.ip = row.ip;
if (row.user_agent) user.user_agent = row.user_agent;
const body = {
  event_source: 'web',
  event_source_id: PIXEL,
  data: [{
    event: 'Contact',
    event_time: Math.floor(Date.now() / 1000),
    event_id: 'lead_' + esc.id_curto,               // 1 Contato por clique (dedup no TikTok)
    user,
    properties: { content_type: 'product', contents: [{ content_id: row.produto || 'ebook', quantity: 1 }] },
    page: { url: 'https://josetelesfb-svg.github.io/whatspix-bridge/go.html' },
  }],
};
if (TEST_EVENT_CODE) body.test_event_code = TEST_EVENT_CODE;
return [{ json: { body } }];""".replace("__TT_TEST__", TT_TEST)
CRED={"httpHeaderAuth":{"id":"RuEJBMyXZeLbum8u","name":"TikTok Events API - jota-digital-tiktok"}}
n_contato = node("TikTok: montar Contato","n8n-nodes-base.code",2,[1300,0],{"jsCode":contato},onError="continueRegularOutput")
n_envia = node("TikTok: enviar Contato","n8n-nodes-base.httpRequest",4.2,[1560,0],
  {"method":"POST","url":"https://business-api.tiktok.com/open_api/v1.3/event/track/",
   "authentication":"genericCredentialType","genericAuthType":"httpHeaderAuth",
   "sendBody":True,"specifyBody":"json","jsonBody":"={{ JSON.stringify($json.body) }}","options":{}},
  onError="continueRegularOutput",credentials=CRED)

wf2={"name":"Ouro Bridge - Liga ID ao Telefone (TikTok)",
 "nodes":[hook("1a mensagem do lead (Leona)","ouro-bridge-lead"),
   node("Preparar","n8n-nodes-base.code",2,[260,0],{"jsCode":prep}),
   dt("Clique pelo código ou toques recentes",[520,0],"get",returnAll=True,matchType="anyCondition",
      filters={"conditions":[{"keyName":"id_curto","condition":"eq","keyValue":s("$json.codigo || '-'")},
                             {"keyName":"whatsapp_em","condition":"gte","keyValue":s("$json.desde")}]}),
   node("Escolher clique","n8n-nodes-base.code",2,[780,0],{"jsCode":pick}),
   dt("Gravar telefone no clique",[1040,0],"update",**by_id(s("$json.id_curto")),columns=mapping({
     "telefone":s("$json.telefone"),"lead_em":s("$json.lead_em"),"casado_por":s("$json.casado_por")})),
   n_contato, n_envia],
 "connections":chain("1a mensagem do lead (Leona)","Preparar","Clique pelo código ou toques recentes","Escolher clique","Gravar telefone no clique","TikTok: montar Contato","TikTok: enviar Contato"),
 "settings":{"executionOrder":"v1","saveDataSuccessExecution":"all","saveDataErrorExecution":"all"}}

# 4) Engajamento: a página manda o estado ACUMULADO (ficou 5s, rolou 50%, rolagem máx, tempo)
#    -> atualiza a linha do clique (update: se a linha não existir, não faz nada)
wf4={"name":"Ouro Bridge - Engajamento na Página (TikTok)",
 "nodes":[hook("Engajamento na página","ouro-bridge-engaj"),
   dt("Atualizar engajamento",[260,0],"update",**by_id(ID),columns=mapping({
     "ficou_5s":txt("ficou_5s",1),"rolou_50":txt("rolou_50",1),
     "scroll_max":txt("scroll_max",3),"tempo_s":txt("tempo_s",6),"video_tocou":txt("video_tocou",1)}))],
 "connections":chain("Engajamento na página","Atualizar engajamento"),
 "settings":{"executionOrder":"v1","saveDataSuccessExecution":"none","saveDataErrorExecution":"all"}}

for f,w in [("ouro-bridge-captura-clique",wf1),("ouro-bridge-toque-botao",wf3),("ouro-bridge-liga-id-telefone",wf2),("ouro-bridge-engajamento",wf4)]:
    json.dump(w,open(f"n8n/{f}.json","w"),ensure_ascii=False,indent=2)
print("ok")
