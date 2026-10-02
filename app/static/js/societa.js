// Espande/chiude il dettaglio di un record sociale
function toggleResults(element) {
    const row = element.closest('.pb-row');
    row.querySelector('.pb-details-container').classList.toggle('active');
    row.querySelector('.toggle-icon').classList.toggle('expanded');
}

document.addEventListener('DOMContentLoaded', function () {
    const root = document.querySelector('.societa-profile');
    if (!root) return;

    // ---------- Cambio sezione (Record / Stagionali / Ultimi / Atleti) ----------
    const buttons = root.querySelectorAll('.toggle-btn');
    const sections = root.querySelectorAll('.results-section');

    function showSection(name) {
        buttons.forEach(b => b.classList.toggle('active', b.dataset.section === name));
        sections.forEach(s => s.classList.toggle('active', s.id === 'section-' + name));
        history.replaceState(null, '', '#' + name);
    }

    buttons.forEach(b => b.addEventListener('click', () => showSection(b.dataset.section)));

    // Permette link diretti tipo /societa/RM100#atleti
    const hash = window.location.hash.slice(1);
    if (hash && document.getElementById('section-' + hash)) showSection(hash);

    // ---------- Filtri (sesso, ambiente, anno, ricerca, solo attivi) ----------
    root.querySelectorAll('[data-filter-bar]').forEach(bar => {
        // ---------- Filtri lato server (categoria, periodo): ricarica mantenendo la sezione (#hash) ----------
        root.querySelectorAll('[data-param]').forEach(el => {
            el.addEventListener('change', () => {
                const url = new URL(window.location.href);
                if (el.value) url.searchParams.set(el.dataset.param, el.value);
                else url.searchParams.delete(el.dataset.param);
                window.location.href = url.toString();
            });
        });
        const section = bar.closest('.results-section');
        const get = name => bar.querySelector(`[data-filter="${name}"]`);

        function apply() {
            const sesso = get('sesso') ? get('sesso').value : '';
            const ambiente = get('ambiente') ? get('ambiente').value : '';
            const q = get('q') ? get('q').value.trim().toLowerCase() : '';
            const soloAttivi = get('attivi') ? get('attivi').checked : false;
            const anno = get('anno') ? get('anno').value : null;

            // Primati stagionali: mostra solo la stagione scelta
            if (anno !== null) {
                section.querySelectorAll('.season-block').forEach(b => {
                    b.style.display = b.dataset.anno === anno ? '' : 'none';
                });
            }

            section.querySelectorAll('[data-sesso]').forEach(el => {
                let ok = true;
                if (sesso && el.dataset.sesso !== sesso) ok = false;
                if (ambiente && el.dataset.ambiente !== ambiente) ok = false;
                if (q && !(el.dataset.nome || '').includes(q)) ok = false;
                if (soloAttivi && el.dataset.attivo !== '1') ok = false;
                el.style.display = ok ? '' : 'none';
            });
        }

        bar.querySelectorAll('select:not([data-param]), input').forEach(i => {
            i.addEventListener('input', apply);
            i.addEventListener('change', apply);
        });
    });

    // ---------- Ordinamento tabella atleti ----------
    root.querySelectorAll('table.sortable-generic').forEach(table => {
        const headers = table.querySelectorAll('thead th[data-type]');

        headers.forEach(th => {
            th.addEventListener('click', () => {
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
        });
    });
});
