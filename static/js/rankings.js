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

            // Preserve relevant parameters when switching tabs
            const urlParams = new URLSearchParams(window.location.search);
            urlParams.set('tab', tabId);
            
            // Reset page to 1 when switching tabs
            urlParams.set('page', '1');
            
            // Update URL without reloading
            window.history.pushState({}, '', `${window.location.pathname}?${urlParams.toString()}`);
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
        
        // Se non ci sono parametri nell'URL, carica le discipline per la categoria di default
        const urlParams = new URLSearchParams(window.location.search);
        if (!urlParams.get('category') && !urlParams.get('discipline')) {
            this.updateDisciplineSelect();
        }

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
    
    // Imposta categoria e carica le discipline
    if (urlParams.get('category')) {
        this.categorySelect.value = urlParams.get('category');
        this.updateDisciplineSelect().then(() => {
            // Dopo che le discipline sono state caricate, imposta la disciplina selezionata
            const discipline = urlParams.get('discipline');
            const ambiente = urlParams.get('ambiente');

            if (discipline && ambiente) {
                // Cerca l'opzione corrispondente
                const options = Array.from(this.disciplineSelect.options);
                const targetOption = options.find(option => {
                    if (!option.value) return false;
                    const data = JSON.parse(option.value);
                    return data.disciplina === discipline && data.ambiente === ambiente;
                });
                
                if (targetOption) {
                    this.disciplineSelect.value = targetOption.value;
                    this.updateWindCheckboxVisibility();
                }
            }
        });
    }
    
    // Imposta gli altri valori
    if (urlParams.get('year')) this.yearSelect.value = urlParams.get('year');
    if (urlParams.get('limit')) this.limitSelect.value = urlParams.get('limit');
    if (urlParams.get('allResults')) this.allResultsToggle.checked = true;
    
    // Imposta il checkbox del vento se presente
    const legalWind = urlParams.get('legal_wind');
    if (legalWind !== null && this.windCheckbox) {
        const windInput = this.windCheckbox.querySelector('input');
        if (windInput) {
            windInput.checked = legalWind.toLowerCase() === 'true';
        }
    }
    }

    async updateDisciplineSelect() {
        const category = this.categorySelect.value;

        if (!category) {
            this.disciplineSelect.disabled = true;
            return;
        }

        try {
            const response = await fetch(`/api/disciplines/${category}/${this.genderCode}`);
            if (!response.ok) throw new Error('Network response was not ok');

            const disciplines = await response.json();

            // Rimuovi tutte le opzioni esistenti
            this.disciplineSelect.innerHTML = '';

            disciplines.forEach(d => {
                if (d.ambiente === 'I-P') {
                    // Crea due opzioni per Indoor e Outdoor
                    const optionOutdoor = document.createElement('option');
                    optionOutdoor.value = JSON.stringify({
                        disciplina: d.disciplina,
                        ambiente: 'P'
                    });
                    optionOutdoor.textContent = d.disciplina;
                    this.disciplineSelect.appendChild(optionOutdoor);

                    const optionIndoor = document.createElement('option');
                    optionIndoor.value = JSON.stringify({
                        disciplina: d.disciplina,
                        ambiente: 'I'
                    });
                    optionIndoor.textContent = d.disciplina + ' (indoor)';
                    this.disciplineSelect.appendChild(optionIndoor);
                } else {
                    // Ambiente singolo (I, P o IP)
                    const option = document.createElement('option');
                    option.value = JSON.stringify({
                        disciplina: d.disciplina,
                        ambiente: d.ambiente
                    });
                    option.textContent = d.disciplina + (d.ambiente === 'I' ? ' (indoor)' : '');
                    this.disciplineSelect.appendChild(option);
                }
            });

            this.disciplineSelect.disabled = false;

            // Se non c'è una disciplina selezionata, seleziona i 100m
            if (!this.disciplineSelect.value) {
                // Cerca l'opzione dei 100m outdoor
                const options = Array.from(this.disciplineSelect.options);
                const hundred = options.find(option => {
                    if (!option.value) return false;
                    const data = JSON.parse(option.value);
                    return data.disciplina === '100m' && data.ambiente === 'P';
                });

                if (hundred) {
                    this.disciplineSelect.value = hundred.value;
                    this.updateWindCheckboxVisibility();
                    // Aggiungi questa riga per forzare il submit dei filtri
                    this.submitFilters();
                }
            }
        } catch (error) {
            console.error('Error loading disciplines:', error);
            this.disciplineSelect.disabled = true;
        }
    }

    async updateWindCheckboxVisibility() {
        const selectedValue = this.disciplineSelect.value;
        if (!selectedValue) {
            this.windCheckbox.style.display = 'none';
            return;
        }

        try {
            const { disciplina, ambiente } = JSON.parse(selectedValue);

            // Non mostrare il checkbox per gare indoor
            if (ambiente === 'I') {
                this.windCheckbox.style.display = 'none';
                return;
            }

            // Controlla se la disciplina ha il vento
            const response = await fetch(`/api/discipline_info/${disciplina}`);
            const info = await response.json();

            this.windCheckbox.style.display = info.vento === 'sì' ? 'block' : 'none';
        } catch (error) {
            console.error('Error checking wind:', error);
            this.windCheckbox.style.display = 'none';
        }
    }

    submitFilters() {
        const formData = new FormData(this.form);
        const urlParams = new URLSearchParams();

        // Aggiungi il tab corrente
        urlParams.set('tab', this.gender);

        // Gestisci la disciplina selezionata
        const disciplineValue = formData.get('discipline');
        if (disciplineValue) {
            const { disciplina, ambiente } = JSON.parse(disciplineValue);
            urlParams.set('discipline', disciplina);
            urlParams.set('ambiente', ambiente);
        }

        // Gestisci il checkbox del vento
        if (this.windCheckbox.style.display !== 'none') {
            const windInput = this.windCheckbox.querySelector('input');
            if (windInput) {
                urlParams.set('legal_wind', windInput.checked);
            }
        }

        // Aggiungi gli altri parametri
        for (const [key, value] of formData.entries()) {
            if (key !== 'discipline' && key !== 'legal_wind' && value) {
                urlParams.set(key, value);
            }
        }

        // Reindirizza alla nuova URL
        window.location.href = `${window.location.pathname}?${urlParams.toString()}`;
    }
}


class AdvancedFilterManager {
    constructor() {
        this.form = document.querySelector('#advancedForm');
        this.disciplineSelect = document.getElementById('advancedDisciplineSelect');
        this.windCheckbox = this.form.querySelector('.wind-checkbox');
        this.ambienteSelect = this.form.querySelector('select[name="ambiente"]');

        this.initializeEventListeners();
        this.loadDisciplines();
        this.initializeFromUrl();
    }

    initializeEventListeners() {
        this.form.addEventListener('submit', (e) => {
            e.preventDefault();
            this.submitFilters();
        });

        // Update wind checkbox when discipline or ambiente changes
        [this.disciplineSelect, this.ambienteSelect].forEach(select => {
            select?.addEventListener('change', () => this.updateWindCheckboxVisibility());
        });
    }

    async updateWindCheckboxVisibility() {
        // Always hide for indoor events
        if (this.ambienteSelect.value === 'I') {
            this.windCheckbox.style.display = 'none';
            return;
        }

        // Hide if no discipline selected
        if (!this.disciplineSelect.value) {
            this.windCheckbox.style.display = 'none';
            return;
        }

        try {
            const response = await fetch(`/api/discipline_info/${this.disciplineSelect.value}`);
            const info = await response.json();
            this.windCheckbox.style.display = info.vento === 'sì' ? 'block' : 'none';
        } catch (error) {
            console.error('Error checking wind:', error);
            this.windCheckbox.style.display = 'none';
        }
    }

    async loadDisciplines() {
        try {
            const response = await fetch('/api/disciplines/all');
            const disciplines = await response.json();

            this.disciplineSelect.innerHTML = '<option value="">Disciplina</option>';
            Object.entries(disciplines).forEach(([disc]) => {
                const option = document.createElement('option');
                option.value = disc;
                option.textContent = disc;
                this.disciplineSelect.appendChild(option);
            });

            // Set initial values from URL
            const urlParams = new URLSearchParams(window.location.search);
            if (urlParams.get('discipline')) {
                this.disciplineSelect.value = urlParams.get('discipline');
                await this.updateWindCheckboxVisibility();
            }
        } catch (error) {
            console.error('Error loading disciplines:', error);
            this.disciplineSelect.innerHTML = '<option value="">Error loading disciplines</option>';
        }
    }

    initializeFromUrl() {
        const urlParams = new URLSearchParams(window.location.search);
        for (const [key, value] of urlParams.entries()) {
            const element = this.form.elements[key];
            if (element) {
                if (element.type === 'checkbox') {
                    element.checked = value.toLowerCase() === 'true';
                } else {
                    element.value = value;
                }
            }
        }
        this.updateWindCheckboxVisibility();
    }

    submitFilters() {
        const formData = new FormData(this.form);
        const urlParams = new URLSearchParams();

        // Set tab first
        urlParams.set('tab', 'advanced');

        // Handle all form fields
        for (const [key, value] of formData.entries()) {
            // Skip empty values except checkboxes
            if (!value && key !== 'legal_wind') continue;

            
            // Special handling for wind checkbox
            if (key === 'legal_wind') {
                urlParams.set(key, 'true');
            } else {
                urlParams.set(key, value);
            }
        }

        // If wind checkbox is visible but unchecked, explicitly set it to false
        const windInput = this.form.querySelector('input[name="legal_wind"]');
        if (windInput && this.windCheckbox.style.display !== 'none' && !windInput.checked) {
            urlParams.set('legal_wind', 'false');
        }

        // Redirect to new URL
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


function goToPage() {
    const input = document.getElementById('pageInput');
    const pagination = document.querySelector('.pagination');
    const totalPages = parseInt(pagination.dataset.totalPages);
    const currentTab = pagination.dataset.currentTab;
    
    const page = parseInt(input.value);
    if (page && page >= 1 && page <= totalPages) {
        // Get current URL parameters
        const urlParams = new URLSearchParams(window.location.search);
        
        // Update page parameter
        urlParams.set('page', page);
        
        // Ensure tab parameter is set
        if (!urlParams.has('tab')) {
            urlParams.set('tab', currentTab);
        }
        
        // Construct new URL preserving all parameters
        window.location.href = `${window.location.pathname}?${urlParams.toString()}`;
    }
}

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
