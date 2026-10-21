# 🛢️ Willy Gas

App de celular para anotar pedidos de gas, fiados y la plata del día.

```
willy_gas/
├── app.py                         ← pantallas (Streamlit)
├── estilos.py                     ← CSS: botones gigantes, alto contraste
├── logica.py                      ← cálculos (precios, resumen del día)
├── db.py                          ← datos: SQLite local o Google Sheets
├── requirements.txt
├── .gitignore                     ← evita subir claves y la base de datos
└── .streamlit/
    ├── config.toml                ← tema claro fijo, sin barra de herramientas
    └── secrets.toml.example       ← plantilla de credenciales
```

## 1. Probar en el computador (5 minutos)

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Sin `secrets.toml`, la app crea sola el archivo `willy_gas.db` (SQLite) y funciona de inmediato.
Para verla en el celular dentro de la misma red Wi-Fi: `streamlit run app.py --server.address 0.0.0.0`
y abra `http://IP-DEL-PC:8501` en el teléfono.

## 2. Dónde guardar los datos para el uso diario

Su papá va a estar en la calle, así que la app tiene que vivir en internet. Hay dos caminos:

| | Opción A (recomendada) | Opción B |
|---|---|---|
| Dónde corre la app | Streamlit Community Cloud (gratis) | Un servidor propio (VPS, Raspberry Pi en la casa con Cloudflare Tunnel) |
| Dónde quedan los datos | Google Sheets | `willy_gas.db` (SQLite) |
| Por qué | El disco de Streamlit Cloud **se borra en cada reinicio**: SQLite ahí perdería todo. Sheets no. Además usted puede ver la planilla desde su propio teléfono. | El disco es permanente y no depende de la API de Google. |

### Opción A paso a paso: Google Sheets + Streamlit Cloud

1. Entre a <https://console.cloud.google.com>, cree un proyecto (ej. `willy-gas`).
2. En **APIs y servicios → Biblioteca**, habilite **Google Sheets API** y **Google Drive API**.
3. En **IAM y administración → Cuentas de servicio**, cree una cuenta. Entre a ella → **Claves → Agregar clave → JSON**. Se descarga un archivo `.json`.
4. Cree una planilla vacía en Google Sheets llamada "Willy Gas". Tóquele **Compartir** e invite como **Editor** al correo `client_email` que aparece en el JSON.
5. Copie el ID de la planilla desde su URL: `docs.google.com/spreadsheets/d/`**`ESTE_ID`**`/edit`.
6. Copie `.streamlit/secrets.toml.example` como `.streamlit/secrets.toml` y rellene `spreadsheet_key` y los campos de `[gcp_service_account]` con los del JSON (la `private_key` va con sus `\n` tal cual).
7. Pruebe en local con `streamlit run app.py`: en **📊 Hoy → ⚙️ Ajustes** debe decir "Datos guardados en: Google Sheets". La app crea sola las hojas `pedidos`, `jornadas` y `config`.
8. Suba la carpeta a un repositorio de GitHub (el `.gitignore` impide subir `secrets.toml`).
9. En <https://share.streamlit.io> → **Create app** → elija el repo y `app.py` → **Advanced settings → Secrets** y pegue el contenido completo de su `secrets.toml`. Despliegue.

**Privacidad:** la app tiene direcciones de clientes. Active el candado poniendo una `clave` en la sección `[acceso]` de los secrets; luego la dirección que guarda en el celular de su papá debe ser `https://su-app.streamlit.app/?k=SU_CLAVE`. Él nunca tiene que escribirla. Como alternativa, Streamlit Cloud permite dejar la app privada e invitar solo ciertos correos.

**Si la app "se durmió":** Streamlit Cloud apaga las apps que pasan muchas horas sin uso. Al abrirla aparece un botón para despertarla; tarda menos de un minuto y los datos están intactos en Sheets. Muéstrele ese botón una vez a su papá.

### Opción B: SQLite en servidor propio

Basta con `streamlit run app.py --server.port 8501` (idealmente como servicio de `systemd`). Use `WILLY_DB=/ruta/segura/willy_gas.db` para elegir dónde se guarda el archivo, y respáldelo a diario, por ejemplo con `cron`:

```bash
0 23 * * * sqlite3 /ruta/willy_gas.db ".backup '/respaldos/willy_$(date +\%F).db'"
```

En ambas opciones existe un respaldo manual: **📊 Hoy → ⚙️ Ajustes → 📥 Descargar respaldo**, que baja un CSV que abre en Excel.

## 3. Dejarla como "app" en el celular de su papá

Android (Chrome): abra la dirección → menú ⋮ → **Agregar a la pantalla principal**. iPhone (Safari): botón Compartir → **Agregar a inicio**. Queda un ícono 🛢️ que abre directo la app.

Streamlit no publica un manifiesto PWA propio, así que esto es un acceso directo y no una PWA instalable completa. Para convertirla después en app de tienda hay dos caminos: envolver la URL con una Trusted Web Activity (Bubblewrap) o Capacitor, o reescribir solo `app.py` en otra tecnología reutilizando la lógica de `logica.py` y el mismo Google Sheet como base de datos.

## 4. Cómo la usa su papá

1. En la mañana toca **☀️ Comenzar nuevo día**.
2. Cuando lo llaman: **➕ Agregar pedido** → toca ➕ en el cilindro → toca la dirección y habla con el 🎤 del teclado → **💾 Guardar pedido**.
3. En cada tarjeta: **🗺️ Ir** abre Google Maps con la ruta; después **✅ Entregado**, **❌ No entregué** o **💰 Fiado** (pregunta cuánto y cuándo cobrar).
4. Si se equivoca, aparece **↩️ Me equivoqué, deshacer**.
5. **💰 Deben** muestra quién debe, ordenado por fecha, con 🔴 los atrasados y el botón **💵 Ya pagó**.
6. **📊 Hoy** muestra cilindros vendidos, plata recibida y total fiado. Ahí también se cambian los precios.

Antes del primer uso, entre a **📊 Hoy → ⚙️ Ajustes** y: (1) ponga los precios reales (los iniciales son referenciales) y (2) escriba la comuna en "Ciudad para el mapa" (ej. `Su comuna, Chile`), para que Google Maps no confunda calles con el mismo nombre en otras ciudades.
