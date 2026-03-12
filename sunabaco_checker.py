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
    r = requests.get(URL, timeout=10)
    r.encoding = r.apparent_encoding
    soup = BeautifulSoup(r.text, "html.parser")

    events = []
    # 1つずつのイベントカードを指す可能性が高い名前を順番に試します
    cards = soup.select(".elementor-post, article.post, .post-item")

    for c in cards:
        # aタグ（リンク）を探す
        link_tag = c.find("a")
        if not link_tag: continue

        url = link_tag.get("href", "")
        # 「#」で始まるものや、イベント詳細じゃないURL（カテゴリー一覧など）を除外
        if not url or url.startswith("#") or "category" in url or url == URL:
            continue

        if not url.startswith("http"):
            url = "https://sunabaco.com" + url

        # タイトルをしっかり取る
        title_tag = c.select_one(".elementor-post__title, h2, h3")
        title = title_tag.get_text(strip=True) if title_tag else link_tag.get_text(strip=True)

        # 重複チェック
        if not any(e['url'] == url for e in events):
            events.append({
                "title": title,
                "date": "確認中", 
                "url": url,
                "image": "" # 必要なら画像取得も追加
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
    print(f"メール送信テスト中: {event['title']}")
    
    # 送るデータをまとめる
    data = {
        "service_id": SERVICE_ID,
        "template_id": TEMPLATE_ID,
        "user_id": PUBLIC_KEY,  # ← 403エラー対策の重要ポイント！
        "template_params": {
            "title": event["title"],
            "date": event["date"],
            "url": event["url"],
            "image": event["image"]
        }
    }

    # 送信
    response = requests.post(
        "https://api.emailjs.com/api/v1.0/email/send",
        json=data
    )
    
    print("EmailJS status:", response.status_code)
    if response.status_code != 200:
        print("エラーの理由:", response.text) # 403の詳しい理由が表示されます

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
