# Optimizador para los equipos de Balance — Web App

Versión web (FastAPI) de la *Herramienta IA para Calderas, Turbogeneradores y Turbogás*.
La interfaz Tkinter se sustituyó por una aplicación web; **los modelos de cálculo no se
modificaron**. El script de escritorio original y su notebook ya no forman parte del
proyecto: toda su lógica vive ahora en `app/`.

## Puesta en marcha

```bash
pip install -r requirements.txt
```

```bash
python run.py
```

Luego abre <http://127.0.0.1:8000>. La documentación interactiva de la API está en
<http://127.0.0.1:8000/docs>.

El arranque tarda un par de segundos: se cargan los cuatro `.parquet` de `data/`
y se ajustan las regresiones iniciales, exactamente igual que hacía el script original al
abrirse.

## Estructura

```
app/
  core.py       Lógica de cálculo, copiada literalmente del script original (sin Tkinter):
                regresiones, Oxi1..Oxi5, calcular_Prod (SLSQP) y optimizar_generacion (PuLP/CBC).
  service.py    Orquestación de un cálculo completo: equivale a on_button_toggle() + fCalcular().
  limites.py    Lectura/escritura de "data/datos.txt" (cargar_Datos / guardar_Datos).
  models.py     Esquemas Pydantic de entrada y salida.
  main.py       Rutas FastAPI y servicio de los archivos estáticos.
static/
  index.html    Interfaz.
  css/styles.css
  js/app.js
  img/          Logos de Ecopetrol, Minciencias y Balance.
data/           Datos (.parquet) y límites operativos.
tools/
  csv_a_parquet.py  Regenera los .parquet desde .csv, si llegan datos nuevos.
run.py          Arranque de uvicorn (HOST y PORT por variable de entorno).
Dockerfile      Imagen del servicio (etapas: dev / produccion).
.devcontainer/  Entorno de desarrollo remoto para VS Code.
.vscode/launch.json
.gitattributes  Finales de linea LF y marcado binario de .parquet/.png/.ico.
```

## Desarrollo remoto en VS Code

Con la extensión **Dev Containers** instalada: abre la carpeta del proyecto y acepta
*Reopen in Container* (o `F1` → *Dev Containers: Reopen in Container*).

El contenedor usa la etapa `dev` del mismo `Dockerfile`, así que reaprovecha las capas
ya construidas y no descarga otra imagen base. El proyecto se **monta** en `/app`: lo que
editas en el host se ve al instante dentro del contenedor, sin reconstruir.

Una vez dentro, `F5` arranca el servidor con recarga automática (ver `.vscode/launch.json`),
o a mano:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

VS Code reenvía el puerto 8000 al host. Cada recarga tarda un par de segundos porque se
releen los datos.

## Docker

```bash
docker build -t herramienta-balance:1.0 .
```

Arranque, montando `datos.txt` desde el host para que los límites operativos que
guardes en la web sobrevivan a recrear el contenedor (PowerShell):

```bash
docker run -d -p 8000:8000 --restart unless-stopped -v "${PWD}/data/datos.txt:/app/data/datos.txt" --name herramienta-balance herramienta-balance:1.0
```

En CMD, `${PWD}` se sustituye por `%cd%`. Si no te importa perder esos límites al
recrear el contenedor, puedes omitir el `-v`.

La app queda en <http://localhost:8000>.

Notas:

- **Tamaño.** La imagen incluye los datos de `data/` (~130 MB en parquet), así
  que ronda los 650 MB. Para una imagen más ligera, descomenta `data/` en
  `.dockerignore` y monta la carpeta: `-v "${PWD}/data:/app/data"`.
- **Solver.** Se usa el CBC que empaqueta PuLP, el mismo binario que en desarrollo.
  Con `CBC_PATH` puedes apuntar a otro CBC del sistema. Si construyes en arm64 y PuLP
  no trae binario, descomenta en el `Dockerfile` las dos líneas que instalan
  `coinor-cbc`.
- **Arranque.** El contenedor tarda unos segundos en responder: carga los parquet y
  ajusta las regresiones (~1,3 s medidos). El `HEALTHCHECK` da 90 s de margen de sobra.
- **Etapas.** `docker build` sin `--target` construye `produccion`, que es la última.
  La etapa `dev` sólo trae Python y las dependencias: existe para el devcontainer.

## Despliegue en Google Cloud Run

`docker build` sin `--target` construye la etapa `produccion`, que es la ultima del
`Dockerfile`: es la que se despliega. El contenedor lee `PORT` del entorno, que es
justo como Cloud Run le indica en que puerto escuchar.

```bash
gcloud run deploy optimizador-balance --source . --region us-central1 --memory 1Gi --allow-unauthenticated
```

Lo que conviene saber antes de publicar:

- **Memoria.** La app ocupa ~660 MB al arrancar: los cuatro `.parquet` quedan
  residentes porque `service.py` los consulta en cada calculo, no solo al ajustar las
  regresiones. Con menos de 1 Gi el contenedor muere por OOM.
- **Visibilidad.** La app no tiene autenticacion, y `PUT /api/limites` deja cambiar los
  limites operativos a cualquier visitante. Los datos son de operacion de planta: quita
  `--allow-unauthenticated` salvo que anadas autenticacion primero.
- **`datos.txt` no persiste.** El sistema de archivos de Cloud Run vive en memoria y el
  servicio escala a cero: al reiniciar, los limites vuelven a los del repositorio.
  Conservarlos exige almacenamiento externo (GCS o una base de datos).
- **Concurrencia.** El `threading.Lock` serializa los calculos. Varios usuarios
  simultaneos se encolan; con dos o tres va bien.
- **Arranque en frio.** Al escalar a cero, la primera peticion tras un rato de inactividad
  paga el arranque del contenedor mas los ~1,3 s de carga de datos.

## API

| Método | Ruta            | Descripción                                                     |
| ------ | --------------- | --------------------------------------------------------------- |
| `GET`  | `/api/estado`   | Calderas/generadores habilitados y sus máximos (cabecera reactiva). |
| `POST` | `/api/calcular` | Optimización completa: reparto de generación y de vapor + guías.  |
| `GET`  | `/api/limites`  | Límites operativos guardados en `datos.txt`.                      |
| `PUT`  | `/api/limites`  | Guarda los límites operativos.                                    |

Ejemplo de cálculo:

```bash
curl -X POST http://127.0.0.1:8000/api/calcular -H "Content-Type: application/json" -d "{\"generacion_electrica\":50,\"vapor_industrial\":450}"
```

## Qué cambió respecto al script original

La lógica de cálculo se trasladó tal cual. Los únicos ajustes fueron los imprescindibles
para que funcione como servidor:

- **Rutas absolutas.** Los datos y `datos.txt` se resuelven desde la raíz del proyecto
  (`core.BASE_DIR`) en vez de depender del directorio de trabajo.
- **Los cuatro `read_csv` pasaron a `read_parquet`.** Mismo contenido: verifiqué que las
  regresiones y el pipeline completo dan resultados idénticos campo por campo.
- **`maxProdV`, `calDisp` e `indices`** se publican en `core` antes de cada cálculo, igual
  que hacía `on_button_toggle()` con las variables globales de Tkinter.
- **Un `threading.Lock`** serializa los cálculos, porque el núcleo conserva el diseño
  original basado en variables globales (`req`, `ef`, `bV`…) y dos peticiones simultáneas
  se pisarían.
- **`min_gen` se inicializa a 0** en `optimizar_generacion`; en el original quedaba sin
  definir si ningún generador estaba disponible.
- **`.copy()` sobre los subconjuntos `d1V`…`d5V`** antes de añadirles `Dif_IGV_V`, para
  evitar el aviso de pandas al escribir sobre una vista.
- **El solver pasó a ser el CBC que empaqueta PuLP** (`core._crear_solver`), en lugar
  del `cbc.exe` que traía el proyecto, que no corre en Linux. Es el mismo solver, otro
  ejecutable: comprobé que ambos dan resultados idénticos campo por campo en ocho
  escenarios. `cbc.exe` se eliminó del repositorio.
- **El solver CBC se invoca con `msg=False`** para no volcar su salida en el log del servidor.
- Los `messagebox` pasan a ser respuestas HTTP 400 con el mismo mensaje, y la alerta de
  demanda (`res_sal['Alerta']`) se devuelve en el campo `alerta`.

## Notas de operación

- El cálculo tarda unos segundos (dos MILP + una optimización SLSQP sobre ~600 000 filas
  por caldera). Se ejecuta en un hilo aparte para no bloquear el servidor.
- Los datos viven en `.parquet`. Los `.csv` originales se eliminaron: los parquet son
  copia exacta de lo que `read_csv(..., skiprows=[0], names=Nombres)` devolvía, columna
  `Fecha` incluida, y el `dropna()` sigue aplicándose al cargar.
- Un único proceso atiende los cálculos en serie. Para varios usuarios concurrentes hay que
  replantear las variables globales de `core.py` antes de añadir workers.
- La fecha/hora en pantalla y el selector de tema se eliminaron; la interfaz usa un único
  tema claro.
