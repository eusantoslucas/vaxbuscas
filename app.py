from flask import Flask, render_template, request, jsonify
import requests
from bs4 import BeautifulSoup
import re

app = Flask(__name__)

# Dicionário de estados e cidades
states_cities = {
    "AC": ["Rio Branco", "Cruzeiro do Sul", "Sena Madureira", "Tarauacá", "Feijó"],
    "AL": ["Maceió", "Arapiraca", "Palmeira dos Índios", "Rio Largo", "Penedo"],
}

# Variáveis globais para armazenar resultados
results = []
running = False

@app.route('/')
def index():
    return render_template('index.html', states=states_cities.keys())

@app.route('/cities/<state>')
def get_cities(state):
    return jsonify(states_cities.get(state, []))

@app.route('/start_search', methods=['POST'])
def start_search():
    global running, results
    if running:
        return jsonify({"error": "Busca já em andamento."}), 400

    data = request.json
    search_term = data.get('search_term')
    selected_cities = data.get('cities')
    state = data.get('state')

    if not search_term or not selected_cities or not state:
        return jsonify({"error": "Termo de busca, cidades e estado são obrigatórios."}), 400

    running = True
    results = []

    # Simulação de busca (substitua por sua lógica de scraping real)
    try:
        url = f"https://www.bing.com/search?q={search_term}+in+{state}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")

        for result in soup.select(".b_algo")[:3]:  # Limita a 3 resultados para simplificar
            title = result.select_one("h2").text.strip() if result.select_one("h2") else "N/A"
            link = result.select_one("a")["href"] if result.select_one("a") else "N/A"
            results.append({"title": title, "url": link, "location": selected_cities[0]})
    except Exception as e:
        return jsonify({"error": f"Erro na busca: {str(e)}"}), 500

    running = False
    return jsonify({"message": "Busca concluída."})

@app.route('/get_results', methods=['GET'])
def get_results():
    return jsonify({"results": results})

@app.route('/stop_search', methods=['POST'])
def stop_search():
    global running
    running = False
    return jsonify({"message": "Busca parada."})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
