import os
import re
import sys
import requests
from datetime import date, timedelta
from ics import Calendar, Event
from ics.grammar.parse import ContentLine

TMDB_API_URL = "https://api.themoviedb.org/3"
TMDB_TOKEN = os.environ.get("TMDB_TOKEN", "")

# Eventos que saíram da API são mantidos por até N dias após o lançamento
KEEP_AFTER_RELEASE_DAYS = 30


def fetch_events():
    if not TMDB_TOKEN:
        print("Erro: variável TMDB_TOKEN não definida.")
        return None

    headers = {
        "Authorization": f"Bearer {TMDB_TOKEN}",
        "Accept": "application/json",
    }

    today = date.today().isoformat()
    # Buscar até 1 ano à frente
    end_date = date.today().replace(year=date.today().year + 1).isoformat()

    all_results = []
    page = 1

    while True:
        resp = requests.get(
            f"{TMDB_API_URL}/discover/movie",
            headers=headers,
            params={
                "language": "pt-BR",
                "region": "BR",
                "release_date.gte": today,
                "release_date.lte": end_date,
                "sort_by": "release_date.asc",
                "with_release_type": "3|2",   # theatrical (wide + limited)
                "page": page,
            },
        )

        print(f"Status HTTP (página {page}):", resp.status_code)

        if resp.status_code != 200:
            print("Falha ao acessar a API do TMDB:", resp.text[:200])
            return None

        data = resp.json()
        results = data.get("results", [])
        all_results.extend(results)

        if page >= data.get("total_pages", 1) or page >= 10:
            break
        page += 1

    print(f"Total de filmes obtidos do TMDB: {len(all_results)}")
    return all_results


def imdb_id_from_url(url):
    """Extrai o ID do IMDb (ttXXXXXXX) da URL do evento."""
    if not url:
        return None
    match = re.search(r"/(tt\d+)/", url)
    return match.group(1) if match else None


def tmdb_id_from_url(url):
    """Extrai o ID do TMDB da URL do evento."""
    if not url:
        return None
    match = re.search(r"/tmdb/(\d+)/", url)
    return match.group(1) if match else None


def load_existing_events(filepath):
    """Carrega eventos existentes do .ics, indexados pelo ID (TMDB ou IMDb)."""
    existing = {}
    if not os.path.exists(filepath):
        return existing

    with open(filepath, encoding="utf-8") as f:
        content = f.read()

    try:
        cal = Calendar(content)
        for event in cal.events:
            # Tentar extrair ID do TMDB primeiro, depois IMDb
            event_id = tmdb_id_from_url(event.url) or imdb_id_from_url(event.url)
            if event_id:
                existing[event_id] = event
    except Exception as e:
        print(f"Aviso: não foi possível carregar eventos existentes: {e}")

    return existing


def build_event(title, tmdb_id, release_date):
    event = Event()
    event.name = f"🎥 {title}"
    event.begin = release_date
    event.make_all_day()
    event.url = f"https://www.themoviedb.org/movie/{tmdb_id}/"
    return event


def merge_events(results, existing_events):
    today = date.today()
    cutoff = today - timedelta(days=KEEP_AFTER_RELEASE_DAYS)

    # Processar filmes vindos do TMDB
    api_events = {}
    for movie in results:
        title = movie.get("title")
        release_str = movie.get("release_date")
        tmdb_id = str(movie.get("id"))

        if not (title and release_str and tmdb_id):
            continue

        try:
            release_date = date.fromisoformat(release_str)
            api_events[tmdb_id] = build_event(title, tmdb_id, release_date)
        except Exception as e:
            print(f"Erro ao processar '{title}':", e)

    # Eventos existentes que sumiram da API: manter se ainda dentro do prazo
    preserved = 0
    expired = 0
    for event_id, event in existing_events.items():
        if event_id in api_events:
            continue

        try:
            event_date = event.begin.date() if hasattr(event.begin, "date") else event.begin
        except Exception:
            continue

        if event_date >= cutoff:
            api_events[event_id] = event
            preserved += 1
        else:
            expired += 1

    print(f"Eventos do TMDB: {len(api_events) - preserved}")
    print(f"Eventos preservados (fora da API, dentro do prazo): {preserved}")
    print(f"Eventos expirados (removidos): {expired}")

    return api_events


def main():
    filepath = "calendar.ics"

    existing_events = load_existing_events(filepath)
    print(f"Eventos existentes carregados: {len(existing_events)}")

    results = fetch_events()
    if results is None:
        print("Abortando: não foi possível buscar eventos da API.")
        sys.exit(1)

    merged = merge_events(results, existing_events)

    calendar = Calendar()
    calendar.extra.append(ContentLine(name="X-WR-CALNAME", value="Lançamentos filmes Brasil - Imdb"))
    for event in merged.values():
        calendar.events.add(event)

    # A biblioteca ics==0.7.2 insere linhas em branco entre propriedades,
    # o que não é válido no RFC 5545. Removemos aqui.
    output = "".join(calendar)
    output = "\n".join(line for line in output.splitlines() if line.strip())
    output += "\n"

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(output)

    print(f"Total de eventos no calendário: {len(merged)}")


if __name__ == "__main__":
    main()
