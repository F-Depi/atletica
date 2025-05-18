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

        // Se non ci sono parametri nell'URL, forza il caricamento dei valori di default
        if (!urlParams.toString()) {
            this.activateTab('men');
            this.menFilters.forceLoadDisciplines();
        } else {
            this.activateTab(initialTab);
        }
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

            const urlParams = new URLSearchParams(window.location.search);
            const previousTab = urlParams.get('tab');

            // Gestisci il cambio di tab
            if (tabId !== previousTab) {
                // Preserva i parametri quando si passa tra tab standard
                if (tabId !== 'advanced' && previousTab && previousTab !== 'advanced') {
                    // Mantieni tutti i parametri esistenti, cambia solo il tab e il gender
                    urlParams.set('tab', tabId);
                    
                    // Aggiorna i form della nuova tab con i valori correnti
                    const targetFilter = tabId === 'men' ? this.menFilters : this.womenFilters;
                    
                    // Imposta i valori nei select
                    if (urlParams.get('category')) {
                        targetFilter.categorySelect.value = urlParams.get('category');
                    }
                    if (urlParams.get('year')) {
                        targetFilter.yearSelect.value = urlParams.get('year');
                    }
                    if (urlParams.get('limit')) {
                        targetFilter.limitSelect.value = urlParams.get('limit');
                    }
                    if (urlParams.get('allResults')) {
                        targetFilter.allResultsToggle.checked = urlParams.get('allResults').toLowerCase() === 'true';
                    }

                    // Forza il caricamento delle discipline mantenendo la disciplina selezionata
                    const currentDiscipline = urlParams.get('discipline');
                    const currentAmbiente = urlParams.get('ambiente');
                    if (currentDiscipline && currentAmbiente) {
                        targetFilter.updateDisciplineSelect().then(() => {
                            // Cerca l'opzione corrispondente
                            const options = Array.from(targetFilter.disciplineSelect.options);
                            const targetOption = options.find(option => {
                                if (!option.value) return false;
                                const data = JSON.parse(option.value);
                                return data.disciplina === currentDiscipline && 
                                       data.ambiente === currentAmbiente;
                            });
                            
                            if (targetOption) {
                                targetFilter.disciplineSelect.value = targetOption.value;
                                targetFilter.updateWindCheckboxVisibility();
                            }
                        });
                    }
                } 
                // Gestione passaggio da/verso tab avanzata
                else {
                    urlParams.set('tab', tabId);
                    
                    if (tabId !== 'advanced') {
                        // Se si passa dalla tab avanzata a una standard
                        urlParams.set('category', 'ASS');
                        urlParams.delete('page');

                        // Forza il caricamento delle discipline
                        if (tabId === 'men') {
                            this.menFilters.forceLoadDisciplines();
                        } else if (tabId === 'women') {
                            this.womenFilters.forceLoadDisciplines();
                        }
                    }
                }
            }

            // Aggiorna l'URL
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
        this.regionSelect = document.getElementById(`${gender}RegionSelect`);
        this.provinceClubSelect = document.getElementById(`${gender}ProvinceClubSelect`);
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
        
        // Store to preserve across category change
        this.currentDisciplineValue = null;
    }

    initializeEventListeners() {
        this.categorySelect.addEventListener('change', () => {
            // Store current discipline selection before updating
            this.currentDisciplineValue = this.disciplineSelect.value ? JSON.parse(this.disciplineSelect.value) : null;
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

        if (urlParams.get('provincia_societa') && this.provinceClubSelect) {
            this.provinceClubSelect.value = urlParams.get('provincia_societa');
        }


        // Imposta gli altri valori
        if (urlParams.get('year')) this.yearSelect.value = urlParams.get('year');
        if (urlParams.get('regione')) this.regionSelect.value = urlParams.get('regione');
        if (this.provinceClubSelect && this.provinceClubSelect.value) {
            urlParams.set('provincia_societa', this.provinceClubSelect.value);
        }

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


    forceLoadDisciplines() {
        // Assicurati che la categoria sia impostata su Assoluti
        this.categorySelect.value = 'ASS';

        // Forza il caricamento delle discipline
        return this.updateDisciplineSelect().then(() => {
            // Dopo il caricamento, seleziona i 100m se non c'è una disciplina selezionata
            if (!this.disciplineSelect.value) {
                const options = Array.from(this.disciplineSelect.options);
                const hundred = options.find(option => {
                    if (!option.value) return false;
                    const data = JSON.parse(option.value);
                    return data.disciplina === '100m' && data.ambiente === 'P';
                });

                if (hundred) {
                    this.disciplineSelect.value = hundred.value;
                    this.updateWindCheckboxVisibility();
                    // Sottometti automaticamente i filtri
                    this.submitFilters();
                }
            }
        }).catch(error => {
            console.error('Error in forceLoadDisciplines:', error);
        });
    }

    async updateDisciplineSelect() {
        const category = this.categorySelect.value || 'ASS';

        try {
            const response = await fetch(`/api/disciplines/${category}/${this.genderCode}`);
            if (!response.ok) throw new Error('Network response was not ok');

            const disciplines = await response.json();

            // Rimuovi tutte le opzioni esistenti
            this.disciplineSelect.innerHTML = '<option value="">Disciplina</option>';

            disciplines.forEach(d => {
                if (d.ambiente === 'I-P') {
                    // Crea due opzioni per Indoor e Outdoor
                    const optionOutdoor = document.createElement('option');
                    optionOutdoor.value = JSON.stringify({
                        disciplina: d.disciplina,
                        ambiente: 'P'
                    });
                    optionOutdoor.textContent = d.disciplina.replace(/_/g, ' ').replace(/^\w/, c => c.toUpperCase());
                    this.disciplineSelect.appendChild(optionOutdoor);

                    const optionIndoor = document.createElement('option');
                    optionIndoor.value = JSON.stringify({
                        disciplina: d.disciplina,
                        ambiente: 'I'
                    });
                    optionIndoor.textContent = d.disciplina.replace(/_/g, ' ').replace(/^\w/, c => c.toUpperCase()) + ' (indoor)';
                    this.disciplineSelect.appendChild(optionIndoor);
                } else {
                    const option = document.createElement('option');
                    option.value = JSON.stringify({
                        disciplina: d.disciplina,
                        ambiente: d.ambiente
                    });
                    option.textContent = d.disciplina.replace(/_/g, ' ').replace(/^\w/, c => c.toUpperCase()) + (d.ambiente === 'I' ? ' (indoor)' : '');
                    this.disciplineSelect.appendChild(option);
                }
            });

            this.disciplineSelect.disabled = false;
            
            // Try to restore previous discipline selection if it exists in the new category
            if (this.currentDisciplineValue) {
                // Look for matching discipline in the new options
                const options = Array.from(this.disciplineSelect.options);
                const matchingOption = options.find(option => {
                    if (!option.value) return false;
                    const optionData = JSON.parse(option.value);
                    return optionData.disciplina === this.currentDisciplineValue.disciplina && 
                           optionData.ambiente === this.currentDisciplineValue.ambiente;
                });
                
                if (matchingOption) {
                    this.disciplineSelect.value = matchingOption.value;
                    // Also update the wind checkbox visibility for the restored selection
                    this.updateWindCheckboxVisibility();
                }
            }
            
            return disciplines;

        } catch (error) {
            console.error('Error loading disciplines:', error);
            this.disciplineSelect.disabled = true;
            throw error;
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

        this.disciplinesLoaded = false;

        // Carica le discipline e inizializza
        this.loadDisciplines().then(() => {
            this.initializeEventListeners();
            this.initializeFromUrl();
            // Forza l'aggiornamento della visibilità del checkbox dopo l'inizializzazione
            this.updateWindCheckboxVisibility();
        }).catch(error => {
            console.error('Error in initial discipline loading:', error);
        });
    }

    initializeEventListeners() {
        this.form.addEventListener('submit', (e) => {
            e.preventDefault();
            this.submitFilters();
        });

        // Aggiungi event listener per il cambio di disciplina
        this.disciplineSelect.addEventListener('change', () => {
            this.updateWindCheckboxVisibility();
        });

        // Aggiungi event listener per il cambio di ambiente
        this.ambienteSelect.addEventListener('change', () => {
            this.updateWindCheckboxVisibility();
        });
    }

    async updateWindCheckboxVisibility() {
        // Assicurati che ci siano sia una disciplina che un ambiente selezionati
        const selectedDiscipline = this.disciplineSelect.value;
        const selectedAmbiente = this.ambienteSelect.value;

        if (!selectedDiscipline || !selectedAmbiente) {
            this.windCheckbox.style.display = 'none';
            return;
        }

        // Nascondi sempre per eventi indoor
        if (selectedAmbiente === 'I') {
            this.windCheckbox.style.display = 'none';
            return;
        }

        try {
            const response = await fetch(`/api/discipline_info/${selectedDiscipline}`);
            if (!response.ok) throw new Error('Network response was not ok');

            const info = await response.json();
            console.log('Discipline info:', info); // Debug log
            this.windCheckbox.style.display = info.vento === 'sì' ? 'block' : 'none';
        } catch (error) {
            console.error('Error checking wind:', error);
            this.windCheckbox.style.display = 'none';
        }
    }

    initializeFromUrl() {
        if (!this.disciplinesLoaded) {
            console.warn('Attempting to initialize from URL before disciplines are loaded');
            return;
        }

        const urlParams = new URLSearchParams(window.location.search);

        // Imposta i valori dei campi form
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
    }

    async loadDisciplines() {
    if (this.disciplinesLoaded) return; // Evita caricamenti multipli

    try {
        const response = await fetch('/api/disciplines/all');
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }

        const disciplines = await response.json();

        // Pulisci il select
        this.disciplineSelect.innerHTML = '<option value="">Disciplina</option>';

        // Aggiungi le discipline
        disciplines.forEach(disc => {
            const option = document.createElement('option');
            option.value = disc;
            option.textContent = disc.replace(/_/g, ' ').replace(/^\w/, c => c.toUpperCase());
            this.disciplineSelect.appendChild(option);
        });

        this.disciplinesLoaded = true;
        this.disciplineSelect.disabled = false;

    } catch (error) {
        console.error('Error loading disciplines:', error);
        this.disciplineSelect.innerHTML = '<option value="">Error loading disciplines</option>';
        this.disciplineSelect.disabled = true;
        throw error;
    }
}


    submitFilters() {
        if (!this.disciplinesLoaded) {
            console.warn('Attempting to submit before disciplines are loaded');
            return;
        }

        const formData = new FormData(this.form);
        const urlParams = new URLSearchParams();

        // Set tab first
        urlParams.set('tab', 'advanced');

        // Handle all form fields
        for (const [key, value] of formData.entries()) {
            if (!value && key !== 'legal_wind') continue;

            if (key === 'legal_wind') {
                urlParams.set(key, 'true');
            } else {
                urlParams.set(key, value);
            }
        }

        // Handle wind checkbox
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


//function loadStats(discipline, queryParams) {
//    // Create a copy of queryParams to avoid modifying the original
//    const params = new URLSearchParams(queryParams);
//
//    // Ensure the category parameter is properly encoded
//    const category = params.get('category');
//    if (category) {
//        params.set('category', encodeURIComponent(category));
//    }
//
//    // Add legal_wind parameter if checkbox exists
//    const legalWindCheckbox = document.querySelector('input[name="legal_wind"]');
//    if (legalWindCheckbox) {
//        params.set('legal_wind', legalWindCheckbox.checked);
//    }
//
//    // Add year parameter if it exists
//    const yearSelect = document.querySelector('select[name="year"]');
//    if (yearSelect && yearSelect.value) {
//        params.set('year', yearSelect.value);
//    }
//
//    fetch(`/api/stats/${encodeURIComponent(discipline)}?${params.toString()}`)
//        .then(response => {
//            if (!response.ok) {
//                throw new Error('Network response was not ok');
//            }
//            return response.json();
//        })
//        .then(data => {
//            const classificaType = document.getElementById('disciplineInfo').dataset.classificaType;
//            const isBestTime = classificaType === 'tempo';
//            const statsHtml = `
//                <div class="stat-box">
//                <h3>Migliore</h3>
//                <p>${formatTime(data.best, classificaType)}</p>
//                </div>
//                <div class="stat-box">
//                <h3>Media</h3>
//                <p>${formatTime(data.average, classificaType)}</p>
//                </div>
//                <div class="stat-box">
//                <h3>Atleti totali</h3>
//                <p>${data.athletes}</p>
//                </div>
//                <div class="stat-box">
//                <h3>Risultati totali</h3>
//                <p>${data.performances}</p>
//                </div>
//                `;
//            document.getElementById('statsContainer').innerHTML = statsHtml;
//        })
//        .catch(error => {
//            console.error('Error fetching stats:', error);
//            document.getElementById('statsContainer').innerHTML = '<p>Error loading statistics</p>';
//        });
//}


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


// Apertura e gestione del Box con link atleta, società e segnalazione errore
document.addEventListener('DOMContentLoaded', function() {
    const rows = document.querySelectorAll('.result-row');
    const detailBox = document.getElementById('detailBox');
    const closeBtn = document.querySelector('.close-btn');
    
    // Elementi per la segnalazione errori
    const btnMostraSegnala = document.getElementById('mostraSegnalaErrore');
    const formSegnalazione = document.getElementById('formSegnalazione');
    const testoSegnalazione = document.getElementById('testoSegnalazione');
    const btnAnnullaSegnalazione = document.getElementById('annullaSegnalazione');
    const btnInviaSegnalazione = document.getElementById('inviaSegnalazione');
    const messaggioInvio = document.getElementById('messaggioInvio');
    
    let currentRowData = null;
    let currentAtleta = '';
    let currentPrestazione = '';
    let csrfToken = '';
    
    // Ottieni il token CSRF all'avvio
    fetchCsrfToken();
    
    function fetchCsrfToken() {
        fetch('/get-csrf-token')
            .then(response => response.json())
            .then(data => {
                csrfToken = data.csrf_token;
                console.log('CSRF token ottenuto');
            })
            .catch(error => {
                console.error('Errore nel recupero del CSRF token:', error);
            });
    }
    
    if (!detailBox || !closeBtn) {
        console.error('Detail box o close button non trovati!');
        return;
    }
    
    // Crea un overlay per facilitare la chiusura al tocco
    const overlay = document.createElement('div');
    overlay.className = 'detail-overlay';
    document.body.appendChild(overlay);
    
    function showDetailBox() {
        detailBox.style.display = 'block';
        overlay.style.display = 'block';
        // Nascondi il form di segnalazione quando si apre il box
        formSegnalazione.style.display = 'none';
        testoSegnalazione.value = '';
        messaggioInvio.textContent = '';
        messaggioInvio.className = 'messaggio-invio';
    }
    
    function hideDetailBox() {
        detailBox.style.display = 'none';
        overlay.style.display = 'none';
    }
    
    rows.forEach(row => {
        row.addEventListener('click', function() {
            const atleta = this.getAttribute('data-atleta');
            const linkAtleta = this.getAttribute('data-link-atleta');
            const societa = this.getAttribute('data-societa');
            const linkSocieta = this.getAttribute('data-link-societa');
            const prestazione = this.getAttribute('data-prestazione');
            const position = this.getAttribute('data-position');
            
            // Memorizza tutti i dati della riga per la segnalazione
            currentRowData = {
                atleta: atleta,
                linkAtleta: linkAtleta,
                societa: societa,
                linkSocieta: linkSocieta,
                prestazione: prestazione,
                position: position
            };
            
            // Memorizza i dati principali per riferimento immediato
            currentAtleta = atleta;
            currentPrestazione = prestazione;
            
            // Popola il box con i dati
            document.getElementById('detailAtleta').textContent = `${atleta} - ${prestazione} (${position}°)`;
            document.getElementById('linkAtleta').href = linkAtleta;

            const clubCode = linkSocieta.slice(-5);
            document.getElementById('linkSocieta').href = linkSocieta;
            document.getElementById('linkSocieta').textContent = `Pagina società (${clubCode})`;

            
            // Mostra il box
            showDetailBox();
        });
    });
    
    // Gestione del form di segnalazione
    btnMostraSegnala.addEventListener('click', function() {
        formSegnalazione.style.display = 'block';
        // Assicurati di avere un token CSRF aggiornato quando mostri il form
        if (!csrfToken) {
            fetchCsrfToken();
        }
    });
    
    btnAnnullaSegnalazione.addEventListener('click', function() {
        formSegnalazione.style.display = 'none';
        testoSegnalazione.value = '';
        messaggioInvio.textContent = '';
        messaggioInvio.className = 'messaggio-invio';
    });
    
    // Controllo input per abilitare/disabilitare il bottone di invio
    testoSegnalazione.addEventListener('input', function() {
        btnInviaSegnalazione.disabled = this.value.trim().length === 0;
    });
    
    // Invio della segnalazione
    btnInviaSegnalazione.addEventListener('click', function() {
        const testoErrore = testoSegnalazione.value.trim();
        if (!testoErrore) return;
        
        if (!csrfToken) {
            messaggioInvio.textContent = 'Errore di sicurezza, ricarica la pagina.';
            messaggioInvio.className = 'messaggio-invio error';
            return;
        }
        
        // Dati da inviare con informazioni aggiuntive
        const datiSegnalazione = {
            atleta: currentAtleta,
            prestazione: currentPrestazione,
            descrizione: testoErrore,
            rowData: currentRowData,            // Dati completi della riga
            pageUrl: window.location.href,      // URL completo della pagina corrente
            queryParams: window.location.search  // Parametri della query
        };

        // Mostra indicatore di caricamento
        messaggioInvio.textContent = 'Invio in corso...';
        messaggioInvio.className = 'messaggio-invio';

        // Utilizza fetch per inviare i dati
        fetch('/api/segnala-errore', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-TOKEN': csrfToken
            },
            body: JSON.stringify(datiSegnalazione),
        })
        .then(response => {
            // First check if response is ok
            if (!response.ok) {
                // For any error response, try to parse the JSON first
                return response.json().then(errorData => {
                    // Throw the error data for the catch block
                    throw errorData;
                });
            }
            return response.json();
        })
        .then(data => {
            // Mostra messaggio di successo
            messaggioInvio.textContent = 'Segnalazione inviata con successo!';
            messaggioInvio.className = 'messaggio-invio success';
            
            // Refresha il token CSRF dopo l'uso
            fetchCsrfToken();
            
            // Pulisci il form e nascondi dopo 2 secondi
            setTimeout(() => {
                formSegnalazione.style.display = 'none';
                testoSegnalazione.value = '';
                messaggioInvio.textContent = '';
                messaggioInvio.className = 'messaggio-invio';
            }, 2000);
        })
        .catch(error => {
            console.error('Errore:', error);

            // Check if the error has specific information from the server
            if (error && error.error) {
                // Display the specific error message from the server
                messaggioInvio.textContent = error.error;
            } else {
                // Fall back to generic error
                messaggioInvio.textContent = 'Errore nell\'invio. Riprova.';
            }

            messaggioInvio.className = 'messaggio-invio error';

            // Refresha il token CSRF in caso di errore
            fetchCsrfToken();
        });
    });
    
    // Chiudi il box quando si clicca sulla X
    closeBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        hideDetailBox();
    });
    
    // Chiudi il box quando si clicca sull'overlay
    overlay.addEventListener('click', function() {
        hideDetailBox();
    });
    
    // Previeni la chiusura quando si clicca sul box stesso
    detailBox.addEventListener('click', function(e) {
        e.stopPropagation();
    });
    
    // Supporto per chiusura con tasto ESC
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && detailBox.style.display === 'block') {
            hideDetailBox();
        }
    });
    
    console.log('Script di dettaglio risultati inizializzato');
});
