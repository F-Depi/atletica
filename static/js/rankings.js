class TabFilterManager {
    constructor() {
        this.tabs = document.querySelectorAll('.tab-btn');
        this.tabContents = document.querySelectorAll('.tab-content');
        this.currentTab = null;

        // Inizializza i gestori dei filtri per ogni tab
        this.menFilters = new StandardFilterManager('men', 'M');
        this.womenFilters = new StandardFilterManager('women', 'F');
        this.advancedFilters = new AdvancedFilterManager();

        this.initializeEventListeners();
        
        // Attiva il tab iniziale basato sull'URL o default a 'men'
        const urlParams = new URLSearchParams(window.location.search);
        const initialTab = urlParams.get('tab') || 'men';
        this.activateTab(initialTab);
    }

    initializeEventListeners() {
        this.tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                this.activateTab(tab.dataset.tab);
            });
        });
    }

    activateTab(tabId) {
        this.tabs.forEach(tab => tab.classList.remove('active'));
        this.tabContents.forEach(content => content.classList.remove('active'));

        const selectedTab = document.querySelector(`.tab-btn[data-tab="${tabId}"]`);
        const selectedContent = document.getElementById(`${tabId}Tab`);

        if (selectedTab && selectedContent) {
            selectedTab.classList.add('active');
            selectedContent.classList.add('active');
            this.currentTab = tabId;
        }
    }
}


class StandardFilterManager {
    constructor(gender, genderCode) {
        this.gender = gender;
        this.genderCode = genderCode;
        
        // Elementi del form
        this.form = document.getElementById(`${gender}Form`);
        this.categorySelect = document.getElementById(`${gender}CategorySelect`);
        this.disciplineSelect = document.getElementById(`${gender}DisciplineSelect`);
        this.yearSelect = document.getElementById(`${gender}YearSelect`);
        this.limitSelect = document.getElementById(`${gender}LimitSelect`);
        this.windCheckbox = document.getElementById(`${gender}WindCheckbox`);
        this.allResultsToggle = document.getElementById(`${gender}AllResults`);

        this.initializeEventListeners();
        this.initializeFromUrl();
    }

    initializeEventListeners() {
        this.categorySelect.addEventListener('change', () => {
            this.updateDisciplineSelect();
        });

        this.disciplineSelect.addEventListener('change', () => {
            this.updateWindCheckboxVisibility();
        });

        this.form.addEventListener('submit', (e) => {
            e.preventDefault();
            this.submitFilters();
        });
    }

    initializeFromUrl() {
        const urlParams = new URLSearchParams(window.location.search);
        
        // Imposta i valori dei filtri dall'URL se presenti
        if (urlParams.get('category')) {
            this.categorySelect.value = urlParams.get('category');
            this.updateDisciplineSelect().then(() => {
                if (urlParams.get('discipline')) {
                    this.disciplineSelect.value = urlParams.get('discipline');
                    this.updateWindCheckboxVisibility();
                }
            });
        }
        
        if (urlParams.get('year')) this.yearSelect.value = urlParams.get('year');
        if (urlParams.get('limit')) this.limitSelect.value = urlParams.get('limit');
        if (urlParams.get('allResults')) this.allResultsToggle.checked = true;
    }

    async updateDisciplineSelect() {
        const category = this.categorySelect.value;
        
        if (!category) {
            this.disciplineSelect.disabled = true;
            this.disciplineSelect.innerHTML = '<option value="">Seleziona disciplina</option>';
            return;
        }

        try {
            const response = await fetch(`/api/disciplines/${category}/${this.genderCode}`);
            if (!response.ok) throw new Error('Network response was not ok');
            
            const disciplines = await response.json();

            this.disciplineSelect.innerHTML = '<option value="">Seleziona disciplina</option>';
            disciplines.forEach(d => {
                const option = document.createElement('option');
                option.value = d.disciplina;
                option.textContent = d.disciplina;
                option.dataset.hasWind = d.vento === 'sì' ? 'true' : 'false';
                this.disciplineSelect.appendChild(option);
            });

            this.disciplineSelect.disabled = false;
        } catch (error) {
            console.error('Error loading disciplines:', error);
            this.disciplineSelect.innerHTML = '<option value="">Errore caricamento discipline</option>';
            this.disciplineSelect.disabled = true;
        }
    }

    updateWindCheckboxVisibility() {
        const selectedOption = this.disciplineSelect.options[this.disciplineSelect.selectedIndex];
        const hasWind = selectedOption && selectedOption.dataset.hasWind === 'true';
        this.windCheckbox.style.display = hasWind ? 'block' : 'none';
    }

    submitFilters() {
        const formData = new FormData(this.form);
        const urlParams = new URLSearchParams();
        
        // Aggiungi il tab corrente
        urlParams.set('tab', this.gender);

        // Aggiungi tutti i parametri del form che hanno un valore
        for (const [key, value] of formData.entries()) {
            if (value) urlParams.set(key, value);
        }

        // Reindirizza alla nuova URL
        window.location.href = `${window.location.pathname}?${urlParams.toString()}`;
    }
}


class AdvancedFilterManager {
    constructor() {
        // Gestisci il form dei filtri avanzati esistente
        const form = document.querySelector('#advancedTab form');
        if (form) {
            form.addEventListener('submit', (e) => {
                e.preventDefault();
                this.submitAdvancedFilters(form);
            });
        }
    }

    submitAdvancedFilters(form) {
        const formData = new FormData(form);
        const urlParams = new URLSearchParams();
        
        for (const [key, value] of formData.entries()) {
            if (value) urlParams.set(key, value);
        }

        urlParams.set('tab', 'advanced');
        window.location.href = `${window.location.pathname}?${urlParams.toString()}`;
    }
}


// Inizializza il gestore dei tab quando il documento è caricato
document.addEventListener('DOMContentLoaded', () => {
    const tabFilterManager = new TabFilterManager();
});


function loadStats(discipline, queryParams) {
    // Create a copy of queryParams to avoid modifying the original
    const params = new URLSearchParams(queryParams);
    
    // Ensure the category parameter is properly encoded
    const category = params.get('category');
    if (category) {
        params.set('category', encodeURIComponent(category));
    }

    // Add legal_wind parameter if checkbox exists
    const legalWindCheckbox = document.querySelector('input[name="legal_wind"]');
    if (legalWindCheckbox) {
        params.set('legal_wind', legalWindCheckbox.checked);
    }

    // Add year parameter if it exists
    const yearSelect = document.querySelector('select[name="year"]');
    if (yearSelect && yearSelect.value) {
        params.set('year', yearSelect.value);
    }

    fetch(`/api/stats/${encodeURIComponent(discipline)}?${params.toString()}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            const classificaType = document.getElementById('disciplineInfo').dataset.classificaType;
            const isBestTime = classificaType === 'tempo';
            const statsHtml = `
                <div class="stat-box">
                    <h3>Migliore</h3>
                    <p>${formatTime(data.best, classificaType)}</p>
                </div>
                <div class="stat-box">
                    <h3>Media</h3>
                    <p>${formatTime(data.average, classificaType)}</p>
                </div>
                <div class="stat-box">
                    <h3>Atleti totali</h3>
                    <p>${data.athletes}</p>
                </div>
                <div class="stat-box">
                    <h3>Risultati totali</h3>
                    <p>${data.performances}</p>
                </div>
            `;
            document.getElementById('statsContainer').innerHTML = statsHtml;
        })
        .catch(error => {
            console.error('Error fetching stats:', error);
            document.getElementById('statsContainer').innerHTML = '<p>Error loading statistics</p>';
        });
}


function formatTime(seconds, classificaType) {
    if (!seconds) return '-';
    seconds = parseFloat(seconds);
    if (classificaType === 'tempo' && seconds >= 60) {
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = (seconds % 60).toFixed(2).padStart(5, '0');
        return `${minutes}:${remainingSeconds}`;
    }
    return seconds.toFixed(2);
}


// To jump to a specific page of the rankings
function goToPage() {
    const input = document.getElementById('pageInput');
    const pagination = document.querySelector('.pagination');
    const totalPages = parseInt(pagination.dataset.totalPages);
    
    const page = parseInt(input.value);
    if (page && page >= 1 && page <= totalPages) {
        // Get current URL parameters
        const urlParams = new URLSearchParams(window.location.search);
        // Update the page parameter
        urlParams.set('page', page);
        // Construct new URL
        window.location.href = `${window.location.pathname}?${urlParams.toString()}`;
    }
}


// Add event listener when the document is loaded
document.addEventListener('DOMContentLoaded', function() {
    const pageInput = document.getElementById('pageInput');
    if (pageInput) {
        pageInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                goToPage();
            }
        });
    }
});
