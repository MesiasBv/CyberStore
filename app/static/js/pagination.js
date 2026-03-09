// Script de paginación automática para todas las tablas
document.addEventListener('DOMContentLoaded', function() {
    function agregarPaginacionATabla(tableId, rowsPerPage = 10) {
        const table = document.getElementById(tableId);
        if (!table) return;
        
        const tbody = table.querySelector('tbody');
        if (!tbody) return;
        
        const rows = Array.from(tbody.querySelectorAll('tr'));
        const totalPages = Math.ceil(rows.length / rowsPerPage);
        
        if (totalPages <= 1) return;
        
        let paginationContainer = table.parentElement.querySelector('.pagination-container');
        if (!paginationContainer) {
            paginationContainer = document.createElement('div');
            paginationContainer.className = 'pagination-container mt-3 d-flex justify-content-center';
            table.parentElement.appendChild(paginationContainer);
        }
        
        let currentPage = 1;
        
        // Usar índice numérico en lugar de tableId para evitar problemas con guiones
        const fnName = 'showPage_' + tableId.replace(/-/g, '_');
        
        window[fnName] = function(page) {
            if (page < 1 || page > totalPages) return;
            currentPage = page;
            const start = (page - 1) * rowsPerPage;
            const end = start + rowsPerPage;
            rows.forEach((row, index) => {
                row.style.display = (index >= start && index < end) ? '' : 'none';
            });
            renderPagination();
        };
        
        function renderPagination() {
            let html = '<nav><ul class="pagination mb-0 pagination-sm">';
            html += '<li class="page-item ' + (currentPage === 1 ? 'disabled' : '') + '">';
            html += '<a class="page-link bg-dark text-white border-secondary" href="#" onclick="event.preventDefault(); ' + fnName + '(' + (currentPage - 1) + ')">‹</a>';
            html += '</li>';
            for (let i = 1; i <= totalPages; i++) {
                html += '<li class="page-item ' + (currentPage === i ? 'active' : '') + '">';
                html += '<a class="page-link ' + (currentPage === i ? 'bg-primary text-white' : 'bg-dark text-white border-secondary') + '" href="#" onclick="event.preventDefault(); ' + fnName + '(' + i + ')">' + i + '</a>';
                html += '</li>';
            }
            html += '<li class="page-item ' + (currentPage === totalPages ? 'disabled' : '') + '">';
            html += '<a class="page-link bg-dark text-white border-secondary" href="#" onclick="event.preventDefault(); ' + fnName + '(' + (currentPage + 1) + ')">›</a>';
            html += '</li>';
            html += '</ul></nav>';
            paginationContainer.innerHTML = html;
        }
        
        window[fnName](1);
    }
    
    setTimeout(function() {
        const tables = document.querySelectorAll('table');
        tables.forEach((table, index) => {
            if (!table.id) {
                table.id = 'table-' + index;
            }
            const tbody = table.querySelector('tbody');
            if (tbody && tbody.querySelectorAll('tr').length > 10) {
                agregarPaginacionATabla(table.id, 10);
            }
        });
    }, 100);
});
