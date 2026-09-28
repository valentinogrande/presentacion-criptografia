# Laboratorio HTTP vs HTTPS

"Banco Bob" es un home banking de juguete que sirve el mismo login por HTTP
y por HTTPS. La idea es capturar el tráfico con Wireshark/tshark y comprobar
que por HTTP la contraseña viaja en texto plano, mientras que por HTTPS solo
se ven bytes cifrados.

## Requisitos

- Python 3
- OpenSSL (para generar el certificado autofirmado)
- Wireshark / tshark, con permisos de captura (ver abajo)

### Permisos de captura (sin `sudo`)

Wireshark y tshark no capturan directamente: delegan en `dumpcap`, que es el
único binario que necesita privilegios. En vez de correr todo como root, se le
dan *capabilities* a `dumpcap` y se limita su ejecución al grupo `wireshark`.

1. Agregar tu usuario al grupo `wireshark` (en Arch lo crea el paquete
   `wireshark-cli`; en Debian/Ubuntu, `sudo dpkg-reconfigure wireshark-common`
   y responder *Sí*):

   ```bash
   sudo usermod -aG wireshark $USER
   ```

2. Verificar que `dumpcap` pertenezca al grupo y tenga las capabilities
   (normalmente el paquete ya lo deja así):

   ```bash
   ls -l /usr/bin/dumpcap
   # -rwxr-x--- 1 root wireshark ... /usr/bin/dumpcap
   getcap /usr/bin/dumpcap
   # /usr/bin/dumpcap cap_net_admin,cap_net_raw=eip
   ```

   Si faltan, aplicarlas a mano:

   ```bash
   sudo chgrp wireshark /usr/bin/dumpcap
   sudo chmod 750 /usr/bin/dumpcap
   sudo setcap cap_net_raw,cap_net_admin+eip /usr/bin/dumpcap
   ```

   - `cap_net_raw`: abrir sockets crudos para leer paquetes.
   - `cap_net_admin`: poner la interfaz en modo promiscuo y configurarla.

3. **Cerrar sesión y volver a entrar** (o reiniciar) para que el grupo nuevo
   tenga efecto. Para probar sin cerrar sesión: `newgrp wireshark`.

4. Comprobar:

   ```bash
   id | grep wireshark      # el grupo tiene que aparecer
   tshark -D                # tiene que listar la interfaz "lo"
   ```

## Presentación

`presentacion/index.html` es la presentación interactiva (~15 min). Se abre con
doble clic en cualquier navegador y funciona sin internet.

- `→` / `Espacio` / `PageDown` avanza; `←` / `PageUp` retrocede.
- Los botones de cada diapositiva disparan la animación; en la del candado se
  arrastra el candado y la llave (un clic también funciona).
- Las diapositivas del lab tienen un botón **captura de respaldo** que muestra
  los volcados reales de `capturas/` por si la demo en vivo falla.

## Levantar el servidor

```bash
python3 server.py
```

| Protocolo | URL                       |
|-----------|---------------------------|
| HTTP      | http://127.0.0.1:8000     |
| HTTPS     | https://127.0.0.1:8443    |

Usuario de prueba: `alice` / `clave123`

La primera vez se generan `cert.pem` y `key.pem`. Como el certificado es
autofirmado, el navegador va a mostrar una advertencia en HTTPS: aceptala para
continuar.

> Usá `127.0.0.1` y no `localhost`: el servidor escucha solo en IPv4 y
> `localhost` puede resolver primero a `::1`.

## Capturar el tráfico

El servidor escucha en `127.0.0.1`, así que todo el tráfico pasa por la
interfaz de **loopback (`lo`)**. Si capturás en `wlan0` o `eth0` no vas a ver
nada.

Los comandos capturan en vivo: dejalos corriendo, hacé el login en el
navegador y cortalos con `Ctrl+C`.

### 1. HTTP: la contraseña en texto plano

```bash
tshark -i lo -f "tcp port 8000" -Y 'http.request.method == "POST"' -x
```

En la columna ASCII del volcado se lee el cuerpo del formulario:

```
usuario=alice&password=clave123
```

Versión resumida, solo con los campos del formulario:

```bash
tshark -i lo -f "tcp port 8000" -Y 'http.request.method == "POST"' \
  -T fields -e ip.src -e http.request.uri -e urlencoded-form.key -e urlencoded-form.value
```

```
127.0.0.1	/login	usuario,password	alice,clave123
```

### 2. HTTPS: solo basura cifrada

```bash
tshark -i lo -f "tcp port 8443" -Y 'tls.app_data && tcp.dstport == 8443' -x
```

Muestra los registros TLS *Application Data* que manda el navegador al
servidor (ahí va el POST del login):

```
0040  cc d7 17 03 03 00 c9 db ed be bd f5 cb 17 f9 b6   ................
0050  a0 a8 00 4f e9 c5 37 02 e5 96 f8 23 38 45 bb 31   ...O..7....#8E.1
0060  92 7a e7 c6 ec 84 d7 d3 2f 26 10 83 59 cf 50 7c   .z....../&..Y.P|
```

`17 03 03` es la cabecera de un registro TLS de datos de aplicación; todo lo
que sigue está cifrado. No aparecen ni `alice` ni `clave123`.

Para ver el flujo completo (handshake incluido):

```bash
tshark -i lo -f "tcp port 8443" -Y tls
```

## Con Wireshark (interfaz gráfica)

1. Elegir la interfaz **Loopback: lo**.
2. Filtro de visualización: `tcp.port == 8000 || tcp.port == 8443`
3. Hacer login por HTTP y por HTTPS.
4. En el paquete `POST /login` (puerto 8000): clic derecho → *Follow → TCP
   Stream* muestra la contraseña.
5. Hacer lo mismo en un paquete *Application Data* del puerto 8443: solo se
   ve contenido ilegible.

## Capturas de respaldo

Si en vivo no funciona, la carpeta `capturas/` tiene el mismo experimento ya
grabado (login de `alice` por HTTP y por HTTPS):

| Archivo                  | Contenido                                        |
|--------------------------|--------------------------------------------------|
| `http.pcapng`            | Captura completa del login por HTTP              |
| `https.pcapng`           | Captura completa del login por HTTPS             |
| `http-post.txt`          | Volcado hex/ASCII del POST: se ve la contraseña  |
| `http-credenciales.txt`  | Solo los campos del formulario                   |
| `https-cifrado.txt`      | Volcado de los datos TLS cifrados                |
| `https-flujo.txt`        | Resumen del flujo TLS (handshake + datos)        |

Los `.pcapng` se abren con Wireshark o con tshark usando `-r` en vez de `-i lo`:

```bash
tshark -r capturas/http.pcapng -Y 'http.request.method == "POST"' -x
tshark -r capturas/https.pcapng -Y 'tls.app_data && tcp.dstport == 8443' -x
```

## Problemas comunes

| Síntoma | Causa / solución |
|---------|------------------|
| No se captura nada | Estás en la interfaz equivocada: usá `lo`. |
| El filtro `http` no muestra nada del 8443 | Es lo esperado: está cifrado. Usá `tls` o filtrá por puerto. |
| `tls.record.content_type == 23` no matchea | En TLS 1.3 usá `tls.app_data`. |
| Error de permisos al capturar | Ver *Permisos de captura*: grupo `wireshark` + capabilities en `dumpcap`, y volver a iniciar sesión. |

## Conclusión

Con HTTP cualquiera que pueda ver el tráfico (misma red Wi-Fi, un router
comprometido, el ISP) lee las credenciales directamente. Con HTTPS el mismo
formulario viaja cifrado con TLS: el atacante ve que hay una conexión y cuántos
bytes se mandan, pero no el contenido.

## Archivos

| Archivo    | Descripción                                  |
|------------|----------------------------------------------|
| `server.py`| Servidor HTTP (8000) y HTTPS (8443)          |
| `cert.pem` | Certificado autofirmado (se genera solo)     |
| `key.pem`  | Clave privada del certificado (solo para el laboratorio) |
