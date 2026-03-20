document.addEventListener("DOMContentLoaded", () => {
    
    // --- View Navigation ---
    const navItems = document.querySelectorAll('.sidebar nav ul li');
    const views = document.querySelectorAll('.view-section');

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
