import requests
from bs4 import BeautifulSoup
import json
import os

URL = "https://sunabaco.com/event/"

IFTTT_URL = "ここにあなたのWebhookURL"


def get_events():

    r = requests.get(URL)

    soup = BeautifulSoup(r.text, "html.parser")

    events = []

    for h3 in soup.find_all("h3"):

        title = h3.get_text(strip=True)

        if title:
            events.append(title)

    return events


def load_old():

    if not os.path.exists("events.json"):
        return []

    with open("events.json") as f:
        return json.load(f)


def save(events):

    with open("events.json", "w") as f:
        json.dump(events, f, ensure_ascii=False)


def notify(event):

    requests.post(
        IFTTT_URL,
        json={"value1": event}
    )


def main():

    events = get_events()

    old = load_old()

    new_events = list(set(events) - set(old))

    if new_events:

        for e in new_events:

            notify(e)

    save(events)


if __name__ == "__main__":

    main()
