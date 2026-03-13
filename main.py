import requests
import json
import os
import re
import urllib.parse

# --- 設定エリア ---
URL = "https://sunabaco.com/event/"

# GitHub Secretsから取得
SERVICE_ID = os.environ.get("EMAILJS_SERVICE_ID")
TEMPLATE_ID = os.environ.get("EMAILJS_TEMPLATE_ID")
PUBLIC_KEY = os.environ.get("EMAILJS_PUBLIC_KEY")
PRIVATE_KEY = os.environ.get("EMAILJS_PRIVATE_KEY", "")

def normalize_url(url):
    """URLを正規化（?以降を削除し、末尾のスラッシュを消す）"""
    if not url: return ""
    url = url.split('?')[0]
    return url.rstrip("/")

def extract_match(content, regex):
    """正規表現で抽出する補助関数"""
    match = re.search(regex, content)
    return match.group(1).strip() if match else ""

def get_events():
    """GASと同じロジック（正規表現）でイベントを抽出"""
    print(f"🔍 {URL} をスキャン中...")
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        r = requests.get(URL, timeout=15, headers=headers)
        html = r.text
    except Exception as e:
        print(f"❌ 通信エラー: {e}")
        return []

    # GASと同じ正規表現で <a>タグをカード単位として抽出
    # href="https://sunabaco.com/event/..." を含むタグを探す
    all_matches = re.findall(r'<a href="https://sunabaco\.com/event/[^"]+"[\s\S]*?</a>', html)
    print(f"カード抽出数: {len(all_matches)}件")

    events = []
    processed_urls = set()

    for card in all_matches:
        # href と title を抽出
        link_match = re.search(r'href="([^"]+)"\s*title="([^"]+)"', card)
        if not link_match:
            continue

        url = normalize_url(link_match.group(1))
        title = link_match.group(2).replace('&amp;', '&').replace('&quot;', '"')

        # 同一実行内での重複をスキップ
        if url in processed_urls:
            continue
        processed_urls.add(url)

        # 画像URLの抽出
        image_url = extract_match(card, r'src="([^"]+)"')
        if image_url:
            image_url = urllib.parse.quote(image_url, safe=':/%')

        # 詳細の抽出 (タグを削除してテキストのみに)
        details_raw = extract_match(card, r'class="eventCard__info">([\s\S]*?)</div>')
        details = re.sub(r'<[^>]+>', ' ', details_raw).strip()

        events.append({
            "title": title,
            "url": url,
            "image": image_url,
            "date": details
        })

    return events

def load_old_urls():
    """履歴ファイルから通知済みURLを取得"""
    if not os.path.exists("events.json"):
        return []
    try:
        with open("events.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            return [normalize_url(e["url"]) for e in data]
    except:
        return []

def send_email(event):
    """EmailJSで送信"""
    print(f"📨 送信中: {event['title']}")
    data = {
        "service_id": SERVICE_ID,
        "template_id": TEMPLATE_ID,
        "user_id": PUBLIC_KEY,
        "template_params": {
            "title": event["title"],
            "url": event["url"],
            "image": event["image"],
            "date": event["date"]
        }
    }
    if PRIVATE_KEY:
        data["accessToken"] = PRIVATE_KEY

    res = requests.post("https://api.emailjs.com/api/v1.0/email/send", json=data)
    print(f"結果: {res.status_code}")

def main():
    events = get_events()
    old_urls = load_old_urls()
    
    new_events = [e for e in events if e["url"] not in old_urls]

    if new_events:
        print(f"🔥 新着 {len(new_events)}件！")
        for e in new_events:
            send_email(e)
    else:
        print("😴 新着なし")

    # 履歴を更新
    with open("events.json", "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
