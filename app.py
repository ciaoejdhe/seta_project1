from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import urllib.request
import urllib.parse
import re
import os

# Dati fermata (già configurati per Piazza Giovanni Paolo II - RE)

FERMATA = {
“risultato”: “palina”,
“nome_fermata”: “PIAZZA GIOVANNI PAOLO II”,
“qm_palina”: “RE320162”,
“x”: “18”,
“y”: “16”,
“refresh”: “0”
}

PORT = int(os.environ.get(“PORT”, 8765))

def get_orari():
url = “https://www.setaweb.it/re/quantomanca”

```
data = urllib.parse.urlencode(FERMATA).encode("utf-8")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Content-Type": "application/x-www-form-urlencoded",
    "Referer": "https://www.setaweb.it/re/quantomanca",
    "Origin": "https://www.setaweb.it"
}

req = urllib.request.Request(url, data=data, headers=headers, method="POST")

with urllib.request.urlopen(req, timeout=10) as resp:
    html = resp.read().decode("utf-8")

return html
```

def parse_corse(html):
“”“Estrae le corse dall’HTML della pagina SETA”””
corse = []

```
# Cerca righe della tabella con linea, direzione e minuti
pattern = r'<td[^>]*>\s*<strong>(\w+)</strong>.*?</td>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(\d+|\*)</td>'
matches = re.findall(pattern, html, re.DOTALL)

for m in matches:
    linea = m[0].strip()
    direzione = re.sub(r'<[^>]+>', '', m[1]).strip()
    minuti = m[2].strip()
    
    corse.append({
        "linea": linea,
        "direzione": direzione,
        "minuti": minuti
    })

# Fallback: cerca pattern più semplice per i minuti
if not corse:
    pattern2 = r'(\d+)</td>\s*<td[^>]*>\s*(\d{1,2}:\d{2})'
    matches2 = re.findall(pattern2, html)
    for m in matches2[:5]:
        corse.append({
            "linea": "?",
            "direzione": "?",
            "minuti": m[0]
        })

return corse
```

def build_messaggio(corse):
if not corse:
return “🚌 Nessun bus trovato per Piazza Giovanni Paolo II”

```
lines = ["🚌 P.za Giovanni Paolo II"]
lines.append("─────────────────────")

for c in corse[:5]:
    minuti = c['minuti']
    if minuti == "*":
        arrivo = "orario non disponibile"
    elif minuti == "0":
        arrivo = "In arrivo!"
    elif minuti == "1":
        arrivo = "1 minuto"
    else:
        arrivo = f"{minuti} minuti"
    
    if c['linea'] != "?":
        lines.append(f"Linea {c['linea']} → {c['direzione']}")
        lines.append(f"   ⏱ {arrivo}")
    else:
        lines.append(f"⏱ {arrivo}")

return "\n".join(lines)
```

class Handler(BaseHTTPRequestHandler):

```
def do_GET(self):
    if self.path == "/bus":
        self.handle_bus()
    elif self.path == "/":
        self.send_json({"status": "ok", "fermata": FERMATA["nome_fermata"]})
    else:
        self.send_response(404)
        self.end_headers()

def handle_bus(self):
    try:
        html = get_orari()
        corse = parse_corse(html)
        messaggio = build_messaggio(corse)
        
        self.send_json({
            "ok": True,
            "messaggio": messaggio,
            "corse": corse
        })
    except Exception as e:
        self.send_json({
            "ok": False,
            "messaggio": f"❌ Errore: {str(e)}",
            "corse": []
        })

def send_json(self, data):
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    self.send_response(200)
    self.send_header("Content-Type", "application/json; charset=utf-8")
    self.send_header("Content-Length", str(len(body)))
    self.send_header("Access-Control-Allow-Origin", "*")
    self.end_headers()
    self.wfile.write(body)

def log_message(self, format, *args):
    pass  # Silenzia i log di default
```

if **name** == “**main**”:
server = HTTPServer((“0.0.0.0”, PORT), Handler)
print(f”Server avviato sulla porta {PORT}”)

server.serve_forever()
