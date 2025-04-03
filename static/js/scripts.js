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

function saveResults() {
    fetch('/get_results')
    .then(response => response.json())
    .then(data => {
        const results = data.results;
        if (results.length === 0) {
            alert('Nenhum resultado para salvar.');
            return;
        }
        const blob = new Blob([JSON.stringify(results, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'resultados.json';
        a.click();
        URL.revokeObjectURL(url);
    });
}

function pollResults() {
    fetch('/get_results')
    .then(response => response.json())
    .then(data => {
        const logsDiv = document.getElementById('logs');
        data.results.forEach(result => {
            if (result.log) {
                logsDiv.innerHTML += `<p>${result.log}</p>`;
            } else if (result.result) {
                logsDiv.innerHTML += `<p>Encontrado: ${result.result.Título} - ${result.result.URL} (CNPJ: ${result.result.CNPJ})</p>`;
            }
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
