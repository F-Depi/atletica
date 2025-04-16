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
                    <h3>${isBestTime ? 'Migliore' : 'Best'}</h3>
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

document.addEventListener('DOMContentLoaded', function() {
    const filterForm = document.getElementById('filterForm');
    const currentDiscipline = document.getElementById('disciplineInfo').dataset.discipline;

    // Function to just load stats without form submission
    function loadCurrentStats() {
        const formData = new FormData(filterForm);
        const queryParams = new URLSearchParams();
        
        for (let [key, value] of formData.entries()) {
            if (value && value.trim() !== '') {
                queryParams.set(key, value);
            }
        }

        const legalWindCheckbox = document.querySelector('input[name="legal_wind"]');
        if (legalWindCheckbox) {
            queryParams.set('legal_wind', legalWindCheckbox.checked);
        }

        const allResultsCheckbox = document.querySelector('input[name="allResults"]');
        if (allResultsCheckbox) {
            queryParams.set('allResults', allResultsCheckbox.checked);
        }

        loadStats(currentDiscipline, queryParams);
    }

    // Add change event listeners to individual filters
    const filters = filterForm.querySelectorAll('select, input[type="checkbox"]');
    filters.forEach(filter => {
        filter.addEventListener('change', loadCurrentStats);
    });

    // Handle form submission
    filterForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const formData = new FormData(filterForm);
        const currentUrl = new URL(window.location.href);
        
        currentUrl.search = '';
        for (let [key, value] of formData.entries()) {
            if (value && value.trim() !== '') {
                currentUrl.searchParams.set(key, value);
            }
        }

        const legalWindCheckbox = document.querySelector('input[name="legal_wind"]');
        if (legalWindCheckbox) {
            currentUrl.searchParams.set('legal_wind', legalWindCheckbox.checked);
        }

        const allResultsCheckbox = document.querySelector('input[name="allResults"]');
        if (allResultsCheckbox) {
            currentUrl.searchParams.set('allResults', allResultsCheckbox.checked);
        }

        currentUrl.searchParams.set('page', '1');
        window.location.href = currentUrl.toString();
    });

    // Load stats when page first loads
    loadCurrentStats();
});
