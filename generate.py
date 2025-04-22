# generate.py
import requests
import json
from bs4 import BeautifulSoup
from ics import Calendar, Event
from dateparser import parse as parse_date
from datetime import datetime

URL = "https://www.imdb.com/pt/calendar/"

def get_imdb_calendar():
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    response = requests.get(URL, headers=headers)
    print("Status HTTP:", response.status_code)

    soup = BeautifulSoup(response.text, 'html.parser')
    script_tag = soup.find("script", {"id": "__NEXT_DATA__"})

    if not script_tag:
        print("Script com os dados não encontrado.")
        return None

    data = json.loads(script_tag.string)
    groups = data.get("props", {}).get("pageProps", {}).get("groups", [])

    calendar = Calendar()
    total_eventos = 0

    for group in groups:
        date_str = group.get("group")
        release_date = parse_date(date_str, languages=["pt"])
        if not release_date:
            continue

        entries = group.get("entries", [])
        for entry in entries:
            title = entry.get("titleText")
            release = entry.get("releaseDate")

            if title and release:
                event = Event()
                event.name = title
                event.begin = datetime.strptime(release, "%a, %d %b %Y %H:%M:%S %Z")
                event.url = f"https://www.imdb.com/title/{entry.get('id')}/"
                calendar.events.add(event)
                total_eventos += 1

    print(f"Total de eventos adicionados: {total_eventos}")
    return calendar

if __name__ == "__main__":
    calendar = get_imdb_calendar()
    if calendar:
        with open("calendar.ics", "w", encoding="utf-8") as f:
            f.writelines(calendar)
