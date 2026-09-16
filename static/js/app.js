/* ============================================================
   Optimizador para los equipos de Balance — cliente
   ============================================================ */

const $ = (sel, ctx = document) => ctx.querySelector(sel);
const $$ = (sel, ctx = document) => [...ctx.querySelectorAll(sel)];

const form = $('#formCalculo');
const btnCalcular = $('#btnCalcular');
const mensajes = $('#mensajes');
const contenido = $('#contenido');
const estadoVacio = $('#estadoVacio');
const tablaGuia = $('#tablaGuia');
const tituloGuia = $('#tituloGuia');

let ultimoResultado = null;
let pestanaActiva = 'calderas';

/* ---------------- Utilidades ---------------- */

const num = (v, dec = 1) =>
  (v === null || v === undefined || Number.isNaN(v))
    ? '—'
    : Number(v).toLocaleString('es-CO', { minimumFractionDigits: dec, maximumFractionDigits: dec });

function toast(texto, tipo = 'ok') {
  const el = document.createElement('div');
  el.className = 'toast' + (tipo === 'error' ? ' toast--error' : '');
  el.textContent = texto;
  $('#toasts').append(el);
  setTimeout(() => el.remove(), 3200);
}

function mostrarMensaje(texto, tipo = 'warn') {
  const el = document.createElement('div');
  el.className = 'alert alert--' + tipo;
  el.innerHTML = `<span>${tipo === 'error' ? '⛔' : '⚠️'}</span><span>${texto}</span>`;
  mensajes.append(el);
}

function limpiarMensajes() { mensajes.innerHTML = ''; }

/* ---------------- Lectura del formulario ---------------- */

function leerEntradas() {
  const n = (name) => parseFloat($(`[name="${name}"]`, form).value);
  const b = (name) => ($(`[name="${name}"]`, form).checked ? 1 : 0);
  return {
    generacion_electrica: n('generacion_electrica'),
    vapor_industrial: n('vapor_industrial'),
    poder_gas_natural: n('poder_gas_natural'),
    poder_gas_combustible: n('poder_gas_combustible'),
    mezcla1: n('mezcla1'),
    mezcla3: n('mezcla3'),
    mezcla4: n('mezcla4'),
    mezcla5: n('mezcla5'),
    caldera1: b('caldera1'),
    caldera3: b('caldera3'),
    caldera4: b('caldera4'),
    caldera5: b('caldera5'),
    turbo1: b('turbo1'),
    turbo2: b('turbo2'),
    turbo3: b('turbo3'),
    turbogas: b('turbogas'),
  };
}

/* ---------------- Estado reactivo de la cabecera ---------------- */

async function refrescarEstado() {
  const e = leerEntradas();
  const q = new URLSearchParams({
    caldera1: e.caldera1, caldera3: e.caldera3, caldera4: e.caldera4, caldera5: e.caldera5,
    turbo1: e.turbo1, turbo2: e.turbo2, turbo3: e.turbo3, turbogas: e.turbogas,
  });
  try {
    const r = await fetch('/api/estado?' + q);
    if (!r.ok) return;
    const s = await r.json();
    $('#tagCalderas').textContent =
      `${s.calderas_habilitadas} habilitada${s.calderas_habilitadas === 1 ? '' : 's'} · máx. ${num(s.produccion_maxima, 0)} Klb/h`;
    $('#tagGeneradores').textContent =
      `${s.generadores_habilitados} habilitado${s.generadores_habilitados === 1 ? '' : 's'} · máx. ${num(s.generacion_maxima, 0)} MWh`;
  } catch { /* la cabecera es informativa: un fallo no bloquea el cálculo */ }
}

/* ---------------- Sliders de mezcla ---------------- */

function sincronizarSliders() {
  $$('.slider').forEach((sl) => {
    const input = $('input[type="range"]', sl);
    $('output', sl).textContent = `${input.value} %`;
  });
  // Atenúa la mezcla de una caldera deshabilitada
  [['mezcla1', 'caldera1'], ['mezcla3', 'caldera3'],
   ['mezcla4', 'caldera4'], ['mezcla5', 'caldera5']].forEach(([mez, cal]) => {
    const slider = $(`[name="${mez}"]`, form).closest('.slider');
    slider.classList.toggle('is-off', !$(`[name="${cal}"]`, form).checked);
  });
}

/* ---------------- Pintado de resultados ---------------- */

function tarjeta({ label, valor, unidad, clase = '', dec = 1 }) {
  return `<div class="card ${clase}">
    <span class="card__label">${label}</span>
    <span class="card__value">${num(valor, dec)}</span>
    <span class="card__unit">${unidad}</span>
  </div>`;
}

function pintarResultado(r) {
  ultimoResultado = r;

  const g = r.generadores;
  $('#cardsGeneradores').innerHTML = [
    tarjeta({ label: 'Generación total', valor: g.total, unidad: 'MWh', clase: 'card--total' }),
    tarjeta({ label: 'Turbo 1', valor: g.turbo1, unidad: 'MWh', clase: g.turbo1 > 0 ? '' : 'card--off' }),
    tarjeta({ label: 'Turbo 2', valor: g.turbo2, unidad: 'MWh', clase: g.turbo2 > 0 ? '' : 'card--off' }),
    tarjeta({ label: 'Turbo 3', valor: g.turbo3, unidad: 'MWh', clase: g.turbo3 > 0 ? '' : 'card--off' }),
    tarjeta({ label: 'Turbogás', valor: g.turbogas, unidad: 'MWh', clase: g.turbogas > 0 ? '' : 'card--off' }),
    tarjeta({ label: 'Disp. para generar', valor: g.disponibilidad, unidad: 'MWh', clase: 'card--disp' }),
  ].join('');

  const c = r.calderas;
  $('#cardsCalderas').innerHTML = [
    tarjeta({ label: 'Carga calderas', valor: c.carga, unidad: 'Klb/h', clase: 'card--total' }),
    tarjeta({ label: 'Caldera 1', valor: c.caldera1, unidad: 'Klb/h', clase: c.caldera1 > 0 ? '' : 'card--off' }),
    tarjeta({ label: 'Caldera 3', valor: c.caldera3, unidad: 'Klb/h', clase: c.caldera3 > 0 ? '' : 'card--off' }),
    tarjeta({ label: 'Caldera 4', valor: c.caldera4, unidad: 'Klb/h', clase: c.caldera4 > 0 ? '' : 'card--off' }),
    tarjeta({ label: 'Caldera 5', valor: c.caldera5, unidad: 'Klb/h', clase: c.caldera5 > 0 ? '' : 'card--off' }),
    tarjeta({ label: 'Disponibilidad', valor: c.disponibilidad, unidad: 'Klb/h', clase: 'card--disp' }),
  ].join('');

  pintarTabla();

  estadoVacio.hidden = true;
  contenido.hidden = false;
  $('#resultados').classList.remove('is-empty');
}

function pintarTabla() {
  if (!ultimoResultado) return;
  const filas = pestanaActiva === 'calderas'
    ? ultimoResultado.tabla_calderas
    : ultimoResultado.tabla_generadores;

  tituloGuia.textContent = pestanaActiva === 'calderas'
    ? 'Guía de operación para las calderas en servicio'
    : 'Guía de operación para los generadores en servicio';

  const thead = $('thead', tablaGuia);
  const tbody = $('tbody', tablaGuia);

  if (!filas || filas.length === 0) {
    thead.innerHTML = '';
    tbody.innerHTML = '<tr><td>Sin equipos en servicio.</td></tr>';
    return;
  }

  const columnas = Object.keys(filas[0]);
  thead.innerHTML = '<tr>' + columnas.map((col) => `<th>${col}</th>`).join('') + '</tr>';
  tbody.innerHTML = filas
    .map((f) => '<tr>' + columnas.map((col) => `<td>${f[col]}</td>`).join('') + '</tr>')
    .join('');
}

/* ---------------- Cálculo ---------------- */

async function calcular(evento) {
  evento.preventDefault();
  limpiarMensajes();

  if (!form.reportValidity()) return;

  btnCalcular.disabled = true;
  btnCalcular.classList.add('is-loading');
  $('.btn__text', btnCalcular).textContent = 'Calculando…';

  try {
    const resp = await fetch('/api/calcular', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(leerEntradas()),
    });
    const datos = await resp.json();

    if (!resp.ok) {
      const detalle = typeof datos.detail === 'string'
        ? datos.detail
        : 'Los valores deben ser numéricos y estar dentro del rango normal de operación.';
      mostrarMensaje(detalle, 'error');
      return;
    }

    if (datos.alerta) mostrarMensaje(datos.alerta, 'warn');
    pintarResultado(datos);
  } catch (err) {
    mostrarMensaje('No se pudo contactar con el servidor. ' + err.message, 'error');
  } finally {
    btnCalcular.disabled = false;
    btnCalcular.classList.remove('is-loading');
    $('.btn__text', btnCalcular).textContent = 'Calcular';
  }
}

/* ---------------- Límites operativos ---------------- */

const modal = $('#modalLimites');
const formLimites = $('#formLimites');
const errorLimites = $('#errorLimites');

async function abrirLimites() {
  errorLimites.hidden = true;
  try {
    const r = await fetch('/api/limites');
    const l = await r.json();
    Object.entries(l).forEach(([k, v]) => {
      const input = $(`[name="${k}"]`, formLimites);
      if (input) input.value = v;
    });
    modal.showModal();
  } catch {
    toast('No se pudieron cargar los límites.', 'error');
  }
}

async function guardarLimites() {
  if (!formLimites.reportValidity()) return;
  errorLimites.hidden = true;

  const cuerpo = {};
  $$('input', formLimites).forEach((i) => { cuerpo[i.name] = parseFloat(i.value); });

  try {
    const r = await fetch('/api/limites', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(cuerpo),
    });
    const datos = await r.json();
    if (!r.ok) {
      errorLimites.textContent = typeof datos.detail === 'string'
        ? datos.detail
        : 'Los valores deben ser numéricos y estar dentro del rango normal de operación.';
      errorLimites.hidden = false;
      return;
    }
    modal.close();
    toast('Datos guardados correctamente.');
    refrescarEstado();
  } catch (err) {
    errorLimites.textContent = 'No se pudo guardar: ' + err.message;
    errorLimites.hidden = false;
  }
}

/* ---------------- Enlaces de eventos ---------------- */

form.addEventListener('submit', calcular);

form.addEventListener('input', (e) => {
  if (e.target.type === 'range') sincronizarSliders();
  if (e.target.type === 'checkbox') { sincronizarSliders(); refrescarEstado(); }
});

$$('.tab').forEach((tab) => {
  tab.addEventListener('click', () => {
    $$('.tab').forEach((t) => {
      const activo = t === tab;
      t.classList.toggle('is-active', activo);
      t.setAttribute('aria-selected', String(activo));
    });
    pestanaActiva = tab.dataset.tab;
    pintarTabla();
  });
});

$('#btnLimites').addEventListener('click', abrirLimites);
$('#btnGuardarLimites').addEventListener('click', guardarLimites);
$('#btnCancelarLimites').addEventListener('click', () => modal.close());

/* ---------------- Arranque ---------------- */

(function inicio() {
  sincronizarSliders();
  refrescarEstado();
})();
