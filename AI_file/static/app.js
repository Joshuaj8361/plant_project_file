document.addEventListener("DOMContentLoaded", () => {
    const appContainer = document.querySelector('.app-container');
    const sidebar = document.getElementById('sidebar');
    const sidebarToggle = document.getElementById('sidebar-toggle');
    const sidebarOverlay = document.getElementById('sidebar-overlay');
    const desktopMediaQuery = window.matchMedia('(min-width: 769px)');

    // --- View Navigation ---
    const navItems = document.querySelectorAll('.sidebar nav ul li');
    const views = document.querySelectorAll('.view-section');

    function setSidebarState(isOpen) {
        appContainer.classList.toggle('sidebar-open', isOpen);
        sidebarToggle.setAttribute('aria-expanded', String(isOpen));
        sidebar.setAttribute('aria-hidden', String(!isOpen));
        sidebarOverlay.setAttribute('aria-hidden', String(!isOpen));
    }

    function applyResponsiveSidebarState() {
        setSidebarState(desktopMediaQuery.matches);
    }

    sidebarToggle.addEventListener('click', () => {
        const isOpen = appContainer.classList.contains('sidebar-open');
        setSidebarState(!isOpen);
    });

    sidebarOverlay.addEventListener('click', () => {
        setSidebarState(false);
    });

    if (typeof desktopMediaQuery.addEventListener === 'function') {
        desktopMediaQuery.addEventListener('change', applyResponsiveSidebarState);
    } else {
        desktopMediaQuery.addListener(applyResponsiveSidebarState);
    }

    applyResponsiveSidebarState();

    navItems.forEach(item => {
        item.addEventListener('click', () => {
            // Update active state in nav
            navItems.forEach(nav => nav.classList.remove('active'));
            item.classList.add('active');

            // Hide all views, show targeted view
            const targetView = item.getAttribute('data-view');
            views.forEach(view => {
                view.classList.add('hidden');
                if(view.id === `view-${targetView}`) {
                    view.classList.remove('hidden');
                }
            });

            if (!desktopMediaQuery.matches) {
                setSidebarState(false);
            }
        });
    });

    // --- Data Fetching ---
    
    // Fetch stats
    fetch('/api/stats')
        .then(res => res.json())
        .then(data => {
            animateValue("stat-plants", 0, data.total_plants || 0, 1000);
            animateValue("stat-chemicals", 0, data.total_phytochemicals || 0, 1000);
            animateValue("stat-proteins", 0, data.total_proteins || 0, 1000);
            animateValue("stat-interactions", 0, data.total_interactions || 0, 1500);
        })
        .catch(err => console.error("Error fetching stats:", err));

    // Fetch plants
    fetch('/api/plants')
        .then(res => res.json())
        .then(plants => {
            const tbody = document.getElementById('table-plants');
            tbody.innerHTML = '';
            plants.forEach(plant => {
                // If CSV keys are different or missing
                const pid = plant.Plant_ID || '-';
                // Note: The CSV might have trailing commas making column names messy, 
                // we'll try to find the name key intelligently.
                const pNameKey = Object.keys(plant).find(k => k.toLowerCase().includes('name')) || 'Common_Name_of_Plant';
                const pName = plant[pNameKey] || '-';
                
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td><strong>${pid}</strong></td>
                    <td>${pName}</td>
                `;
                tbody.appendChild(tr);
            });
        })
        .catch(err => console.error("Error fetching plants:", err));

    // Fetch proteins
    fetch('/api/proteins')
        .then(res => res.json())
        .then(proteins => {
            const tbody = document.getElementById('table-proteins');
            tbody.innerHTML = '';
            proteins.forEach(protein => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td><strong>${protein.UniProt_ID || '-'}</strong></td>
                    <td>${protein.Protein_Name || '-'}</td>
                `;
                tbody.appendChild(tr);
            });
        })
        .catch(err => console.error("Error fetching proteins:", err));

    // --- Disease Search Logic ---
    const searchBtn = document.getElementById('disease-search-btn');
    const searchInput = document.getElementById('disease-input');
    const searchTable = document.getElementById('disease-search-table');
    const searchTbody = document.getElementById('table-disease-search');
    const searchError = document.getElementById('disease-search-error');

    if (searchBtn) {
        searchBtn.addEventListener('click', () => {
            const disease = searchInput.value.trim();
            if(!disease) return;

            searchBtn.textContent = "Searching...";
            searchTable.style.display = 'none';
            searchError.style.display = 'none';
            
            fetch(`/api/disease-search?disease=${encodeURIComponent(disease)}`)
                .then(res => res.json())
                .then(plants => {
                    searchBtn.textContent = "Search";
                    if(plants.length === 0) {
                        searchError.textContent = "No recommended plants/fruits found for this disease in our database. (Try 'diabetes' or 'fever')";
                        searchError.style.color = "#ffcccc";
                        searchError.style.display = 'block';
                    } else {
                        searchTbody.innerHTML = '';
                        plants.forEach(plant => {
                            const pid = plant.Plant_ID || '-';
                            const pNameKey = Object.keys(plant).find(k => k.toLowerCase().includes('name')) || 'Common_Name_of_Plant';
                            const pName = plant[pNameKey] || '-';
                            
                            const tr = document.createElement('tr');
                            tr.innerHTML = `
                                <td><strong>${pid}</strong></td>
                                <td>${pName}</td>
                            `;
                            searchTbody.appendChild(tr);
                        });
                        searchTable.style.display = 'table';
                    }
                })
                .catch(err => {
                    console.error("Error fetching disease search:", err);
                    searchBtn.textContent = "Search";
                    searchError.textContent = "An error occurred while searching.";
                    searchError.style.color = "#ffcccc";
                    searchError.style.display = 'block';
                });
        });
        
        // Allow pressing Enter to search
        searchInput.addEventListener('keypress', function (e) {
            if (e.key === 'Enter') {
                searchBtn.click();
            }
        });
    }

    // --- GNN Logic ---
    const gnnBtn = document.getElementById('gnn-btn');
    const gnnInput = document.getElementById('gnn-input');
    const gnnTable = document.getElementById('gnn-table');
    const gnnTbody = document.getElementById('table-gnn');
    const gnnError = document.getElementById('gnn-error');

    if (gnnBtn) {
        gnnBtn.addEventListener('click', () => {
            const disease = gnnInput.value.trim();
            if(!disease) return;

            gnnBtn.textContent = "Predicting...";
            gnnTable.style.display = 'none';
            gnnError.style.display = 'none';
            
            fetch(`/api/gnn-predict?disease=${encodeURIComponent(disease)}`)
                .then(res => res.json())
                .then(plants => {
                    gnnBtn.textContent = "Predict";
                    if(!Array.isArray(plants) || plants.length === 0) {
                        gnnError.textContent = "Could not generate novel insights for this disease (requires valid disease map).";
                        gnnError.style.color = "#ffcccc";
                        gnnError.style.display = 'block';
                    } else {
                        gnnTbody.innerHTML = '';
                        plants.forEach(plant => {
                            const tr = document.createElement('tr');
                            tr.innerHTML = `
                                <td><strong>${plant.Plant_ID || '-'}</strong></td>
                                <td>${plant.Common_Name_of_Plant || '-'}</td>
                                <td style="color: var(--accent-color); font-weight: bold;">${plant.GNN_Similarity_Score}% Match</td>
                            `;
                            gnnTbody.appendChild(tr);
                        });
                        gnnTable.style.display = 'table';
                    }
                })
                .catch(err => {
                    console.error("Error fetching GNN predictions:", err);
                    gnnBtn.textContent = "Predict";
                    gnnError.textContent = "An error occurred during network traversal.";
                    gnnError.style.color = "#ffcccc";
                    gnnError.style.display = 'block';
                });
        });
        
        // Allow pressing Enter to search
        gnnInput.addEventListener('keypress', function (e) {
            if (e.key === 'Enter') {
                gnnBtn.click();
            }
        });
    }

    // --- Helper for number animation ---
    function animateValue(id, start, end, duration) {
        if (start === end) return;
        let obj = document.getElementById(id);
        let startTimestamp = null;
        const step = (timestamp) => {
            if (!startTimestamp) startTimestamp = timestamp;
            const progress = Math.min((timestamp - startTimestamp) / duration, 1);
            obj.innerHTML = Math.floor(progress * (end - start) + start);
            if (progress < 1) {
                window.requestAnimationFrame(step);
            }
        };
        window.requestAnimationFrame(step);
    }
});
