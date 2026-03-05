from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import urllib.request
import urllib.parse
import re
import os

FERMATE = {
    "piazza": {
        "nome_display": "P.za Giovanni Paolo II",
        "risultato": "palina",
        "nome_fermata": "PIAZZA GIOVANNI PAOLO II",
        "qm_palina": "RE320162",
        "x": "18",
        "y": "16",
        "refresh": "0"
    },
    "marsala": {
        "nome_display": "INC. Via Marsala",
        "risultato": "palina",
        "nome_fermata": "INC. VIA MARSALA",
        "qm_palina": "RE310107",
        "refresh": "0"
    }
}

PORT = int(os.environ.get("PORT", 8765))

def get_orari(fermata):
    url = "https://www.setaweb.it/re/quantomanca"
    data = urllib.parse.urlencode(fermata).encode("utf-8")
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
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.DOTALL)
    for row in rows:
        cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
        if len(cells) < 3:
            continue
        linea = re.sub(r'<[^>]+>', '', cells[0]).strip()
        if not linea or not re.match(r'^\d+', linea):
            continue
        direzione = re.sub(r'<[^>]+>', '', cells[1]).strip()
        minuti = re.sub(r'<[^>]+>', '', cells[2]).strip()
        minuti = re.sub(r'[^0-9*]', '', minuti)
        if not minuti:
            minuti = "*"
        corse.append({"linea": linea, "direzione": direzione, "minuti": minuti})
    return corse

def build_messaggio(corse, nome_display, filtro_linea=None):
    if filtro_linea:
        filtro = filtro_linea.strip().lstrip("0") or "0"
        corse = [c for c in corse if c["linea"].lstrip("0") == filtro]

    if not corse:
        if filtro_linea:
            return "Nessun bus trovato per la linea " + filtro_linea
        return "Nessun bus trovato"

    if filtro_linea:
        lines = ["Linea " + filtro_linea + " - " + nome_display]
    else:
        lines = ["Bus " + nome_display]

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
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        linea = params.get("linea", [None])[0]
        fermata_key = params.get("fermata", ["piazza"])[0].lower()

        if parsed.path == "/bus":
            self.handle_bus(fermata_key, linea)
        elif parsed.path == "/fermate":
            self.handle_fermate()
        elif parsed.path == "/":
            self.send_json({"status": "ok"})
        else:
            self.send_response(404)
            self.end_headers()

    def handle_fermate(self):
        lista = [{"chiave": k, "nome": v["nome_display"]} for k, v in FERMATE.items()]
        self.send_json({"fermate": lista})

    def handle_bus(self, fermata_key, filtro_linea=None):
        try:
            if fermata_key not in FERMATE:
                self.send_json({"ok": False, "messaggio": "Fermata non trovata: " + fermata_key, "corse": []})
                return
            fermata = FERMATE[fermata_key]
            nome_display = fermata["nome_display"]
            html = get_orari(fermata)
            corse = parse_corse(html)
            messaggio = build_messaggio(corse, nome_display, filtro_linea)
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
