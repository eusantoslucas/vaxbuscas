function updateCities() {
    const state = document.getElementById('state').value;
    const citiesContainer = document.getElementById('cities_container');
    citiesContainer.innerHTML = '';

    if (state) {
        fetch(`/cities/${state}`)
            .then(response => response.json())
            .then(cities => {
                cities.forEach(city => {
                    const checkbox = document.createElement('input');
                    checkbox.type = 'checkbox';
                    checkbox.value = city;
                    checkbox.id = `city_${city}`;
                    const label = document.createElement('label');
                    label.htmlFor = `city_${city}`;
                    label.textContent = city;
                    citiesContainer.appendChild(checkbox);
                    citiesContainer.appendChild(label);
                    citiesContainer.appendChild(document.createElement('br'));
                });
            });
    }
}

function loadProxies() {
    const proxies = document.getElementById('proxies').value;
    fetch('/load_proxies', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ proxies })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert(data.error);
        } else {
            alert(data.message);
        }
    });
}

function testProxies() {
    fetch('/test_proxies', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert(data.error);
        } else {
            alert(data.message);
        }
    });
}

function startSearch() {
    const searchTerm = document.getElementById('search_term').value;
    const state = document.getElementById('state').value;
    const cities = Array.from(document.querySelectorAll('#cities_container input:checked')).map(input => input.value);
    const maxPages = document.getElementById('max_pages').value;
    const numThreads = document.getElementById('num_threads').value;

    if (!searchTerm || !state || cities.length === 0) {
        alert('Por favor, preencha o termo de busca, selecione um estado e pelo menos uma cidade.');
        return;
    }

    fetch('/start_search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ search_term: searchTerm, cities, state, max_pages: maxPages, num_threads: numThreads })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert(data.error);
        } else {
            alert(data.message);
            pollResults();
            updateDashboard();
        }
    });
}

function pauseSearch() {
    fetch('/pause_search', { method: 'POST' })
    .then(response => response.json())
    .then(data => alert(data.message));
}

function stopSearch() {
    fetch('/stop_search', { method: 'POST' })
    .then(response => response.json())
    .then(data => alert(data.message));
}

function showSaveFields() {
    const modal = document.getElementById('fieldsModal');
    const fieldsContainer = document.getElementById('fields_container');
    fieldsContainer.innerHTML = '';

    const fields = ["Título", "URL", "CNPJ", "Telefone", "Email", "Localização", 
                   "Website", "WhatsApp", "Google Meu Negócio", "LinkedIn", "Instagram",
                   "Situação Cadastral", "Nome dos Sócios", "Data de Abertura", "Inscrição Estadual"];
    fields.forEach(field => {
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.value = field;
        checkbox.id = `field_${field}`;
        checkbox.checked = true;
        const label = document.createElement('label');
        label.htmlFor = `field_${field}`;
        label.textContent = field;
        fieldsContainer.appendChild(checkbox);
        fieldsContainer.appendChild(label);
        fieldsContainer.appendChild(document.createElement('br'));
    });

    modal.style.display = 'block';
}

function closeModal() {
    document.getElementById('fieldsModal').style.display = 'none';
}

function saveResults() {
    const fields = Array.from(document.querySelectorAll('#fields_container input:checked')).map(input => input.value);
    fetch('/save_results', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ fields })
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(data => { throw new Error(data.error); });
        }
        return response.blob();
    })
    .then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `resultados_${new Date().toISOString().replace(/[:.]/g, '-')}.csv`;
        a.click();
        window.URL.revokeObjectURL(url);
        closeModal();
    })
    .catch(error => {
        alert(error.message);
    });
}

function pollResults() {
    fetch('/get_results')
    .then(response => response.json())
    .then(data => {
        const logsDiv = document.getElementById('logs');
        data.logs.forEach(log => {
            const color = log.level === "info" ? "green" : log.level === "error" ? "red" : "yellow";
            logsDiv.innerHTML += `<p style="color: ${color}">[${log.timestamp}] ${log.message}</p>`;
        });
        data.results.forEach(result => {
            logsDiv.innerHTML += `<p style="color: green">Encontrado: ${result.Título} - ${result.URL} (CNPJ: ${result.CNPJ})</p>`;
        });
        logsDiv.scrollTop = logsDiv.scrollHeight;
        setTimeout(pollResults, 1000);
    });
}

function updateDashboard() {
    fetch('/dashboard')
    .then(response => response.json())
    .then(data => {
        document.getElementById('cities_searched').textContent = data.cities_searched;
        document.getElementById('top_city').textContent = data.top_city;
        document.getElementById('monthly_cnpjs').textContent = data.monthly_cnpjs;
        setTimeout(updateDashboard, 5000);
    });
}
