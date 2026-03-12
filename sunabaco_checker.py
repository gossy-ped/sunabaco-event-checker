import requests
from bs4 import BeautifulSoup
import json
import os
import subprocess

URL = "https://sunabaco.com/event/"

# ここは自分の値に書き換えてください
SERVICE_ID = "service_9u0xdoa"
TEMPLATE_ID = "template_ax2xf9c"
PUBLIC_KEY = "nFppopYuqo7kDqjlp"

def get_events():
    """イベント一覧を取得する関数"""
    try:
        r = requests.get(URL, timeout=10)
        r.encoding = r.apparent_encoding
        soup = BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        print(f"サイトが開けませんでした: {e}")
        return []

    events = []
    
    # SUNABACOのサイト構造（WordPress/Elementor）に合わせた「箱」の探し方
    # 複数のパターンで探すことで、1つだけでなく全部を拾えるようにします
    cards = soup.select(".elementor-post, article, .post-item, .card")

    for c in cards:
        # 1. リンク(URL)を探す
        # #で始まるタグ用リンクを除外し、/event/ を含む本物のリンクだけを探す
        link_tag = None
        for a in c.find_all("a"):
            href = a.get("href", "")
            if href and "/event/" in href and not href.startswith("#") and not href.endswith("/event/"):
                link_tag = a
                break
        
        if not link_tag:
            continue

        url = link_tag["href"]
        if not url.startswith("http"):
            url = "https://sunabaco.com" + url

        # 2. タイトルを探す
        # リンクの中の文字か、h2/h3タグから取得する
        title = link_tag.get_text(strip=True)
        if not title:
            t_tag = c.find(["h2", "h3"])
            title = t_tag.get_text(strip=True) if t_tag else "無題のイベント"

        # 3. 画像(image)を探す
        img_tag = c.find("img")
        image = img_tag.get("src", "") if img_tag else ""

        # 4. 日付(date)を探す
        date_tag = c.find("time")
        date = date_tag.get_text(strip=True) if date_tag else "日付なし"

        # 重複（同じURL）をリストに入れないようにする
        if not any(e['url'] == url for e in events):
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
    try:
        with open("events.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save(events):
    with open("events.json", "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)

def send_email(event):
    print(f"メール送信中: {event['title']}")
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

def push_to_github():
    try:
        subprocess.run(["git", "config", "--global", "user.name", "github-actions"], check=True)
        subprocess.run(["git", "config", "--global", "user.email", "actions@github.com"], check=True)
        subprocess.run(["git", "add", "events.json"], check=True)
        # 変更がない場合にエラーにならないよう check=False に設定
        subprocess.run(["git", "commit", "-m", "update events"], check=False)
        subprocess.run(["git", "push"], check=True)
    except Exception as e:
        print(f"GitHubへの保存に失敗しました: {e}")

def main():
    # 1. サイトから今のイベントを全部持ってくる
    events = get_events()
    print(f"合計 {len(events)} 個のイベントを見つけました。")

    # 2. 前回のデータを読み込む
    old = load_old()
    old_urls = [e["url"] for e in old]

    # 3. 「新しく増えたもの」だけを探す
    new_events = []
    for e in events:
        if e["url"] not in old_urls:
            new_events.append(e)

    # 4. 新しいのがあればメールを送る
    if new_events:
        print(f"新着 {len(new_events)} 件！通知を送ります。")
        for e in new_events:
            send_email(e)
    else:
        print("新しいイベントはありませんでした。")

    # 5. 最新の状態を保存してGitHubにアップする
    save(events)
    push_to_github()

if __name__ == "__main__":
    main()
