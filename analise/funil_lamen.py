import json, os, sys, urllib.request, urllib.parse, datetime as dt
KEY=open(os.path.expanduser('~/.config/ouro-bridge/n8n_key')).read().strip()
BASE='https://n8n.srv1661587.hstgr.cloud/api/v1/data-tables/3HxLTtbOps3mWweq/rows'
since=(dt.datetime.utcnow()-dt.timedelta(hours=60)).strftime('%Y-%m-%dT%H:%M:%S.000Z')
filt=json.dumps({"type":"and","filters":[{"columnName":"createdAt","condition":"gte","value":since}]},separators=(',',':'))
rows=[];cur=None
while True:
    q={'limit':250,'filter':filt}
    if cur: q['cursor']=cur
    r=json.load(urllib.request.urlopen(urllib.request.Request(BASE+'?'+urllib.parse.urlencode(q,quote_via=urllib.parse.quote),headers={'X-N8N-API-KEY':KEY})))
    rows+=r.get('data',[]); cur=r.get('nextCursor')
    if not cur: break
json.dump(rows,open(sys.argv[1],'w'))
print(len(rows))
