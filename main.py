import requests
from bs4 import BeautifulSoup
import json
import os
import subprocess
import urllib.parse

URL = "https://sunabaco.com/event/"

# 環境変数から取得するようにするとセキュリティ的に安全です（GitHubのSettingsで設定可能）
SERVICE_ID = os.environ.get("EMAILJS_SERVICE_ID", "あなたのSERVICE_ID")
TEMPLATE_ID = os.environ.get("EMAILJS_TEMPLATE_ID", "あなたのTEMPLATE_ID")
PUBLIC_KEY = os.environ.get("EMAILJS_PUBLIC_KEY", "あなたのPUBLIC_KEY")
PRIVATE_KEY = os.environ.get("EMAILJS_PRIVATE_KEY", "") # 403が出るならこれも設定

def normalize_url(url):
    """URLの末尾スラッシュとパラメータを削除して統一する"""
    if not url: return ""
    parsed = urllib.parse.urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")

def get_events():
    headers = {'User-Agent': 'Mozilla/5.0'}
    r = requests.get(URL, timeout=10, headers=headers)
    r.encoding = r.apparent_encoding
    soup = BeautifulSoup(r.text, "html.parser")

    events = []
    # GAS版で成功した「eventCard」クラスを直接狙います
    cards = soup.select(".eventCard")

    processed_urls = set()

    for c in cards:
        link_tag = c.select_one("a")
        if not link_tag: continue

        # aタグのtitle属性にタイトルが入っている（GAS版の知見）
        title = link_tag.get("title", "").strip()
        url = normalize_url(link_tag.get("href", ""))
        
        if not url or url in processed_urls:
            continue
        processed_urls.add(url)

        # 画像の抽出
        img_tag = c.select_one("img")
        image_url = img_tag.get("src", "") if img_tag else ""
        if image_url:
            image_url = urllib.parse.quote(image_url, safe=':/%') # 日本語URL対策

        # 詳細情報の抽出 (eventCard__info)
        info_tag = c.select_one(".eventCard__info")
        details = info_tag.get_text(" ", strip=True) if info_tag else "詳細はページを確認"

        events.append({
            "title": title,
            "date": details, 
            "url": url,
            "image": image_url
        })

    return events

def load_old():
    if not os.path.exists("events.json"):
        return []
    try:
        with open("events.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            return [normalize_url(e["url"]) for e in data]
    except:
        return []

def send_email(event):
    print(f"メール送信中: {event['title']}")
    
    data = {
        "service_id": SERVICE_ID,
        "template_id": TEMPLATE_ID,
        "user_id": PUBLIC_KEY,
        "accessToken": PRIVATE_KEY, # 403エラーが出る場合はPrivate Key(API Key)を追加
        "template_params": {
            "title": event["title"],
            "date": event["date"],
            "url": event["url"],
            "image": event["image"] # Template側で <img src="{{image}}"> と設定
        }
    }

    response = requests.post(
        "https://api.emailjs.com/api/v1.0/email/send",
        json=data,
        headers={'Content-Type': 'application/json'}
    )
    
    if response.status_code == 200:
        print("✅ 送信成功")
    else:
        print(f"❌ 送信失敗 ({response.status_code}): {response.text}")

# --- main, save, push_to_github は元のロジックを継承 ---
# (main内の判定も normalize_url を通した old_urls と比較するようにしてください)
