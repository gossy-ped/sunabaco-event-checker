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

    for a in soup.find_all("a", href=True):

        title = a.get_text(strip=True)
        link = a["href"]

        if "event" in link and len(title) > 5:

            if not link.startswith("http"):
                link = "https://sunabaco.com" + link

            events.append({
                "title": title,
                "url": link
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


def send_email(message):

    requests.post(
        "https://api.emailjs.com/api/v1.0/email/send",
        json={
            "service_id": SERVICE_ID,
            "template_id": TEMPLATE_ID,
            "user_id": PUBLIC_KEY,
            "template_params": {
                "message": message
            }
        }
    )


def commit_and_push():

    subprocess.run(["git", "config", "--global", "user.name", "github-actions"])
    subprocess.run(["git", "config", "--global", "user.email", "actions@github.com"])

    subprocess.run(["git", "add", "events.json"])
    subprocess.run(["git", "commit", "-m", "update events"])
    subprocess.run(["git", "push"])


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

            message = f"{e['title']}\n{e['url']}"

            send_email(message)

    save(events)

    commit_and_push()


if __name__ == "__main__":
    main()
