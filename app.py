from flask import Flask, render_template, request, jsonify, send_file
import requests
from bs4 import BeautifulSoup
import re
import threading
import queue
import time
from collections import Counter
from datetime import datetime
import json
import io
import pandas as pd

app = Flask(__name__)

# Variáveis globais para controle
running = False
paused = False
stopped = False
valid_proxies = []
results = []
task_queue = queue.Queue()
threads = []
search_counter = 0
saved_cnpjs = set()
monthly_cnpjs = Counter()
city_cnpj_count = Counter()
logs = []

# Dicionário de estados e cidades
states_cities = {
    "AC": ["Rio Branco", "Cruzeiro do Sul", "Sena Madureira", "Tarauacá", "Feijó"],
    "AL": ["Maceió", "Arapiraca", "Palmeira dos Índios", "Rio Largo", "Penedo"],
}

# Sites prioritários
priority_sites = [
    "cnpj.biz",
    "econodata.com.br",
    "casadosdados.com.br",
    "informecadastral.com.br",
    "diariocidade.com.br",
    "consultas.plus"
]

def log_message(message, level="info"):
    """Adiciona uma mensagem ao log."""
    logs.append({"message": message, "level": level, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})

@app.route('/')
def index():
    return render_template('index.html', states=states_cities.keys())

@app.route('/cities/<state>')
def get_cities(state):
    return jsonify(states_cities.get(state, []))

@app.route('/load_proxies', methods=['POST'])
def load_proxies():
    global valid_proxies
    data = request.json
    proxies = data.get('proxies', '').splitlines()
    proxies = [p.strip() for p in proxies if p.strip()]
    valid_proxies = proxies
    log_message(f"Carregados {len(proxies)} proxies manualmente.")
    return jsonify({"message": f"Carregados {len(proxies)} proxies manualmente."})

@app.route('/test_proxies', methods=['POST'])
def test_proxies():
    global valid_proxies
    if not valid_proxies:
        log_message("Nenhum proxy carregado para testar.", "error")
        return jsonify({"error": "Nenhum proxy carregado para testar."}), 400

    proxies = valid_proxies.copy()
    valid_proxies = []
    progress = {"total": len(proxies), "current": 0}

    for i, proxy in enumerate(proxies):
        try:
            response = requests.get("https://www.google.com", proxies={"http": proxy, "https": proxy}, timeout=5)
            if response.status_code == 200:
                valid_proxies.append(proxy)
                log_message(f"Proxy {proxy} válido.")
            else:
                log_message(f"Proxy {proxy} retornou status {response.status_code}.", "error")
        except Exception as e:
            log_message(f"Erro no proxy {proxy}: {str(e)}", "error")
        progress["current"] = i + 1

    log_message(f"Teste concluído. {len(valid_proxies)} proxies válidos.")
    return jsonify({"message": f"Teste concluído. {len(valid_proxies)} proxies válidos."})

@app.route('/start_search', methods=['POST'])
def start_search():
    global running, paused, stopped, results, search_counter
    if running:
        log_message("Busca já em andamento.", "error")
        return jsonify({"error": "Busca já em andamento."}), 400

    data = request.json
    search_term = data.get('search_term')
    selected_cities = data.get('cities')
    state = data.get('state')
    max_pages = int(data.get('max_pages', 5))
    num_threads = int(data.get('num_threads', 1))

    if not search_term or not selected_cities or not state:
        log_message("Termo de busca, cidades e estado são obrigatórios.", "error")
        return jsonify({"error": "Termo de busca, cidades e estado são obrigatórios."}), 400

    running = True
    paused = False
    stopped = False
    results = []
    search_counter = 0

    threading.Thread(target=manage_search, args=(search_term, selected_cities, state, max_pages, num_threads), daemon=True).start()
    return jsonify({"message": "Busca iniciada."})

@app.route('/pause_search', methods=['POST'])
def pause_search():
    global paused
    if running:
        paused = not paused
        log_message(f"Busca {'pausada' if paused else 'retomada'}.")
        return jsonify({"message": f"Busca {'pausada' if paused else 'retomada'}."})
    return jsonify({"error": "Nenhuma busca em andamento."}), 400

@app.route('/stop_search', methods=['POST'])
def stop_search():
    global running, stopped
    if running:
        stopped = True
        running = False
        log_message("Busca parada pelo usuário.")
        return jsonify({"message": "Busca parada."})
    return jsonify({"error": "Nenhuma busca em andamento."}), 400

@app.route('/get_results', methods=['GET'])
def get_results():
    return jsonify({"results": results, "logs": logs})

@app.route('/dashboard', methods=['GET'])
def dashboard():
    cities_searched = len(set([result["Localização"] for result in results if "Localização" in result]))
    top_city = city_cnpj_count.most_common(1)
    top_city_text = top_city[0][0] + f" ({top_city[0][1]})" if top_city else "N/A"
    current_month = datetime.now().strftime("%Y-%m")
    monthly_count = monthly_cnpjs[current_month]
    return jsonify({
        "cities_searched": cities_searched,
        "top_city": top_city_text,
        "monthly_cnpjs": monthly_count
    })

@app.route('/save_results', methods=['POST'])
def save_results():
    global saved_cnpjs
    data = request.json
    selected_fields = data.get('fields', [])
    if not results:
        return jsonify({"error": "Nenhum resultado para salvar."}), 400
    if not selected_fields:
        return jsonify({"error": "Selecione pelo menos um campo."}), 400

    df = pd.DataFrame(results)
    if "CNPJ" in df.columns:
        df.drop_duplicates(subset="CNPJ", keep="first", inplace=True)
        for cnpj in df["CNPJ"]:
            if cnpj != "N/A":
                saved_cnpjs.add(cnpj)

    df = df[selected_fields]
    output = io.StringIO()
    df.to_csv(output, index=False, encoding='utf-8')
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f"resultados_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    )

def get_search_url(search_term, cities, state, page):
    global search_counter
    first = (page - 1) * 10 + 1
    site_index = (search_counter // 5) % len(priority_sites)
    priority_site = priority_sites[site_index]
    search_counter += 1
    log_message(f"Priorizando site: {priority_site} na página {page}")
    cities_query = "+".join(cities)
    return f"https://www.bing.com/search?q={search_term}+in+{cities_query},+{state}+site:{priority_site}&first={first}"

def fetch_cnpj_details(cnpj):
    cnpj = re.sub(r'[^0-9]', '', cnpj)
    url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            socios = ", ".join([socio["nome"] for socio in data.get("qsa", [])]) if data.get("qsa") else "N/A"
            return {
                "Situação Cadastral": data.get("situacao_cadastral", "N/A"),
                "Nome dos Sócios": socios,
                "Data de Abertura": data.get("data_inicio_atividade", "N/A"),
                "Inscrição Estadual": data.get("inscricao_estadual", "N/A")
            }
        else:
            log_message(f"Erro na API para CNPJ {cnpj}: Status {response.status_code}", "error")
            return {"Situação Cadastral": "N/A", "Nome dos Sócios": "N/A", "Data de Abertura": "N/A", "Inscrição Estadual": "N/A"}
    except Exception as e:
        log_message(f"Erro ao consultar CNPJ {cnpj}: {str(e)}", "error")
        return {"Situação Cadastral": "N/A", "Nome dos Sócios": "N/A", "Data de Abertura": "N/A", "Inscrição Estadual": "N/A"}

def extract_details_from_page(url, proxy=None):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124'}
    proxies = {"http": proxy, "https": proxy} if proxy else None
    try:
        response = requests.get(url, headers=headers, proxies=proxies, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.get_text()
        links = [a.get('href') for a in soup.find_all('a', href=True)]

        cnpj_pattern = re.compile(r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}')
        phone_pattern = re.compile(r'\(?\d{2}\)?[\s-]?\d{4,5}[\s-]?\d{4}')
        email_pattern = re.compile(r'[\w\.-]+@[\w\.-]+\.\w+')
        website_pattern = re.compile(r'(?:https?://)?(?:www\.)?[\w\.-]+\.(?:com|com\.br|org|net)(?:/[\w/-]*)?')
        whatsapp_pattern = re.compile(r'(?:https?://)?(?:wa\.me|api\.whatsapp\.com|whatsapp\.com)/[\d+]{10,15}|\(?\d{2}\)?[\s-]?\d{5}[\s-]?\d{4}')

        cnpj = cnpj_pattern.search(text).group() if cnpj_pattern.search(text) else "N/A"
        phone = phone_pattern.search(text).group() if phone_pattern.search(text) else "N/A"
        email = email_pattern.search(text).group() if email_pattern.search(text) else "N/A"
        website = website_pattern.search(text).group() if website_pattern.search(text) else "N/A"
        whatsapp = whatsapp_pattern.search(text).group() if whatsapp_pattern.search(text) else "N/A"

        social_media = {
            "Google Meu Negócio": "N/A",
            "LinkedIn": "N/A",
            "Instagram": "N/A",
            "WhatsApp": whatsapp
        }
        for link in links:
            if "google.com/maps" in link or "g.page" in link:
                social_media["Google Meu Negócio"] = link
            elif "linkedin.com" in link:
                social_media["LinkedIn"] = link
            elif "instagram.com" in link:
                social_media["Instagram"] = link
            elif "whatsapp.com" in link or "wa.me" in link:
                social_media["WhatsApp"] = link

        state = request.json.get('state') if request.json else None
        state_found = False
        location = "N/A"
        if state:
            for city in states_cities.get(state, []):
                if city in text:
                    state_found = True
                    location = city
                    break
        if not state_found and state:
            log_message(f"Localização de {url} não corresponde ao estado {state}. Ignorando.", "warning")
            return None

        details = {
            "CNPJ": cnpj,
            "Telefone": phone,
            "Email": email,
            "Localização": location,
            "Website": website,
            "WhatsApp": social_media["WhatsApp"],
            "Google Meu Negócio": social_media["Google Meu Negócio"],
            "LinkedIn": social_media["LinkedIn"],
            "Instagram": social_media["Instagram"]
        }

        if cnpj != "N/A" and cnpj not in saved_cnpjs:
            cnpj_details = fetch_cnpj_details(cnpj)
            details.update(cnpj_details)
            current_month = datetime.now().strftime("%Y-%m")
            monthly_cnpjs[current_month] += 1
            city_cnpj_count[location] += 1

        return details
    except Exception as e:
        log_message(f"Erro ao extrair detalhes de {url}: {str(e)}", "error")
        return None

def worker():
    global running, paused, stopped
    while not stopped:
        try:
            if paused:
                time.sleep(1)
                continue
            page = task_queue.get(timeout=1)
            if not running or stopped:
                break

            search_term = task_queue.search_term
            selected_cities = task_queue.selected_cities
            state = task_queue.state
            proxy = valid_proxies[0] if valid_proxies else None

            url = get_search_url(search_term, selected_cities, state, page)
            log_message(f"Thread {threading.current_thread().name} buscando página {page}...")

            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124'}
            proxies = {"http": proxy, "https": proxy} if proxy else None
            try:
                response = requests.get(url, headers=headers, proxies=proxies, timeout=10)
                soup = BeautifulSoup(response.text, "html.parser")

                search_results = soup.select(".b_algo")
                if not search_results:
                    log_message(f"Nenhum resultado na página {page}.", "warning")
                else:
                    for result in search_results:
                        if stopped:
                            break
                        try:
                            title = result.select_one("h2").text.strip() if result.select_one("h2") else "N/A"
                            link_element = result.select_one("a")
                            url = link_element["href"] if link_element and "href" in link_element.attrs else "N/A"
                            if url != "N/A":
                                details = extract_details_from_page(url, proxy)
                                if details and details["CNPJ"] not in saved_cnpjs:
                                    result_data = {"Título": title, "URL": url}
                                    result_data.update(details)
                                    results.append(result_data)
                                    log_message(f"Encontrado: {title} - {url} (CNPJ: {details['CNPJ']})")
                        except AttributeError as e:
                            log_message(f"Erro ao extrair dados de um resultado: {str(e)}", "error")

            except Exception as e:
                log_message(f"Erro na página {page}: {str(e)}", "error")
            finally:
                task_queue.task_done()

        except queue.Empty:
            break

def manage_search(search_term, selected_cities, state, max_pages, num_threads):
    global running, stopped, threads
    task_queue.search_term = search_term
    task_queue.selected_cities = selected_cities
    task_queue.state = state

    for page in range(1, max_pages + 1):
        task_queue.put(page)

    threads = []
    for i in range(min(num_threads, max_pages)):
        t = threading.Thread(target=worker, name=f"Thread-{i+1}", daemon=True)
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    running = False
    stopped = False
    paused = False
    log_message(f"Busca concluída. Total de resultados: {len(results)}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
