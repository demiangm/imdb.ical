import os
import re
import requests
from datetime import date, timedelta
from ics import Calendar, Event
from ics.grammar.parse import ContentLine

GRAPHQL_URL = "https://graphql.imdb.com/"
HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

# Eventos que saíram da API são mantidos por até N dias após o lançamento
KEEP_AFTER_RELEASE_DAYS = 30

QUERY = """
{
  comingSoon(
    comingSoonType: MOVIE,
    regionOverride: "BR",
    first: 250,
    releasingOnOrAfter: "%s"
  ) {
    edges {
      node {
        id
        titleText { text }
        releaseDate {
          day
          month
          year
        }
      }
    }
  }
}
"""


def fetch_events():
    # Busca a partir de hoje para pegar todos os próximos lançamentos
    # Filmes já lançados são preservados pelo mecanismo de merge
    start_date = date.today()
    query = QUERY % start_date.strftime("%Y-%m-%d")

    response = requests.post(GRAPHQL_URL, json={"query": query}, headers=HEADERS)
    print("Status HTTP:", response.status_code)

    if response.status_code != 200:
        print("Falha ao acessar a API GraphQL.")
        return None

    data = response.json()
    if "errors" in data:
        print("Erros na resposta GraphQL:", data["errors"])
        return None

    return data.get("data", {}).get("comingSoon", {}).get("edges", [])


def imdb_id_from_url(url):
    """Extrai o ID do IMDb (ttXXXXXXX) da URL do evento."""
    if not url:
        return None
    match = re.search(r"/(tt\d+)/", url)
    return match.group(1) if match else None


def load_existing_events(filepath):
    """Carrega eventos existentes do .ics, indexados pelo ID do IMDb."""
    existing = {}
    if not os.path.exists(filepath):
        return existing

    with open(filepath, encoding="utf-8") as f:
        content = f.read()

    try:
        cal = Calendar(content)
        for event in cal.events:
            imdb_id = imdb_id_from_url(event.url)
            if imdb_id:
                existing[imdb_id] = event
    except Exception as e:
        print(f"Aviso: não foi possível carregar eventos existentes: {e}")

    return existing


def build_event(title, title_id, release_date):
    event = Event()
    event.name = f"🎥 {title}"
    event.begin = release_date
    event.make_all_day()
    event.url = f"https://www.imdb.com/title/{title_id}/"
    return event


def merge_events(edges, existing_events):
    """
    Merge entre eventos da API e eventos existentes no .ics.

    Regras:
    - Eventos da API sempre entram (atualizados ou novos).
    - Eventos existentes que sumiram da API são mantidos se a data de
      lançamento ainda não passou há mais de KEEP_AFTER_RELEASE_DAYS dias.
    """
    today = date.today()
    cutoff = today - timedelta(days=KEEP_AFTER_RELEASE_DAYS)

    # Processar eventos vindos da API
    api_events = {}
    for edge in edges:
        node = edge.get("node", {})
        title = node.get("titleText", {}).get("text")
        release = node.get("releaseDate")
        title_id = node.get("id")

        if not (title and release and release.get("year") and release.get("month") and release.get("day")):
            continue

        try:
            release_date = date(release["year"], release["month"], release["day"])
            api_events[title_id] = build_event(title, title_id, release_date)
        except Exception as e:
            print(f"Erro ao processar '{title}':", e)

    # Eventos existentes que sumiram da API: manter se ainda dentro do prazo
    preserved = 0
    expired = 0
    for imdb_id, event in existing_events.items():
        if imdb_id in api_events:
            continue  # já está nos novos, será sobrescrito

        # Determinar a data do evento existente
        try:
            event_date = event.begin.date() if hasattr(event.begin, "date") else event.begin
        except Exception:
            continue

        if event_date >= cutoff:
            api_events[imdb_id] = event
            preserved += 1
        else:
            expired += 1

    print(f"Eventos da API: {len(api_events) - preserved}")
    print(f"Eventos preservados (fora da API, dentro do prazo): {preserved}")
    print(f"Eventos expirados (removidos): {expired}")

    return api_events


def main():
    filepath = "calendar.ics"

    existing_events = load_existing_events(filepath)
    print(f"Eventos existentes carregados: {len(existing_events)}")

    edges = fetch_events()
    if edges is None:
        print("Abortando: não foi possível buscar eventos da API.")
        return

    merged = merge_events(edges, existing_events)

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
