document.addEventListener('DOMContentLoaded', () => {
    const flashes = document.querySelectorAll('.flash');
    flashes.forEach(flash => {
        setTimeout(() => {
            flash.style.opacity = '0';
            flash.style.transform = 'translateX(100%)';
            flash.style.transition = 'all .3s ease';
            setTimeout(() => flash.remove(), 300);
        }, 4000);
    });

    const searchInput = document.getElementById('search-input');
    const searchForm = document.getElementById('search-form');
    if (searchInput && searchForm) {
        let timer;
        searchInput.addEventListener('input', () => {
            clearTimeout(timer);
            timer = setTimeout(() => searchForm.submit(), 300);
        });
    }

// Date filter validation
    const dateFilterForm = document.getElementById('date-filter-form');
    const dateFromInput = document.getElementById('date-from');
    const dateToInput = document.getElementById('date-to');
    const dateError = document.getElementById('date-error');

    // Restauramos tu lógica original para bloquear el calendario en el HTML
    if (dateFromInput && dateToInput) {
        const now = new Date();
        const today = now.toISOString().slice(0, 10);
        dateFromInput.setAttribute('max', today);
        dateToInput.setAttribute('max', today);
        if (!dateFromInput.value) dateFromInput.value = today;
        if (!dateToInput.value) dateToInput.value = today;
    }

    if (dateFilterForm && dateFromInput && dateToInput && dateError) {
        dateFilterForm.addEventListener('submit', e => {
            const from = dateFromInput.value;
            const to = dateToInput.value;
            const today = new Date().toISOString().slice(0, 10);

            // Función nuclear para apagar cualquier cosa que parezca un spinner
            const apagarSpinner = () => {
                const spinners = document.querySelectorAll('#spinner, #loading, #procesando, .spinner-container, .loading-overlay, .loader, [id*="spin"], [class*="spin"], [id*="load"]');
                spinners.forEach(s => s.style.display = 'none');
            };

            // Si hay un error en las fechas...
            if ((from && to && from > to) || (from && from > today) || (to && to > today)) {
                e.preventDefault(); // 1. Frena el envío al servidor
                e.stopImmediatePropagation(); // 2. 🛑 NUEVO: Frena CUALQUIER otro script que quiera prender el spinner

                // Mostramos el mensaje correcto
                if (from > to) {
                    dateError.textContent = 'La fecha desde no puede ser mayor que la fecha hasta.';
                } else {
                    dateError.textContent = 'No se pueden seleccionar fechas posteriores a hoy.';
                }
                dateError.style.display = 'block';

                // 3. Apagamos el spinner al instante, y de nuevo a los 50ms por si otro script es más lento
                apagarSpinner();
                setTimeout(apagarSpinner, 50);
                
                return; // Corta la ejecución acá
            }

            dateError.style.display = 'none';
        });
    }

    // Theme toggle
    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        const currentTheme = localStorage.getItem('theme') || 'dark';
        if (currentTheme === 'light') {
            document.body.classList.add('light-theme');
            themeToggle.textContent = '🌙';
        } else {
            themeToggle.textContent = '☀️';
        }

        themeToggle.addEventListener('click', () => {
            document.body.classList.toggle('light-theme');
            const isLight = document.body.classList.contains('light-theme');
            localStorage.setItem('theme', isLight ? 'light' : 'dark');
            themeToggle.textContent = isLight ? '🌙' : '☀️';
        });
    }

    // Sidebar toggle
    const sidebar = document.getElementById('sidebar');
    const sidebarOverlay = document.getElementById('sidebar-overlay');
    const sidebarToggle = document.getElementById('sidebar-toggle');
    const sidebarClose = document.getElementById('sidebar-close');

    const closeSidebar = () => {
        if (!sidebar) return;
        sidebar.classList.remove('open');
        document.body.classList.remove('sidebar-open');
        if (sidebarOverlay) sidebarOverlay.classList.remove('active');
        sidebar.setAttribute('aria-hidden', 'true');
        if (sidebarOverlay) sidebarOverlay.setAttribute('aria-hidden', 'true');
    };

    const openSidebar = () => {
        if (!sidebar) return;
        sidebar.classList.add('open');
        document.body.classList.add('sidebar-open');
        if (sidebarOverlay) sidebarOverlay.classList.add('active');
        sidebar.setAttribute('aria-hidden', 'false');
        if (sidebarOverlay) sidebarOverlay.setAttribute('aria-hidden', 'false');
    };

    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', () => {
            if (sidebar && sidebar.classList.contains('open')) {
                closeSidebar();
            } else {
                openSidebar();
            }
        });
    }

    if (sidebarClose) sidebarClose.addEventListener('click', closeSidebar);
    if (sidebarOverlay) sidebarOverlay.addEventListener('click', closeSidebar);

    document.addEventListener('keydown', event => {
        if (event.key === 'Escape') {
            closeSidebar();
        }
    });

    document.querySelectorAll('.sidebar .nav-links a').forEach(link => {
        link.addEventListener('click', () => closeSidebar());
    });

    // Tabla columnas redimensionables (aplica a todas las tablas con clase .tabla)
    const makeTableResizable = table => {
        const ths = table.querySelectorAll('thead th');
        if (!ths.length) return;

        // Asegura un colgroup para controlar anchos por columna
        let colgroup = table.querySelector('colgroup');
        if (!colgroup) {
            colgroup = document.createElement('colgroup');
            ths.forEach(() => {
                const col = document.createElement('col');
                colgroup.appendChild(col);
            });
            table.prepend(colgroup);
        } else if (colgroup.children.length < ths.length) {
            for (let i = colgroup.children.length; i < ths.length; i++) {
                const col = document.createElement('col');
                colgroup.appendChild(col);
            }
        }

        table.style.tableLayout = 'fixed';

        ths.forEach((th, index) => {
            if (!th.querySelector('.resizer')) {
                const resizer = document.createElement('div');
                resizer.className = 'resizer';
                th.appendChild(resizer);

                let startX = 0;
                let startWidth = 0;
                const minContentWidth = Math.max(100, th.scrollWidth + 12);

                const onMouseMove = e => {
                    const delta = e.clientX - startX;
                    let newWidth = startWidth + delta;
                    if (newWidth < minContentWidth) newWidth = minContentWidth;
                    if (newWidth > 50) {
                        th.style.width = `${newWidth}px`;
                        const col = table.querySelectorAll('col')[index];
                        if (col) col.style.width = `${newWidth}px`;
                    }
                };

                const onMouseUp = () => {
                    document.removeEventListener('mousemove', onMouseMove);
                    document.removeEventListener('mouseup', onMouseUp);
                };

                resizer.addEventListener('mousedown', e => {
                    e.preventDefault();
                    startX = e.clientX;
                    startWidth = th.offsetWidth;
                    document.addEventListener('mousemove', onMouseMove);
                    document.addEventListener('mouseup', onMouseUp);
                });
            }

            // Establecer ancho inicial a partir del col + contenido
            const currentCol = table.querySelectorAll('col')[index];
            const desiredWidth = Math.max(100, th.scrollWidth + 12);
            if (currentCol) currentCol.style.width = `${desiredWidth}px`;
            th.style.width = `${desiredWidth}px`;
        });
    };

    document.querySelectorAll('.table-wrapper .tabla').forEach(makeTableResizable);

    // Transportista field toggle
    const nuevoEstadoSelect = document.getElementById('nuevo_estado');
    const transportistaGroup = document.getElementById('transportista-group');
    const transportistaSelect = document.getElementById('transportista');
    
    if (nuevoEstadoSelect && transportistaGroup) {
        nuevoEstadoSelect.addEventListener('change', () => {
            if (nuevoEstadoSelect.value === 'En tránsito') {
                transportistaGroup.style.display = 'block';
                transportistaSelect.required = true;
            } else {
                transportistaGroup.style.display = 'none';
                transportistaSelect.required = false;
                transportistaSelect.value = '';
            }
        });
    }

    // Cargar datos de prueba con ciclo entre 3 datasets
    const loadTestDataBtn = document.getElementById('load-test-data');
    if (loadTestDataBtn) {
        const testDatasets = [
            {
                remitente_nombre: 'Juan Carlos Martínez',
                remitente_dni: '25456890',
                remitente_direccion: 'Avenida 9 de Julio 1234, Buenos Aires, CABA',
                remitente_telefono: '1145678901',
                remitente_email: 'juan.martinez@example.com',
                destinatario_nombre: 'Patricia González López',
                destinatario_dni: '33789012',
                destinatario_direccion: 'Calle Belgrano 567, Mendoza, Mendoza',
                destinatario_telefono: '2614567890',
                destinatario_email: 'patricia.gonzalez@example.com',
                origen: 'Buenos Aires',
                destino: 'Mendoza',
                peso: '1.8',
                dimensiones: '25x15x10 cm',
                descripcion: 'Documentos comerciales y muestras'
            },
            {
                remitente_nombre: 'Roberto Fernández Silva',
                remitente_dni: '23-34313092-9',
                remitente_direccion: 'Paseo Colón 2890, La Plata, Buenos Aires',
                remitente_telefono: '3416789012',
                remitente_email: 'roberto.fernandez@example.com',
                destinatario_nombre: 'Mariana Rodríguez Díaz',
                destinatario_dni: '27-34494462-3',
                destinatario_direccion: 'Ruta 9 km 45, Rosario, Santa Fe',
                destinatario_telefono: '3815234567',
                destinatario_email: 'mariana.rodriguez@example.com',
                origen: 'La Plata',
                destino: 'Rosario',
                peso: '3.2',
                dimensiones: '35x25x20 cm',
                descripcion: 'Mercadería para distribuición'
            },
            {
                remitente_nombre: 'Luis Alberto Sánchez',
                remitente_dni: '12345678',
                remitente_direccion: 'San Martín 450, Córdoba, Córdoba',
                remitente_telefono: '2214568934',
                remitente_email: 'luis.sanchez@example.com',
                destinatario_nombre: 'Claudia María Pérez',
                destinatario_dni: '23456789',
                destinatario_direccion: 'Calle Rivadavia 789, Salta, Salta',
                destinatario_telefono: '2615234890',
                destinatario_email: 'claudia.perez@example.com',
                origen: 'Córdoba',
                destino: 'Salta',
                peso: '2.5',
                dimensiones: '30x20x15 cm',
                descripcion: 'Paquete con artículos varios'
            }
        ];

        let currentDatasetIndex = parseInt(sessionStorage.getItem('testDataIndex') || '0');

        loadTestDataBtn.addEventListener('click', (e) => {
            e.preventDefault();
            
            const testData = testDatasets[currentDatasetIndex];
            
            // Llenar campos de texto
            for (const [key, value] of Object.entries(testData)) {
                const field = document.querySelector(`[name="${key}"]`);
                if (field) field.value = value;
            }

            // Marcar radio buttons
            const envioExpressNo = document.querySelector('input[name="envio_express"][value="off"]');
            if (envioExpressNo) envioExpressNo.checked = true;

            // Marcar checkbox de aceptación
            const aceptaLey = document.querySelector('input[name="acepta_ley"]');
            if (aceptaLey) aceptaLey.checked = true;

            // Cambiar índice para el próximo click
            currentDatasetIndex = (currentDatasetIndex + 1) % testDatasets.length;
            sessionStorage.setItem('testDataIndex', currentDatasetIndex);
        });
    }
});
