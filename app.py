from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import urllib.request
import urllib.parse
import re
import os

FERMATA = {
    "risultato": "palina",
    "nome_fermata": "PIAZZA GIOVANNI PAOLO II",
    "qm_palina": "RE320162",
    "x": "18",
    "y": "16",
    "refresh": "0"
}

PORT = int(os.environ.get("PORT", 8765))

def get_orari():
    url = "https://www.setaweb.it/re/quantomanca"
    data = urllib.parse.urlencode(FERMATA).encode("utf-8")
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/x-www-form-urlencoded",
        "Referer": "https://www.setaweb.it/re/quantomanca",
        "Origin": "https://www.setaweb.it"
    }
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=10) as resp:
        html = resp.read().decode("utf-8")
    return html

def parse_corse(html):
    corse = []
    # Cerca le righe della tabella <tr>
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.DOTALL)
    for row in rows:
        cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
        if len(cells) < 3:
            continue
        # Prima cella: numero linea (es. 07, 13...)
        linea = re.sub(r'<[^>]+>', '', cells[0]).strip()
        if not linea or not re.match(r'^\d+', linea):
            continue
        # Seconda cella: direzione
        direzione = re.sub(r'<[^>]+>', '', cells[1]).strip()
        # Terza cella: minuti
        minuti = re.sub(r'<[^>]+>', '', cells[2]).strip()
        if not minuti:
            minuti = "*"
        corse.append({"linea": linea, "direzione": direzione, "minuti": minuti})
    return corse

def build_messaggio(corse):
    if not corse:
        return "Nessun bus trovato"
    lines = ["Bus P.za Giovanni Paolo II"]
    for c in corse[:6]:
        minuti = c["minuti"]
        if minuti == "*":
            arrivo = "orario non disp."
        elif minuti == "0":
            arrivo = "In arrivo!"
        elif minuti == "1":
            arrivo = "1 minuto"
        else:
            arrivo = minuti + " min"
        lines.append("L." + c["linea"] + " " + c["direzione"] + " - " + arrivo)
    return "\n".join(lines)

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/bus":
            self.handle_bus()
        elif self.path == "/debug":
            self.handle_debug()
        elif self.path == "/":
            self.send_json({"status": "ok"})
        else:
            self.send_response(404)
            self.end_headers()

    def handle_debug(self):
        try:
            html = get_orari()
            body = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:
            self.send_json({"ok": False, "messaggio": str(e)})

    def handle_bus(self):
        try:
            html = get_orari()
            corse = parse_corse(html)
            messaggio = build_messaggio(corse)
            self.send_json({"ok": True, "messaggio": messaggio, "corse": corse})
        except Exception as e:
            self.send_json({"ok": False, "messaggio": "Errore: " + str(e), "corse": []})

    def send_json(self, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass

if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    print("Server avviato sulla porta " + str(PORT))
    server.serve_forever()
