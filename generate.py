# generate.py
import requests
from bs4 import BeautifulSoup
from ics import Calendar, Event
from urllib.parse import urljoin
from dateparser import parse as parse_date

URL = "https://www.imdb.com/pt/calendar/"
BASE = "https://www.imdb.com"

def get_imdb_calendar():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
    response = requests.get(URL, headers=headers)
    print(f"Status HTTP: {response.status_code}")

    # Salva o HTML retornado para debug
    with open("dump.html", "w", encoding="utf-8") as f:
        f.write(response.text)

    soup = BeautifulSoup(response.text, 'html.parser')
    calendar = Calendar()
    eventos = 0

    for date_header in soup.find_all('h4'):
        date_text = date_header.get_text(strip=True)
        release_date = parse_date(date_text, languages=["pt"])
        print(f"Encontrou data: {date_text} → {release_date}")
        if not release_date:
            continue

        ul = date_header.find_next_sibling('ul')
        if ul:
            for li in ul.find_all('li'):
                a = li.find('a', href=True)
                if a and '/title/' in a['href']:
                    event = Event()
                    event.name = a.get_text(strip=True)
                    event.begin = release_date
                    event.url = urljoin(BASE, a['href'])
                    calendar.events.add(event)
                    eventos += 1
                    print(f"  ↳ Evento: {event.name}")

    print(f"Total de eventos adicionados: {eventos}")
    return calendar

if __name__ == "__main__":
    cal = get_imdb_calendar()
    print(f"Total de eventos: {len(cal.events)}")
    with open("calendar.ics", "w", encoding="utf-8") as f:
        f.writelines(cal)
