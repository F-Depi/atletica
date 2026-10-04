// Espande/chiude il dettaglio di un record sociale
function toggleResults(element) {
    const row = element.closest('.pb-row');
    row.querySelector('.pb-details-container').classList.toggle('active');
    row.querySelector('.toggle-icon').classList.toggle('expanded');
}

document.addEventListener('DOMContentLoaded', function () {
    const root = document.querySelector('.societa-profile');
    if (!root) return;

    const baseUrl = root.dataset.baseUrl;
    const buttons = root.querySelectorAll('.toggle-btn');
    const sections = root.querySelectorAll('.results-section');
    const sectionEl = name => document.getElementById('section-' + name);

    // ---------- Caricamento a richiesta delle schede ----------
    // Le schede diverse da "Record sociali" sono frammenti HTML scaricati al primo uso.
    // Il querystring della pagina (categoria, periodo) viene inoltrato al server.
    const lazyUrl = {
        stagionali() {
            const sel = sectionEl('stagionali').querySelector('[data-filter="anno"]');
            return sel ? `${baseUrl}/stagionali/${encodeURIComponent(sel.value)}${location.search}` : null;
        },
        recenti: () => `${baseUrl}/recenti${location.search}`,
        atleti: () => `${baseUrl}/atleti${location.search}`,
    };

    const fetchCache = new Map(); // url -> Promise<string>
    function fetchHtml(url) {
        if (!fetchCache.has(url)) {
            const p = fetch(url).then(r => {
                if (!r.ok) throw new Error(r.status);
                return r.text();
            });
            p.catch(() => fetchCache.delete(url)); // in caso di errore si può riprovare
            fetchCache.set(url, p);
        }
        return fetchCache.get(url);
    }

    async function ensureLoaded(name) {
        const section = sectionEl(name);
        const box = section && section.querySelector('[data-lazy]');
        const url = lazyUrl[name] && lazyUrl[name]();
        if (!box || !url || box.dataset.loaded === url) return;

        box.classList.add('loading');
        try {
            box.innerHTML = await fetchHtml(url);
            box.dataset.loaded = url;
            applyFilters(section); // riapplica sesso/ambiente/ricerca al nuovo contenuto
        } catch (e) {
            box.innerHTML = '<p class="no-results">Errore nel caricamento. Ricarica la pagina.</p>';
        } finally {
            box.classList.remove('loading');
        }
    }

    // ---------- Cambio sezione (Record / Stagionali / Ultimi / Atleti) ----------
    function showSection(name) {
        buttons.forEach(b => b.classList.toggle('active', b.dataset.section === name));
        sections.forEach(s => s.classList.toggle('active', s.id === 'section-' + name));
        history.replaceState(null, '', '#' + name);
        ensureLoaded(name);
    }

    buttons.forEach(b => {
        b.addEventListener('click', () => showSection(b.dataset.section));
        // Precarica appena il dito/mouse si avvicina al tab: il click trova già la risposta
        const prefetch = () => {
            const url = lazyUrl[b.dataset.section] && lazyUrl[b.dataset.section]();
            if (url) fetchHtml(url).catch(() => {});
        };
        b.addEventListener('mouseenter', prefetch, { once: true });
        b.addEventListener('touchstart', prefetch, { once: true, passive: true });
    });

    // ---------- Filtri lato client (sesso, ambiente, ricerca, solo attivi) ----------
    function applyFilters(section) {
        const bar = section.querySelector('[data-filter-bar]');
        if (!bar) return;
        const ctl = name => bar.querySelector(`[data-filter="${name}"]`);

        const sesso = ctl('sesso') ? ctl('sesso').value : '';
        const ambiente = ctl('ambiente') ? ctl('ambiente').value : '';
        const q = ctl('q') ? ctl('q').value.trim().toLowerCase() : '';
        const soloAttivi = ctl('attivi') ? ctl('attivi').checked : false;

        section.querySelectorAll('[data-sesso]').forEach(el => {
            let ok = true;
            if (sesso && el.dataset.sesso !== sesso) ok = false;
            if (ambiente && el.dataset.ambiente !== ambiente) ok = false;
            if (q && !(el.dataset.nome || '').includes(q)) ok = false;
            if (soloAttivi && el.dataset.attivo !== '1') ok = false;
            el.style.display = ok ? '' : 'none';
        });
    }

    // Filtri lato server (categoria, periodo): ricarica la pagina mantenendo la sezione (#hash).
    // Un solo listener delegato per tutta la pagina.
    root.addEventListener('change', e => {
        const t = e.target;

        if (t.matches('[data-param]')) {
            const url = new URL(window.location.href);
            if (t.value) url.searchParams.set(t.dataset.param, t.value);
            else url.searchParams.delete(t.dataset.param);
            window.location.href = url.toString();
            return;
        }

        if (!t.matches('[data-filter-bar] [data-filter]')) return;
        const section = t.closest('.results-section');
        if (t.dataset.filter === 'anno') ensureLoaded('stagionali'); // cambia stagione: altro frammento
        else applyFilters(section);
    });

    // Ricerca atleta mentre si digita (con un piccolo debounce)
    let searchTimer;
    root.addEventListener('input', e => {
        if (!e.target.matches('[data-filter="q"]')) return;
        clearTimeout(searchTimer);
        const section = e.target.closest('.results-section');
        searchTimer = setTimeout(() => applyFilters(section), 120);
    });

    // ---------- Ordinamento tabella atleti (delegato: la tabella arriva dopo) ----------
    root.addEventListener('click', e => {
        const th = e.target.closest('table.sortable-generic th[data-type]');
        if (!th) return;

        const table = th.closest('table');
        const headers = table.querySelectorAll('thead th[data-type]');
        const idx = Array.from(th.parentNode.children).indexOf(th);
        const dir = th.dataset.dir === 'asc' ? 'desc' : 'asc';
        const isNum = th.dataset.type === 'num';

        headers.forEach(h => {
            delete h.dataset.dir;
            h.querySelector('.sort-icon').textContent = '';
        });
        th.dataset.dir = dir;
        th.querySelector('.sort-icon').textContent = dir === 'asc' ? '▲' : '▼';

        const value = row => {
            const cell = row.cells[idx];
            const v = cell.dataset.value !== undefined ? cell.dataset.value : cell.textContent.trim();
            return isNum ? (parseFloat(v) || 0) : v.toLowerCase();
        };

        const tbody = table.tBodies[0];
        const rows = Array.from(tbody.rows);
        rows.sort((a, b) => {
            const x = value(a), y = value(b);
            const c = isNum ? x - y : x.localeCompare(y);
            return dir === 'asc' ? c : -c;
        });
        rows.forEach(r => tbody.appendChild(r));
    });

    // ---------- Avvio ----------
    sections.forEach(applyFilters); // applica subito i default (es. sesso preselezionato)

    // Permette link diretti tipo /societa/RM100#atleti
    const hash = window.location.hash.slice(1);
    if (hash && sectionEl(hash)) showSection(hash);
});
