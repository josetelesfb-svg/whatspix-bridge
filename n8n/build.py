# Gera os JSONs dos workflows do Ouro Bridge (n8n 2.19.x). Rodar: python3 n8n/build.py
import json, uuid
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
     "user_agent":s("($json.headers['user-agent'] || '').toString().slice(0, 500)"),"ip":s(IP)}))],
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
prep=r"""// Chamado pela integração no início do fluxo da Leona. Precisa de "telefone" ({phone_number}).
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
pick=r"""// Entre os toques no botão sem telefone na janela, escolhe o código (se veio) ou o mais recente.
const p = $('Preparar').first().json;
const rows = $input.all().map(i => i.json).filter(r => r.id_curto && r.whatsapp_em && r.whatsapp_em <= p.agora);
if (!rows.length) return [];
let escolhido = p.codigo ? rows.find(r => r.id_curto === p.codigo) : null;
let via = 'codigo';
if (!escolhido) {
  rows.sort((a, b) => (a.whatsapp_em < b.whatsapp_em ? 1 : -1));
  escolhido = rows[0];
  via = rows.length === 1 ? 'horario' : 'horario_' + rows.length + '_candidatos';
}
return [{ json: { id_curto: escolhido.id_curto, telefone: p.telefone, lead_em: p.agora, casado_por: via } }];"""
wf2={"name":"Ouro Bridge - Liga ID ao Telefone (TikTok)",
 "nodes":[hook("1a mensagem do lead (Leona)","ouro-bridge-lead"),
   node("Preparar","n8n-nodes-base.code",2,[260,0],{"jsCode":prep}),
   dt("Toques recentes sem dono",[520,0],"get",returnAll=True,matchType="allConditions",
      filters={"conditions":[{"keyName":"telefone","condition":"isEmpty"},
                             {"keyName":"whatsapp_em","condition":"gte","keyValue":s("$json.desde")}]}),
   node("Escolher clique","n8n-nodes-base.code",2,[780,0],{"jsCode":pick}),
   dt("Gravar telefone no clique",[1040,0],"update",**by_id(s("$json.id_curto")),columns=mapping({
     "telefone":s("$json.telefone"),"lead_em":s("$json.lead_em"),"casado_por":s("$json.casado_por")}))],
 "connections":chain("1a mensagem do lead (Leona)","Preparar","Toques recentes sem dono","Escolher clique","Gravar telefone no clique"),
 "settings":{"executionOrder":"v1","saveDataSuccessExecution":"all","saveDataErrorExecution":"all"}}

for f,w in [("ouro-bridge-captura-clique",wf1),("ouro-bridge-toque-botao",wf3),("ouro-bridge-liga-id-telefone",wf2)]:
    json.dump(w,open(f"n8n/{f}.json","w"),ensure_ascii=False,indent=2)
print("ok")
