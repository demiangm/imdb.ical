import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from ics import Calendar, Event

URL = "https://www.imdb.com/calendar/?region=BR&type=MOVIE"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
}

def extract_data_from_next_script(html):
    soup = BeautifulSoup(html, "html.parser")
    script_tag = soup.find("script", id="__NEXT_DATA__")
    if script_tag:
        return json.loads(script_tag.string)
    return None

def parse_events(data):
    calendar = Calendar()
    total_eventos = 0

    try:
        groups = data["props"]["pageProps"]["groups"]
        for group in groups:
            entries = group.get("entries", [])
            for entry in entries:
                title = entry.get("titleText")
                release = entry.get("releaseDate")
                if title and release:
                    event = Event()
                    event.name = title

                    # Parse date and make all-day
                    release_date = datetime.strptime(release, "%a, %d %b %Y %H:%M:%S %Z").date()
                    event.begin = release_date
                    event.make_all_day()

                    event.url = f"https://www.imdb.com/title/{entry.get('id')}/"
                    calendar.events.add(event)
                    total_eventos += 1
    except Exception as e:
        print("Erro ao processar os dados:", e)

    return calendar, total_eventos

def main():
    response = requests.get(URL, headers=HEADERS)
    print("Status HTTP:", response.status_code)

    if response.status_code == 200:
        html = response.text
        with open("dump.html", "w", encoding="utf-8") as f:
            f.write(html)

        data = extract_data_from_next_script(html)
        if data:
            calendar, total_eventos = parse_events(data)
            with open("calendar.ics", "w", encoding="utf-8") as f:
                f.writelines(calendar)
            print(f"Total de eventos adicionados: {total_eventos}")
        else:
            print("Não foi possível extrair os dados JSON.")
    else:
        print("Falha ao acessar a página.")

if __name__ == "__main__":
    main()
