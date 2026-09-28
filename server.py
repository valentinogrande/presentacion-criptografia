#!/usr/bin/env python3
"""Banco Bob: el mismo login servido por HTTP (8000) y por HTTPS (8443).

Uso:  python3 server.py
Luego abrir http://127.0.0.1:8000 y https://127.0.0.1:8443
"""
import html
import pathlib
import ssl
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

HTTP_PORT = 8000
HTTPS_PORT = 8443
USUARIO, CLAVE = "alice", "clave123"

AQUI = pathlib.Path(__file__).parent
CERT, KEY = AQUI / "cert.pem", AQUI / "key.pem"

PAGINA = """<!doctype html>
<html><head><meta charset="utf-8"><title>Banco Bob</title></head>
<body>
<h1>Banco Bob</h1>
<p><i>Home banking ({esquema})</i></p>
<hr>
{contenido}
</body></html>"""

FORM = """<form method="post" action="/login">
<table>
<tr><td>Usuario:</td><td><input type="text" name="usuario" value="alice"></td></tr>
<tr><td>Contrase&ntilde;a:</td><td><input type="password" name="password"></td></tr>
</table>
<input type="submit" value="Ingresar">
</form>
<p><small>Usuario de prueba: alice / clave123</small></p>"""


class Handler(BaseHTTPRequestHandler):
    def responder(self, contenido, codigo=200):
        esquema = "HTTPS" if isinstance(self.connection, ssl.SSLSocket) else "HTTP"
        cuerpo = PAGINA.format(esquema=esquema, contenido=contenido).encode()
        self.send_response(codigo)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def do_GET(self):
        self.responder(FORM)

    def do_POST(self):
        largo = int(self.headers.get("Content-Length", 0))
        datos = parse_qs(self.rfile.read(largo).decode())
        usuario = datos.get("usuario", [""])[0]
        clave = datos.get("password", [""])[0]
        if usuario == USUARIO and clave == CLAVE:
            self.responder(f"<p><b>Bienvenida, {html.escape(usuario)}.</b></p>"
                           "<p>Saldo: $1.250.000</p><p><a href='/'>Salir</a></p>")
        else:
            self.responder("<p style='color:red'>Usuario o contrase&ntilde;a incorrectos.</p>"
                           + FORM, 401)


def generar_certificado():
    if CERT.exists() and KEY.exists():
        return
    print("Generando certificado autofirmado...")
    subprocess.run(
        ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
         "-keyout", str(KEY), "-out", str(CERT), "-days", "365",
         "-subj", "/CN=localhost",
         "-addext", "subjectAltName=DNS:localhost,IP:127.0.0.1"],
        check=True, capture_output=True)


def main():
    generar_certificado()

    http_srv = ThreadingHTTPServer(("127.0.0.1", HTTP_PORT), Handler)

    https_srv = ThreadingHTTPServer(("127.0.0.1", HTTPS_PORT), Handler)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(CERT, KEY)
    https_srv.socket = ctx.wrap_socket(https_srv.socket, server_side=True)

    threading.Thread(target=http_srv.serve_forever, daemon=True).start()
    print(f"HTTP : http://127.0.0.1:{HTTP_PORT}")
    print(f"HTTPS: https://127.0.0.1:{HTTPS_PORT}")
    print("Ctrl+C para cortar.")
    try:
        https_srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
