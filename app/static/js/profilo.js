// Toggle between sections
document.addEventListener('DOMContentLoaded', function() {
    const pbsBtn = document.getElementById('show-pbs-btn');
    const recentBtn = document.getElementById('show-recent-btn');
    const pbsSection = document.getElementById('pbs-section');
    const recentSection = document.getElementById('recent-section');

    pbsBtn.addEventListener('click', function() {
        pbsBtn.classList.add('active');
        recentBtn.classList.remove('active');
        pbsSection.classList.add('active');
        recentSection.classList.remove('active');
    });

    recentBtn.addEventListener('click', function() {
        recentBtn.classList.add('active');
        pbsBtn.classList.remove('active');
        recentSection.classList.add('active');
        pbsSection.classList.remove('active');
    });

    // Initialize sorting on all sortable tables
    initializeSortableTables();
});

// Toggle individual PB details
function toggleResults(element) {
    const container = element.closest('.pb-row');
    const detailsContainer = container.querySelector('.pb-details-container');
    const toggleIcon = container.querySelector('.toggle-icon');

    if (detailsContainer.classList.contains('active')) {
        detailsContainer.classList.remove('active');
        toggleIcon.classList.remove('expanded');
    } else {
        detailsContainer.classList.add('active');
        toggleIcon.classList.add('expanded');
    }
}

// Table sorting functionality
function initializeSortableTables() {
    const sortableTables = document.querySelectorAll('table.sortable');

    sortableTables.forEach(table => {
        const headers = table.querySelectorAll('th.sortable-header');

        headers.forEach(header => {
            header.addEventListener('click', function() {
                const sortDirection = this.classList.contains('sort-asc') ? 'desc' : 'asc';

                // Reset all headers
                headers.forEach(h => {
                    h.classList.remove('sort-asc', 'sort-desc');
                    h.querySelector('.sort-icon').textContent = '';
                });

                // Set current header
                this.classList.add('sort-' + sortDirection);
                this.querySelector('.sort-icon').textContent = sortDirection === 'asc' ? '▲' : '▼';

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

    // Different sorting methods based on column type
    let compareFunc;
    switch(sortType) {
        case 'result':
            // Sort by raw result value (numerical for times, distances)
            compareFunc = (a, b) => {
                const aVal = parseFloat(a.getAttribute('data-raw-result')) || 0;
                const bVal = parseFloat(b.getAttribute('data-raw-result')) || 0;
                console.log(`Comparing: ${aVal} vs ${bVal}`); 
                // For running events, lower is better (but stored as raw values that are comparable)
                return direction === 'asc' ? aVal - bVal : bVal - aVal;
            };
            break;

        case 'date':
            // Sort by date (numerical YYYYMMDD format)
            compareFunc = (a, b) => {
                const aVal = a.getAttribute('data-raw-date') || '00000000';
                const bVal = b.getAttribute('data-raw-date') || '00000000';

                return direction === 'asc' ? 
                    aVal.localeCompare(bVal) : 
                    bVal.localeCompare(aVal);
            };
            break;

        default:
            return; // If not a sortable column
    }

    // Sort rows
    rows.sort(compareFunc);

    // Re-append rows in new order
    rows.forEach(row => tbody.appendChild(row));
}

