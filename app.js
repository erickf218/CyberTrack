/**
 * CyberTrack v0.2 "Inventory Core"
 * ------------------------------------------------------------------
 * A partir de esta versión el inventario ya NO vive en el HTML.
 * Se pide al backend (FastAPI + SQLite) y se dibuja aquí en JS.
 *
 * Requiere que el backend esté corriendo:
 *   cd backend && uvicorn app.main:app --reload
 * ------------------------------------------------------------------
 */

// Antes esto era 'http://127.0.0.1:8000' — con el frontend ahora
// servido por el mismo backend (ver app/main.py), una ruta relativa
// vacía funciona tanto en desarrollo local como ya desplegado, sin
// tener que cambiar nada entre los dos casos.
const API_BASE = window.location.hostname === 'localhost' 
    ? 'http://127.0.0.1:8000' 
    : 'https://cybertrack-api.onrender.com';

let inventoryCache = []; // última respuesta del backend, usada para filtrar sin volver a pedirla

document.addEventListener('DOMContentLoaded', () => {
  setupTabs();
  setupSearch();
  setupAddPartModal();
  setupPhotoDetection();
  setupAssistant();
  loadInventory();
});

/**
 * Pestañas del rail. Solo "Inventario" tiene contenido real por ahora;
 * el resto está marcado como "pronto" en el HTML para no fingir
 * funciones que todavía no existen.
 */
function setupTabs() {
  const items = document.querySelectorAll('.rail__item');

  items.forEach((item) => {
    item.addEventListener('click', () => {
      items.forEach((i) => i.classList.remove('is-active'));
      item.classList.add('is-active');

      const targetId = item.dataset.scrollTo;
      if (targetId) {
        document.getElementById(targetId)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });
}

/**
 * Pide el inventario al backend y lo dibuja. Si el backend no está
 * corriendo, muestra un mensaje claro en vez de dejar la pantalla vacía
 * sin explicación.
 */
async function loadInventory() {
  const status = document.getElementById('inventoryStatus');
  status.textContent = 'Cargando inventario…';
  status.classList.remove('is-error', 'is-hidden');

  try {
    const response = await fetch(`${API_BASE}/api/inventory`);
    if (!response.ok) throw new Error(`El servidor respondió ${response.status}`);

    inventoryCache = await response.json();
    renderInventory(inventoryCache);
    renderStats(inventoryCache);

    status.classList.add('is-hidden');
  } catch (error) {
    status.textContent =
      'No se pudo conectar con el backend. Revisa que esté corriendo en ' +
      `${API_BASE} (uvicorn app.main:app --reload).`;
    status.classList.add('is-error');
    console.error('[CyberTrack] Error al cargar el inventario:', error);
  }
}

/**
 * Agrupa las piezas por categoría y reconstruye las tablas del
 * inventario dentro de #inventoryContainer.
 */
function renderInventory(parts) {
  const container = document.getElementById('inventoryContainer');
  container.innerHTML = '';

  if (parts.length === 0) {
    container.innerHTML = '<p class="inventory-status">Todavía no hay piezas registradas.</p>';
    return;
  }

  const byCategory = groupBy(parts, (part) => part.category);

  Object.entries(byCategory).forEach(([category, items]) => {
    const section = document.createElement('div');
    section.className = 'category';
    section.dataset.category = category;

    const heading = document.createElement('h3');
    heading.textContent = category;
    section.appendChild(heading);

    const table = document.createElement('table');
    table.className = 'parts-table';
    const tbody = document.createElement('tbody');

    items.forEach((part) => {
      const row = document.createElement('tr');
      if (part.is_low_stock) row.classList.add('is-low');

      row.innerHTML = `
        <td class="part-name">
          ${escapeHtml(part.name)}
          ${part.is_low_stock ? '<span class="low-flag">stock bajo</span>' : ''}
        </td>
        <td class="part-code">${escapeHtml(part.code)}</td>
        <td class="part-count">
          <button type="button" class="qty-edit" data-edit-qty="${part.id}" title="Editar cantidad">${part.quantity}</button>
        </td>
        <td class="part-actions">
          <button type="button" class="btn-icon" title="Eliminar ${escapeHtml(part.name)}" data-delete-id="${part.id}">
            <svg viewBox="0 0 24 24" fill="none" width="14" height="14"><path d="M4 7h16M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2m-8 0 1 12a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1l1-12" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </button>
        </td>
      `;
      row.querySelector('[data-delete-id]').addEventListener('click', () => deletePart(part.id, part.name));
      row.querySelector('[data-edit-qty]').addEventListener('click', (event) => startQuantityEdit(event.target, part));
      tbody.appendChild(row);
    });

    table.appendChild(tbody);
    section.appendChild(table);
    container.appendChild(section);
  });
}

/**
 * Actualiza las tarjetas de resumen arriba del inventario.
 * "Pieza más usada" no se calcula aquí porque necesita historial
 * de uso, que todavía no existe (llega en v0.5).
 */
function renderStats(parts) {
  const totalParts = parts.length;
  const categories = new Set(parts.map((p) => p.category)).size;
  const lowStock = parts.filter((p) => p.is_low_stock).length;

  document.getElementById('statTotalParts').textContent = totalParts;
  document.getElementById('statCategories').textContent = categories;
  document.getElementById('statLowStock').textContent = lowStock;
}

/**
 * Filtro sobre el inventario ya cargado (no vuelve a pedirlo al
 * backend, filtra lo que ya tenemos en inventoryCache).
 */
function setupSearch() {
  const input = document.querySelector('.search input');
  if (!input) return;

  input.addEventListener('input', (event) => {
    const query = event.target.value.trim().toLowerCase();

    const filtered = query
      ? inventoryCache.filter(
          (part) =>
            part.name.toLowerCase().includes(query) ||
            part.code.toLowerCase().includes(query)
        )
      : inventoryCache;

    renderInventory(filtered);
  });
}

/**
 * Modal de "Agregar pieza": abrir/cerrar y manejar el submit.
 */
function setupAddPartModal() {
  const backdrop = document.getElementById('addPartBackdrop');
  const form = document.getElementById('addPartForm');
  const errorBox = document.getElementById('addPartError');

  const open = (prefill = {}) => {
    errorBox.hidden = true;
    form.reset();
    refreshCategoryOptions();
    if (prefill.name) form.querySelector('input[name="name"]').value = prefill.name;
    if (prefill.category) form.querySelector('input[name="category"]').value = prefill.category;
    if (prefill.code) form.querySelector('input[name="code"]').value = prefill.code;
    if (prefill.quantity) form.querySelector('input[name="quantity"]').value = prefill.quantity;
    backdrop.hidden = false;
    form.querySelector('input[name="name"]').focus();
  };
  const close = () => { backdrop.hidden = true; };

  // Se expone para que renderDetectionList() pueda abrir el modal
  // precargado con el nombre detectado por YOLO.
  window.openAddPartModal = open;

  document.getElementById('openAddPart').addEventListener('click', () => open());
  document.getElementById('closeAddPart').addEventListener('click', close);
  document.getElementById('cancelAddPart').addEventListener('click', close);

  // Cerrar al hacer click fuera del cuadro del modal, o con Escape.
  backdrop.addEventListener('click', (event) => {
    if (event.target === backdrop) close();
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && !backdrop.hidden) close();
  });

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    errorBox.hidden = true;

    const formData = new FormData(form);
    const payload = {
      name: formData.get('name').trim(),
      code: formData.get('code').trim(),
      category: formData.get('category').trim(),
      quantity: Number(formData.get('quantity')),
      low_stock_threshold: Number(formData.get('low_stock_threshold')),
    };

    try {
      const response = await fetch(`${API_BASE}/api/inventory`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(extractErrorMessage(body, response.status));
      }

      close();
      await loadInventory();
    } catch (error) {
      errorBox.textContent = error.message;
      errorBox.hidden = false;
    }
  });
}

/**
 * Llena el <datalist> de categorías con las que ya existen en el
 * inventario cargado, para que sea fácil reusar "Motores", "Sensores", etc.
 */
function refreshCategoryOptions() {
  const datalist = document.getElementById('categoryOptions');
  const categories = [...new Set(inventoryCache.map((p) => p.category))];
  datalist.innerHTML = categories.map((c) => `<option value="${escapeHtml(c)}">`).join('');
}

/**
 * Elimina una pieza tras confirmar, y recarga el inventario.
 */
async function deletePart(partId, partName) {
  const confirmed = window.confirm(`¿Eliminar "${partName}" del inventario?`);
  if (!confirmed) return;

  try {
    const response = await fetch(`${API_BASE}/api/inventory/${partId}`, { method: 'DELETE' });
    if (!response.ok && response.status !== 204) {
      throw new Error(`El servidor respondió ${response.status}`);
    }
    await loadInventory();
  } catch (error) {
    console.error('[CyberTrack] Error al eliminar la pieza:', error);
    window.alert('No se pudo eliminar la pieza. Revisa que el backend esté corriendo.');
  }
}

/**
 * Convierte el botón de cantidad en un <input> editable al hacer clic.
 * Enter o perder el foco confirma; Escape cancela. Útil sobre todo
 * para corregir el "1" que deja el auto-agregado desde detección,
 * sin tener que borrar la pieza y crearla de nuevo.
 */
function startQuantityEdit(button, part) {
  const cell = button.parentElement;
  const input = document.createElement('input');
  input.type = 'number';
  input.min = '0';
  input.value = part.quantity;
  input.className = 'qty-input';

  cell.innerHTML = '';
  cell.appendChild(input);
  input.focus();
  input.select();

  let settled = false;

  const confirm = async () => {
    if (settled) return;
    settled = true;
    const newQuantity = Number(input.value);

    if (!Number.isFinite(newQuantity) || newQuantity < 0 || newQuantity === part.quantity) {
      await loadInventory();
      return;
    }

    try {
      const response = await fetch(`${API_BASE}/api/inventory/${part.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ quantity: newQuantity }),
      });
      if (!response.ok) throw new Error(`El servidor respondió ${response.status}`);
    } catch (error) {
      console.error('[CyberTrack] Error al actualizar cantidad:', error);
      window.alert('No se pudo actualizar la cantidad.');
    }
    await loadInventory();
  };

  const cancel = async () => {
    if (settled) return;
    settled = true;
    await loadInventory();
  };

  input.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') input.blur();
    if (event.key === 'Escape') cancel();
  });
  input.addEventListener('blur', confirm);
}

/**
 * Flujo de detección por foto.
 * 1. Usuario elige una imagen.
 * 2. Se muestra dentro del scan-frame.
 * 3. Se manda a POST /api/detect.
 * 4. Se dibujan las cajas sobre la imagen y una lista debajo con
 *    botón para agregar cada objeto detectado al inventario.
 */
function setupPhotoDetection() {
  const input = document.getElementById('photoInput');
  const chooseBtn = document.getElementById('choosePhoto');
  const scanImage = document.getElementById('scanImage');
  const placeholder = document.getElementById('scanPlaceholder');
  const scanLine = document.getElementById('scanLine');
  const badge = document.getElementById('scanBadge');
  const hint = document.getElementById('detectHint');

  chooseBtn.addEventListener('click', () => input.click());

  input.addEventListener('change', async () => {
    const file = input.files[0];
    if (!file) return;

    const sizeKB = (file.size / 1024).toFixed(1);
    console.info(
      `[CyberTrack] Foto seleccionada: nombre="${file.name}" tipo="${file.type}" tamaño=${sizeKB}KB`
    );

    // Se muestra en pantalla, no solo en consola — así no hace falta
    // abrir las herramientas de desarrollador para ver el diagnóstico.
    hint.textContent = `Foto: ${file.name || '(sin nombre)'} · ${file.type || 'tipo desconocido'} · ${sizeKB} KB`;
    hint.classList.remove('is-error');

    if (file.size === 0) {
      hint.textContent =
        `"${file.name}" pesa 0 KB — es común cuando una foto vive solo en iCloud y ` +
        'no se ha descargado al equipo todavía. Ábrela una vez en Fotos o Finder ' +
        'para que se descargue, y vuelve a intentar.';
      hint.classList.add('is-error');
      setBadge(badge, 'error', 'is-error');
      return;
    }

    // Mostrar la foto de inmediato, antes de que responda el backend.
    const objectUrl = URL.createObjectURL(file);
    scanImage.src = objectUrl;
    scanImage.hidden = false;
    placeholder.hidden = true;
    document.getElementById('detectionTags').innerHTML = '';
    document.getElementById('detectionResults').hidden = true;

    setBadge(badge, 'analizando…', 'is-scanning');
    scanLine.classList.add('is-active');

    try {
      const formData = new FormData();
// Safari necesita que el tercer parámetro sea explícito y con extensión conocida
const safeName = file.name || 'photo.jpg';
formData.append('file', file, safeName);

      const response = await fetch(`${API_BASE}/api/detect`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(extractErrorMessage(body, response.status));
      }

      const result = await response.json();
      drawDetectionTags(result.detections);
      await autoAddAllDetections(result.detections);

      hint.textContent =
        result.count === 0
          ? 'No se detectó nada reconocible con el modelo genérico actual.'
          : `${result.count} objeto(s) detectado(s) y agregado(s) — ${result.model}`;
      setBadge(badge, `${result.count} detección(es)`, 'is-ready');
    } catch (error) {
      hint.textContent = `No se pudo analizar la foto: ${error.message}`;
      hint.classList.add('is-error');
      setBadge(badge, 'error', 'is-error');
      console.error('[CyberTrack] Error en detección:', error);
    } finally {
      scanLine.classList.remove('is-active');
    }
  });
}

function setBadge(badge, text, stateClass) {
  badge.classList.remove('is-ready', 'is-scanning', 'is-error');
  badge.classList.add(stateClass);
  badge.innerHTML = `<span class="dot"></span> ${text}`;
}

/**
 * Dibuja las etiquetas de detección sobre la imagen.
 *
 * Con Gemini, `det.box` siempre viene como null — a diferencia de YOLO,
 * Gemini identifica QUÉ pieza es pero no da coordenadas exactas de
 * dónde está en la foto. Si algún día el detector vuelve a dar
 * coordenadas (YOLO u otro modelo de detección real), esta función ya
 * las dibuja sin cambios.
 */
function drawDetectionTags(detections) {
  const container = document.getElementById('detectionTags');
  container.innerHTML = '';

  detections.forEach((det) => {
    if (!det.box) return; // Gemini no da posición — no hay dónde dibujar la etiqueta

    const tag = document.createElement('div');
    tag.className = 'detection-tag';
    tag.style.top = `${det.box.y * 100}%`;
    tag.style.left = `${det.box.x * 100}%`;
    tag.innerHTML = `<span>${escapeHtml(det.label)}</span><b>${Math.round(det.confidence * 100)}%</b>`;
    container.appendChild(tag);
  });
}

/**
 * Agrega automáticamente CADA pieza que Gemini detectó, sin pedir
 * clic. Se procesan una por una (no en paralelo) para que si dos
 * detecciones de la misma foto generan el mismo código, la segunda
 * vea ya creada a la primera y sume cantidad en vez de chocar.
 *
 * Cada fila muestra su estado en vivo (Agregando… → ✓ Agregada) y un
 * botón "Deshacer" por si Gemini se equivocó — la responsabilidad de
 * revisar sigue siendo del usuario, solo que después del hecho en vez
 * de antes.
 */
async function autoAddAllDetections(detections) {
  const section = document.getElementById('detectionResults');
  const list = document.getElementById('detectionList');
  list.innerHTML = '';
  section.hidden = detections.length === 0;

  for (const det of detections) {
    const item = document.createElement('div');
    item.className = 'detection-item';
    item.innerHTML = `
      <div class="detection-item__info">
        <span class="detection-item__label">${escapeHtml(det.label)}</span>
        <span class="detection-item__meta">${escapeHtml(det.category || 'General')} · ${escapeHtml(det.code || '')} · confianza ${Math.round(det.confidence * 100)}%</span>
      </div>
      <span class="detection-item__status" data-status>Agregando…</span>
    `;
    list.appendChild(item);

    await autoAddDetection(det, item.querySelector('[data-status]'));
  }
}

/**
 * Agrega (o suma cantidad, si el código ya existía) una sola
 * detección, y deja el resultado + botón "Deshacer" en `statusEl`.
 */
async function autoAddDetection(det, statusEl) {
  const payload = {
    name: capitalize(det.label),
    code: (det.code || detectionFallbackCode(det.label)).toUpperCase(),
    category: det.category || 'General',
    quantity: 1,
    low_stock_threshold: 2,
  };

  try {
    const response = await fetch(`${API_BASE}/api/inventory`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (response.status === 409) {
      await bumpExistingPartQuantity(payload.code, statusEl);
      return;
    }

    if (!response.ok) {
      const body = await response.json().catch(() => null);
      throw new Error(extractErrorMessage(body, response.status));
    }

    const created = await response.json();
    statusEl.innerHTML = '';
    statusEl.appendChild(document.createTextNode('✓ Agregada '));
    statusEl.appendChild(makeUndoLink(created.id, created.name));
    await loadInventory();
  } catch (error) {
    statusEl.textContent = `✗ No se pudo agregar: ${error.message}`;
    statusEl.classList.add('is-error');
    console.error('[CyberTrack] Error al agregar desde detección:', error);
  }
}

/**
 * Busca la pieza existente por código en el inventario ya cargado y le
 * suma 1 unidad. Si por alguna razón no la encuentra en la caché local
 * (poco probable, pero mejor no fallar en silencio), recarga el
 * inventario primero e intenta una vez más antes de rendirse.
 */
async function bumpExistingPartQuantity(code, statusEl) {
  let existing = inventoryCache.find((p) => p.code.toUpperCase() === code);

  if (!existing) {
    await loadInventory();
    existing = inventoryCache.find((p) => p.code.toUpperCase() === code);
  }

  if (!existing) {
    statusEl.textContent = '✗ No se encontró la pieza existente para sumarle.';
    statusEl.classList.add('is-error');
    return;
  }

  try {
    const response = await fetch(`${API_BASE}/api/inventory/${existing.id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ quantity: existing.quantity + 1 }),
    });
    if (!response.ok) throw new Error(`El servidor respondió ${response.status}`);

    statusEl.textContent = `✓ Ya tenías esta — ahora son ${existing.quantity + 1}`;
    await loadInventory();
  } catch (error) {
    statusEl.textContent = `✗ No se pudo actualizar la cantidad: ${error.message}`;
    statusEl.classList.add('is-error');
    console.error('[CyberTrack] Error al sumar cantidad existente:', error);
  }
}

/**
 * Botón "Deshacer" para una pieza recién agregada automáticamente —
 * la elimina sin pedir confirmación (a diferencia del botón de la
 * tabla de inventario), porque acaba de pasar hace un segundo y el
 * usuario ya está viendo exactamente qué está deshaciendo.
 */
function makeUndoLink(partId, partName) {
  const link = document.createElement('button');
  link.type = 'button';
  link.className = 'detection-item__undo';
  link.textContent = 'Deshacer';
  link.addEventListener('click', async () => {
    link.disabled = true;
    link.textContent = 'Deshaciendo…';
    try {
      const response = await fetch(`${API_BASE}/api/inventory/${partId}`, { method: 'DELETE' });
      if (!response.ok && response.status !== 204) throw new Error(`status ${response.status}`);
      link.parentElement.textContent = `— eliminada (${partName})`;
      await loadInventory();
    } catch (error) {
      link.disabled = false;
      link.textContent = 'Deshacer';
      window.alert('No se pudo deshacer. Puedes eliminarla manualmente desde el inventario.');
      console.error('[CyberTrack] Error al deshacer:', error);
    }
  });
  return link;
}

/**
 * Agrega una detección directo al inventario, sin pasar por el modal.
 * Cantidad fija en 1 (el usuario la corrige después en la tabla) y
 * umbral de stock bajo en 2 como default razonable.
 *
 * Si el código ya existe (Gemini detectó otra vez el mismo tipo de
 * pieza que ya tienes registrada), en vez de pedir que lo resuelvas a
 * mano, le suma 1 a la cantidad que ya tenía — es la interpretación
 * más natural: "encontré otra unidad de esto".
 */
async function quickAddFromDetection(det, button) {
  const originalText = button.textContent;
  button.disabled = true;
  button.textContent = 'Agregando…';

  const payload = {
    name: capitalize(det.label),
    code: (det.code || detectionFallbackCode(det.label)).toUpperCase(),
    category: det.category || 'General',
    quantity: 1,
    low_stock_threshold: 2,
  };

  try {
    const response = await fetch(`${API_BASE}/api/inventory`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (response.status === 409) {
      await bumpExistingPartQuantity(payload.code, button, originalText);
      return;
    }

    if (!response.ok) {
      const body = await response.json().catch(() => null);
      throw new Error(extractErrorMessage(body, response.status));
    }

    button.textContent = '✓ Agregado';
    await loadInventory();
  } catch (error) {
    console.error('[CyberTrack] Error al agregar desde detección:', error);
    button.disabled = false;
    button.textContent = originalText;
    window.alert(`No se pudo agregar: ${error.message}`);
  }
}

/**
 * Busca la pieza existente por código en el inventario ya cargado y le
 * suma 1 unidad. Si por alguna razón no la encuentra en la caché local
 * (poco probable, pero mejor no fallar en silencio), recarga el
 * inventario primero e intenta una vez más antes de rendirse.
 */
async function bumpExistingPartQuantity(code, button, originalText) {
  let existing = inventoryCache.find((p) => p.code.toUpperCase() === code);

  if (!existing) {
    await loadInventory();
    existing = inventoryCache.find((p) => p.code.toUpperCase() === code);
  }

  if (!existing) {
    // No debería pasar, pero si pasa, dejamos que el usuario lo resuelva a mano.
    window.openAddPartModal({ name: capitalize(code), quantity: 1 });
    button.disabled = false;
    button.textContent = originalText;
    return;
  }

  try {
    const response = await fetch(`${API_BASE}/api/inventory/${existing.id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ quantity: existing.quantity + 1 }),
    });
    if (!response.ok) throw new Error(`El servidor respondió ${response.status}`);

    button.textContent = `✓ Ya tenías esta — ahora son ${existing.quantity + 1}`;
    await loadInventory();
  } catch (error) {
    console.error('[CyberTrack] Error al sumar cantidad existente:', error);
    button.disabled = false;
    button.textContent = originalText;
    window.alert('No se pudo actualizar la cantidad de la pieza existente.');
  }
}

/**
 * Respaldo por si Gemini no sugiere un código utilizable (raro, pero
 * mejor no tronar): usa las primeras letras del nombre + 3 dígitos.
 */
function detectionFallbackCode(label) {
  const letters = label.replace(/[^a-zA-Z]/g, '').slice(0, 4).toUpperCase() || 'PZA';
  const suffix = Math.floor(100 + Math.random() * 900);
  return `${letters}-${suffix}`;
}

function capitalize(text) {
  return text.charAt(0).toUpperCase() + text.slice(1);
}

/**
 * Chat del asistente. El historial ahora vive en la base de datos
 * (tabla assistant_messages) — se carga completo al abrir la página
 * y cada pregunta/respuesta se guarda sola en el backend. Aquí solo
 * se mantiene una copia en memoria para no tener que volver a pedirlo
 * en cada pregunta nueva.
 */
const MAX_CONTEXT_MESSAGES = 20; // cuántos mensajes recientes se le mandan a Groq como contexto

function setupAssistant() {
  const form = document.getElementById('assistantForm');
  const input = document.getElementById('assistantInput');
  const chat = document.getElementById('assistantChat');
  const emptyState = document.getElementById('assistantEmpty');
  const sendButton = document.getElementById('assistantSend');

  const history = []; // [{role: 'user'|'assistant', content: '...'}]

  loadAssistantHistory(chat, emptyState, history);

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const question = input.value.trim();
    if (!question) return;

    emptyState?.remove();
    appendAssistantMessage(chat, 'user', question);
    history.push({ role: 'user', content: question });
    input.value = '';
    input.disabled = true;
    sendButton.disabled = true;

    const pending = appendAssistantMessage(chat, 'pending', 'Pensando…');

    try {
      const response = await fetch(`${API_BASE}/api/assistant/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question,
          // Mandamos el historial SIN el mensaje que acabamos de agregar
          // (el backend lo agrega aparte como el mensaje "user" actual),
          // y solo los últimos N para no mandar una conversación gigante.
          history: history.slice(0, -1).slice(-MAX_CONTEXT_MESSAGES),
        }),
      });

      const body = await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(extractErrorMessage(body, response.status));
      }

      pending.remove();
      appendAssistantMessage(chat, 'assistant', body.answer);
      history.push({ role: 'assistant', content: body.answer });
      // El backend ya guardó estos dos mensajes en la base de datos.
    } catch (error) {
      pending.remove();
      appendAssistantMessage(
        chat,
        'error',
        `No se pudo consultar al asistente: ${error.message}`
      );
      console.error('[CyberTrack] Error del asistente:', error);
    } finally {
      input.disabled = false;
      sendButton.disabled = false;
      input.focus();
    }
  });
}

/**
 * Pide el historial guardado al backend y lo dibuja en el chat, en
 * orden, antes de que el usuario escriba nada nuevo. Si falla (ej.
 * backend apagado), no rompe el chat — simplemente arranca vacío,
 * como si fuera la primera vez.
 */
async function loadAssistantHistory(chat, emptyState, history) {
  try {
    const response = await fetch(`${API_BASE}/api/assistant/history`);
    if (!response.ok) return;

    const messages = await response.json();
    if (messages.length === 0) return;

    emptyState?.remove();
    messages.forEach((msg) => {
      appendAssistantMessage(chat, msg.role, msg.content);
      history.push({ role: msg.role, content: msg.content });
    });
  } catch (error) {
    console.error('[CyberTrack] No se pudo cargar el historial del asistente:', error);
  }
}

function appendAssistantMessage(chat, role, text) {
  const bubble = document.createElement('div');
  bubble.className = `assistant__msg assistant__msg--${role}`;
  bubble.textContent = text;
  chat.appendChild(bubble);
  chat.scrollTop = chat.scrollHeight;
  return bubble;
}

// ---------------- utilidades ----------------

/**
 * Convierte el cuerpo de un error del backend en un texto legible.
 *
 * FastAPI manda el error de dos formas MUY distintas:
 *   - Errores que nosotros mismos lanzamos (HTTPException): detail es
 *     un STRING, ej. {"detail": "Ya existe una pieza con ese código"}.
 *   - Errores de validación automática (422, antes de que nuestro
 *     código corra): detail es una LISTA de objetos, ej.
 *     {"detail": [{"loc": [...], "msg": "field required", ...}]}.
 *
 * Sin esto, un 422 se mostraba como "[object Object]" — nada útil.
 */
function extractErrorMessage(body, status) {
  const detail = body?.detail;

  if (typeof detail === 'string') return detail;

  if (Array.isArray(detail)) {
    const messages = detail.map((e) => e.msg || JSON.stringify(e)).join('; ');
    return messages || `El servidor respondió ${status}`;
  }

  return `El servidor respondió ${status}`;
}

function groupBy(items, keyFn) {
  return items.reduce((acc, item) => {
    const key = keyFn(item);
    (acc[key] ||= []).push(item);
    return acc;
  }, {});
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}
