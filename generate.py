# generate.py
import requests
from bs4 import BeautifulSoup
from ics import Calendar, Event
from datetime import datetime
from urllib.parse import urljoin
import locale

locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')

URL = "https://www.imdb.com/pt/calendar/?ref_=nv_mv_cal"
BASE = "https://www.imdb.com"

def get_imdb_calendar():
    response = requests.get(URL)
    soup = BeautifulSoup(response.text, 'html.parser')
    calendar = Calendar()

    for date_header in soup.find_all('h4'):
        date_text = date_header.text.strip()
        try:
            release_date = datetime.strptime(date_text, "%d de %B de %Y")
        except ValueError:
            continue

        ul = date_header.find_next_sibling('ul')
        if ul:
            for li in ul.find_all('li'):
                a = li.find('a')
                if a:
                    event = Event()
                    event.name = a.text
                    event.begin = release_date
                    event.url = urljoin(BASE, a['href'])
                    calendar.events.add(event)

    return calendar

if __name__ == "__main__":
    with open("calendar.ics", "w", encoding="utf-8") as f:
        f.writelines(get_imdb_calendar())
