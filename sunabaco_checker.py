import requests
from bs4 import BeautifulSoup
import json
import os
import subprocess

URL = "https://sunabaco.com/event/"

SERVICE_ID = "service_9u0xdoa"
TEMPLATE_ID = "template_ax2xf9c"
PUBLIC_KEY = "public_nFppopYuqo7kDqjlp"


def get_events():
    r = requests.get(URL)
    r.encoding = r.apparent_encoding
    soup = BeautifulSoup(r.text, "html.parser")

    events = []
    # ここは左端を揃える
    cards = soup.select("article, .post-item, .card, .card-news") 

    for c in cards:
        # ここから下は for の中なので1段右にズラす
        links = c.find_all("a")
        link_tag = None
        
        for l in links:
            href = l.get("href", "")
            # #で始まるリンクや、空っぽのリンクは飛ばす
            if href and not href.startswith("#") and "/event/" in href:
                link_tag = l
                break
        
        if not link_tag:
            continue

        url = link_tag["href"]
        if not url.startswith("http"):
            url = "https://sunabaco.com" + url

        # タイトルを探す
        title = link_tag.get_text(strip=True)
        if not title:
            t_tag = c.find(["h2", "h3"])
            title = t_tag.get_text(strip=True) if t_tag else "無題のイベント"
        # 3. 日付を探す
        date_tag = c.find("time")
        date = date_tag.get_text(strip=True) if date_tag else "日付なし"

        # 4. 画像（image）を準備する
        img_tag = c.find("img")
        if img_tag:
            image = img_tag.get("src", "") # 画像があればそのURLを入れる
        else:
            image = "" # 画像がなければ空っぽにする
            
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

    response = requests.post(
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
