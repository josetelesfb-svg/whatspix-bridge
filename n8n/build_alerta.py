# Alerta de chip desconectado: e-mail da Leona (Gmail/IMAP) -> Telegram. Rodar: python3 n8n/build_alerta.py
import json, uuid
IMAP = {"imap": {"id": "2eq5nJ3RMs9KFvyR", "name": "Gmail IMAP - alertas Leona"}}
TG = {"telegramApi": {"id": "jP81FyGHqycTwAt9", "name": "Telegram - bot de alertas (JOTA)"}}
CHAT_ID = "1478620951"  # mesmo chat dos alertas de comprovante
def nid(n): return str(uuid.uuid5(uuid.NAMESPACE_URL, "alerta-chip/" + n))

parse = r"""// Lê o e-mail da Leona e monta o texto do alerta. E-mails que não são de (des)conexão são ignorados.
const out = [];
for (const it of $input.all()) {
  const e = it.json;
  const assunto = String(e.subject || '');
  const html = String(e.textHtml || '');
  const texto = String(e.textPlain || html.replace(/<br\s*\/?>/gi, '\n').replace(/<[^>]+>/g, ' ').replace(/&nbsp;/g, ' '));
  const t = (assunto + '\n' + texto).replace(/[ \t]+/g, ' ');
  const caiu = /desconectad/i.test(t);
  const voltou = !caiu && /reconectad|conectada novamente|voltou a (se )?conectar/i.test(t);
  if (!caiu && !voltou) continue;
  const ROT = '(?:Inst[âa]ncia|N[úu]mero|Desconectada em|Reconectada em|Conectada em|Acesse)';
  const pega = (rot) => { const m = t.match(new RegExp('(?:^|\\n|\\s)' + rot + '\\s*:\\s*(.+?)(?=\\s*' + ROT + '\\s*:|\\s*Acesse|\\n|$)')); return m ? m[1].trim() : ''; };
  const inst = pega('Inst[âa]ncia') || assunto.split(':').slice(1).join(':').trim();
  const num = (pega('N[úu]mero').match(/\d{10,13}/) || [''])[0];
  const quando = pega('(?:Desconectada|Reconectada|Conectada) em');
  const fmt = num.length === 13 ? `+${num.slice(0,2)} ${num.slice(2,4)} ${num.slice(4,9)}-${num.slice(9)}`
            : num.length === 12 ? `+${num.slice(0,2)} ${num.slice(2,4)} ${num.slice(4,8)}-${num.slice(8)}` : num;
  const texto_msg = caiu
    ? `🚨 CHIP CAIU\n\n📌 ${inst}\n📱 ${fmt || 'número não identificado'}\n⏰ ${quando || new Date().toLocaleString('pt-BR', {timeZone: 'America/Sao_Paulo'})}\n\nReconecte na Leona o quanto antes.`
    : `✅ Chip reconectado\n\n📌 ${inst}\n📱 ${fmt}\n⏰ ${quando}`;
  out.push({ json: { texto_msg, caiu, instancia: inst, numero: num } });
}
return out;"""

def code(name, pos): return {"id": nid(name), "name": name, "type": "n8n-nodes-base.code", "typeVersion": 2, "position": pos, "parameters": {"jsCode": parse}}
def telegram(name, pos): return {"id": nid(name), "name": name, "type": "n8n-nodes-base.telegram", "typeVersion": 1.2, "position": pos,
    "credentials": TG, "parameters": {"resource": "message", "operation": "sendMessage", "chatId": CHAT_ID,
    "text": "={{ $json.texto_msg }}", "additionalFields": {"appendAttribution": False}}}

principal = {"name": "Alerta - Chip desconectado (Leona → Telegram)",
 "nodes": [
  {"id": nid("imap"), "name": "E-mail da Leona", "type": "n8n-nodes-base.emailReadImap", "typeVersion": 2.1, "position": [0, 0],
   "credentials": IMAP, "parameters": {"mailbox": "INBOX", "postProcessAction": "nothing", "format": "simple",
     "options": {"customEmailConfig": '["UNSEEN", ["FROM", "noreply@leonasolutions.io"]]'}}},
  code("Montar alerta", [240, 0]), telegram("Avisar no Telegram", [480, 0])],
 "connections": {"E-mail da Leona": {"main": [[{"node": "Montar alerta", "type": "main", "index": 0}]]},
                 "Montar alerta": {"main": [[{"node": "Avisar no Telegram", "type": "main", "index": 0}]]}},
 "settings": {"executionOrder": "v1", "saveDataSuccessExecution": "all", "saveDataErrorExecution": "all"}}

teste = {"name": "Alerta - Chip desconectado (TESTE, apagar depois)",
 "nodes": [
  {"id": nid("hook"), "name": "E-mail simulado", "type": "n8n-nodes-base.webhook", "typeVersion": 2.1, "position": [0, 0],
   "webhookId": nid("hook-id"), "parameters": {"httpMethod": "POST", "path": "alerta-chip-teste", "responseMode": "lastNode", "options": {}}},
  {"id": nid("unwrap"), "name": "Formato do e-mail", "type": "n8n-nodes-base.code", "typeVersion": 2, "position": [200, 0],
   "parameters": {"jsCode": "return $input.all().map(i => ({ json: i.json.body }));"}},
  code("Montar alerta", [400, 0]), telegram("Avisar no Telegram", [600, 0])],
 "connections": {"E-mail simulado": {"main": [[{"node": "Formato do e-mail", "type": "main", "index": 0}]]},
                 "Formato do e-mail": {"main": [[{"node": "Montar alerta", "type": "main", "index": 0}]]},
                 "Montar alerta": {"main": [[{"node": "Avisar no Telegram", "type": "main", "index": 0}]]}},
 "settings": {"executionOrder": "v1"}}
json.dump(principal, open("n8n/alerta-chip.json", "w"), ensure_ascii=False, indent=2)
json.dump(teste, open("n8n/alerta-chip-teste.json", "w"), ensure_ascii=False, indent=2)
print("ok")
