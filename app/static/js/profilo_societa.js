// Toggle between sections
document.addEventListener('DOMContentLoaded', function() {
    const toggleBtns = document.querySelectorAll('.toggle-btn');
    const sections = {
        'seasonal': document.getElementById('seasonal-section'),
        'recent': document.getElementById('recent-section'),
        'athletes': document.getElementById('athletes-section'),
        'records': document.getElementById('records-section')
    };

    toggleBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const sectionId = this.getAttribute('data-section');
            
            // Update buttons
            toggleBtns.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            
            // Update sections
            Object.values(sections).forEach(section => {
                if (section) section.classList.remove('active');
            });
            if (sections[sectionId]) {
                sections[sectionId].classList.add('active');
            }
        });
    });

    // Initialize sorting on all sortable tables
    initializeSortableTables();
    
    // Initialize filters
    initializeFilters();
});

// Toggle seasonal results details
function toggleSeasonalResults(element) {
    const container = element.closest('.seasonal-row');
    const detailsContainer = container.querySelector('.details-container');
    const toggleIcon = container.querySelector('.toggle-icon');

    if (detailsContainer.classList.contains('active')) {
        detailsContainer.classList.remove('active');
        toggleIcon.classList.remove('expanded');
    } else {
        detailsContainer.classList.add('active');
        toggleIcon.classList.add('expanded');
    }
}

// Toggle record details
function toggleRecordDetails(element) {
    const container = element.closest('.record-row');
    const detailsContainer = container.querySelector('.details-container');
    const toggleIcon = container.querySelector('.toggle-icon');

    if (detailsContainer.classList.contains('active')) {
        detailsContainer.classList.remove('active');
        toggleIcon.classList.remove('expanded');
    } else {
        detailsContainer.classList.add('active');
        toggleIcon.classList.add('expanded');
    }
}


// Gestione cambio stagione
document.getElementById('season-select')?.addEventListener('change', async function() {
    const year = this.value;
    const codSocieta = window.location.pathname.split('/').pop();
    
    try {
        const response = await fetch(`/societa/${codSocieta}/seasonal?year=${year}`);
        const data = await response.json();
        
        if (data.error) {
            console.error(data.error);
            return;
        }
        
        updateSeasonalResults(data.results, data.discipline_order);
        
    } catch (error) {
        console.error('Errore nel caricamento dei risultati:', error);
    }
});


// Sostituisci la funzione updateSeasonalResults esistente
function updateSeasonalResults(results, disciplineOrder) {
    const container = document.querySelector('.seasonal-list');
    
    if (!container) return;
    
    // Se non ci sono risultati
    if (!results || Object.keys(results).length === 0) {
        container.innerHTML = '<p class="no-results">Nessun risultato stagionale disponibile per questa stagione.</p>';
        return;
    }
    
    let html = '';
    
    // Usa l'ordine fornito dal server (che ora gestisce già M/F)
    const orderedKeys = disciplineOrder || Object.keys(results);
    
    for (const key of orderedKeys) {
        const disciplineData = results[key];
        
        if (!disciplineData) continue;
        
        // Estraggo nome base e genere dai dati forniti dall'API
        const baseName = disciplineData.base_discipline ? disciplineData.base_discipline.replace(/_/g, ' ') : key;
        const gender = disciplineData.gender || '';
        
        const best = disciplineData.best;
        const resultsList = disciplineData.results;
        
        html += `
        <div class="seasonal-row gender-${gender}" data-discipline="${key}">
            <div class="seasonal-header" onclick="toggleSeasonalResults(this)">
                <div class="discipline-name">
                    ${baseName}
                    ${gender ? `<span class="gender-badge ${gender}">${gender}</span>` : ''}
                </div>
                <div class="result-count">
                    <span class="count-badge">${resultsList.length}</span>
                </div>
                <div class="best-result">
                    <span class="result"><b>${best.prestazione_display}</b></span>
                    ${best.vento ? `<span class="wind">(${best.vento})</span>` : ''}
                </div>
                <span class="toggle-icon">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M6 9l6 6 6-6"/>
                    </svg>
                </span>
            </div>

            <div class="details-container">
                <table class="results-table sortable">
                    <thead>
                        <tr>
                            <th class="sortable-header sort-default" data-sort="result">Pres. <span class="sort-icon">▼</span></th>
                            <th>Atleta</th>
                            <th class="sortable-header" data-sort="date">Data <span class="sort-icon"></span></th>
                            <th>Luogo</th>
                            <th>Cat.</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${resultsList.map(result => `
                        <tr data-raw-result="${result.prestazione || 0}"
                            data-raw-date="${result.data ? result.data.split('/').reverse().join('') : '00000000'}">
                            <td class="result">
                                ${result.prestazione_display}
                                ${result.vento ? `<span class="wind"> (${result.vento})</span>` : ''}
                            </td>
                            <td class="athlete-name">
                                <a href="/atleti/${result.atleta_link}">
                                    ${result.atleta}
                                </a>
                            </td>
                            <td class="date">${result.data || '-'}</td>
                            <td class="location">${result.luogo || '-'}</td>
                            <td class="category">${result.categoria || '-'}</td>
                        </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        </div>
        `;
    }
    
    container.innerHTML = html;
    
    // Re-initialize sortable tables for new content
    initializeSortableTables();
}

// Build HTML for a seasonal row
function buildSeasonalRowHTML(discipline, data) {
    const displayName = discipline.replace(/_/g, ' ');
    const windDisplay = data.best.vento ? `<span class="wind">(${data.best.vento})</span>` : '';
    
    let rowsHTML = '';
    data.results.forEach(result => {
        const windCell = result.vento ? `<span class="wind"> (${result.vento})</span>` : '';
        rowsHTML += `
            <tr data-raw-result="${result.prestazione || 0}" data-raw-date="${result.data ? result.data.replace(/\//g, '') : '00000000'}">
                <td class="result">${result.prestazione_display}${windCell}</td>
                <td class="athlete-name"><a href="/atleta/${result.atleta_link}">${result.atleta}</a></td>
                <td class="date">${result.data || '-'}</td>
                <td class="location">${result.luogo || '-'}</td>
                <td class="category">${result.categoria || '-'}</td>
            </tr>
        `;
    });
    
    return `
        <div class="seasonal-row" data-discipline="${displayName}">
            <div class="seasonal-header" onclick="toggleSeasonalResults(this)">
                <div class="discipline-name">${displayName}</div>
                <div class="result-count"><span class="count-badge">${data.results.length}</span></div>
                <div class="best-result">
                    <span class="result"><b>${data.best.prestazione_display}</b></span>
                    ${windDisplay}
                </div>
                <span class="toggle-icon">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M6 9l6 6 6-6"/>
                    </svg>
                </span>
            </div>
            <div class="details-container">
                <table class="results-table sortable">
                    <thead>
                        <tr>
                            <th class="sortable-header sort-default" data-sort="result">Pres. <span class="sort-icon">▼</span></th>
                            <th>Atleta</th>
                            <th class="sortable-header" data-sort="date">Data <span class="sort-icon"></span></th>
                            <th>Luogo</th>
                            <th>Cat.</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${rowsHTML}
                    </tbody>
                </table>
            </div>
        </div>
    `;
}

// Initialize filters
function initializeFilters() {
    // Season filter
    const seasonSelect = document.getElementById('season-select');
    if (seasonSelect) {
        seasonSelect.addEventListener('change', function() {
            const year = this.value;
            loadSeasonalResults(year);
        });
    }

    // Athlete search filter
    const athleteSearch = document.getElementById('athlete-search');
    if (athleteSearch) {
        athleteSearch.addEventListener('input', debounce(function() {
            filterAthletes();
        }, 300));
    }

    // Category filter
    const categoryFilter = document.getElementById('category-filter');
    if (categoryFilter) {
        categoryFilter.addEventListener('change', function() {
            filterAthletes();
        });
    }

    // Gender filter
    const genderFilter = document.getElementById('gender-filter');
    if (genderFilter) {
        genderFilter.addEventListener('change', function() {
            filterAthletes();
        });
    }

    // Status filter (active/historical)
    const statusFilter = document.getElementById('status-filter');
    if (statusFilter) {
        statusFilter.addEventListener('change', function() {
            filterAthletes();
        });
    }

    // Discipline type filter for records
    const disciplineTypeFilter = document.getElementById('discipline-type-filter');
    if (disciplineTypeFilter) {
        disciplineTypeFilter.addEventListener('change', function() {
            filterRecords();
        });
    }
}

// Filter athletes
function filterAthletes() {
    const searchTerm = document.getElementById('athlete-search')?.value.toLowerCase() || '';
    const categoryFilter = document.getElementById('category-filter')?.value || '';
    const genderFilter = document.getElementById('gender-filter')?.value || '';
    const statusFilter = document.getElementById('status-filter')?.value || '';
    
    const athleteCards = document.querySelectorAll('.athlete-card');
    let visibleCount = 0;
    
    athleteCards.forEach(card => {
        const name = card.getAttribute('data-name') || '';
        const category = card.getAttribute('data-category') || '';
        const gender = card.getAttribute('data-gender') || '';
        const isActive = card.getAttribute('data-active') === 'true';
        
        const matchesSearch = name.includes(searchTerm);
        const matchesCategory = !categoryFilter || category === categoryFilter;
        const matchesGender = !genderFilter || gender === genderFilter;
        
        let matchesStatus = true;
        if (statusFilter === 'active') {
            matchesStatus = isActive;
        } else if (statusFilter === 'historical') {
            matchesStatus = !isActive;
        }
        
        if (matchesSearch && matchesCategory && matchesGender && matchesStatus) {
            card.style.display = '';
            visibleCount++;
        } else {
            card.style.display = 'none';
        }
    });

    // Update visible count indicator
    const countIndicator = document.getElementById('visible-athletes-count');
    if (countIndicator) {
        countIndicator.textContent = visibleCount;
    }
}

// Filter records by discipline type
function filterRecords() {
    const typeFilter = document.getElementById('discipline-type-filter')?.value || '';
    
    const recordRows = document.querySelectorAll('.record-row');
    
    recordRows.forEach(row => {
        const type = row.getAttribute('data-type') || '';
        
        if (!typeFilter || type === typeFilter) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
}

// Debounce utility
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Table sorting functionality
function initializeSortableTables() {
    const sortableTables = document.querySelectorAll('table.sortable');

    sortableTables.forEach(table => {
        const headers = table.querySelectorAll('th.sortable-header');

        headers.forEach(header => {
            // Remove existing listeners by cloning
            const newHeader = header.cloneNode(true);
            header.parentNode.replaceChild(newHeader, header);
            
            newHeader.addEventListener('click', function() {
                const sortDirection = this.classList.contains('sort-asc') ? 'desc' : 'asc';

                // Reset all headers in this table
                const allHeaders = table.querySelectorAll('th.sortable-header');
                allHeaders.forEach(h => {
                    h.classList.remove('sort-asc', 'sort-desc');
                    const icon = h.querySelector('.sort-icon');
                    if (icon) icon.textContent = '';
                });

                // Set current header
                this.classList.add('sort-' + sortDirection);
                const sortIcon = this.querySelector('.sort-icon');
                if (sortIcon) {
                    sortIcon.textContent = sortDirection === 'asc' ? '▲' : '▼';
                }

                // Sort the table
                sortTable(table, this, sortDirection);
            });
        });
    });
}

function sortTable(table, header, direction) {
    const sortType = header.getAttribute('data-sort');
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));

    let compareFunc;
    switch(sortType) {
        case 'result':
            compareFunc = (a, b) => {
                const aVal = parseFloat(a.getAttribute('data-raw-result')) || 0;
                const bVal = parseFloat(b.getAttribute('data-raw-result')) || 0;
                return direction === 'asc' ? aVal - bVal : bVal - aVal;
            };
            break;

        case 'date':
            compareFunc = (a, b) => {
                const aVal = a.getAttribute('data-raw-date') || '00000000';
                const bVal = b.getAttribute('data-raw-date') || '00000000';
                return direction === 'asc' ? 
                    aVal.localeCompare(bVal) : 
                    bVal.localeCompare(aVal);
            };
            break;

        default:
            return;
    }

    rows.sort(compareFunc);
    rows.forEach(row => tbody.appendChild(row));
}
