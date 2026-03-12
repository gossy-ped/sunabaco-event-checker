import requests
from bs4 import BeautifulSoup
import json
import os
import subprocess

URL = "https://sunabaco.com/event/"

SERVICE_ID = "service_9u0xdoa"
TEMPLATE_ID = "template_ax2xf9c"
PUBLIC_KEY = "nFppopYuqo7kDqjlp"


def get_events():

    r = requests.get(URL)
    soup = BeautifulSoup(r.text, "html.parser")

    events = []

    cards = soup.find_all("article")

    for c in cards:

        link = c.find("a")

        if not link:
            continue

        url = link["href"]

        if not url.startswith("http"):
            url = "https://sunabaco.com" + url

        title = link.get_text(strip=True)

        img = c.find("img")

        image = img["src"] if img else ""

        date_tag = c.find("time")

        date = date_tag.get_text(strip=True) if date_tag else ""

        events.append({
            "title": title,
            "date": date,
            "url": url,
            "image": image
        })

    return events


def load_old():

    if not os.path.exists("events.json"):
        return []

    with open("events.json") as f:
        return json.load(f)


def save(events):

    with open("events.json", "w") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)


def send_email(event):

    requests.post(
        "https://api.emailjs.com/api/v1.0/email/send",
        json={
            "service_id": SERVICE_ID,
            "template_id": TEMPLATE_ID,
            "public_key": PUBLIC_KEY,
            "template_params": {
                "title": event["title"],
                "date": event["date"],
                "url": event["url"],
                "image": event["image"]
            }
        }
    )
    print("EmailJS status:", response.status_code)
    print(response.text)

def push_to_github():

    subprocess.run(["git","config","--global","user.name","github-actions"])
    subprocess.run(["git","config","--global","user.email","actions@github.com"])

    subprocess.run(["git","add","events.json"])

    subprocess.run(["git","commit","-m","update events"], check=False)

    subprocess.run(["git","push"])


def main():

    events = get_events()

    old = load_old()

    old_urls = [e["url"] for e in old]

    new_events = []

    for e in events:
        if e["url"] not in old_urls:
            new_events.append(e)

    if new_events:

        for e in new_events:
            send_email(e)

    save(events)

    push_to_github()


if __name__ == "__main__":
    main()
