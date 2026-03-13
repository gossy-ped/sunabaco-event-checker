import requests
from bs4 import BeautifulSoup
import json
import os
import urllib.parse

# --- 設定エリア ---
URL = "https://sunabaco.com/event/"

# GitHub Secretsから値を受け取る
SERVICE_ID = os.environ.get("EMAILJS_SERVICE_ID")
TEMPLATE_ID = os.environ.get("EMAILJS_TEMPLATE_ID")
PUBLIC_KEY = os.environ.get("EMAILJS_PUBLIC_KEY")
PRIVATE_KEY = os.environ.get("EMAILJS_PRIVATE_KEY", "") # 403エラーが出る場合のみ使用

def normalize_url(url):
    """URLの末尾スラッシュやパラメータを消して統一する"""
    if not url: return ""
    parsed = urllib.parse.urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")

def get_events():
    """サイトからイベント情報を抜き出す"""
    print(f"🔍 {URL} を確認中...")
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        r = requests.get(URL, timeout=15, headers=headers)
        r.encoding = r.apparent_encoding
        soup = BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        print(f"❌ サイトへのアクセスに失敗しました: {e}")
        return []

    events = []
    # GAS版で成功した「eventCard」クラスを狙い撃ち
    cards = soup.select(".eventCard")
    processed_urls = set()

    for c in cards:
        link_tag = c.select_one("a")
        if not link_tag: continue

        # URLの取得と正規化
        raw_url = link_tag.get("href", "")
        url = normalize_url(raw_url)
        
        # 今回の実行内での重複排除
        if not url or url in processed_urls:
            continue
        processed_urls.add(url)

        # タイトルの取得（title属性またはh3タグ）
        title = link_tag.get("title", "").strip()
        if not title:
            title_el = c.select_one("h3")
            title = title_el.get_text(strip=True) if title_el else "無題のイベント代"

        # 画像URLの取得とエンコード（日本語ファイル名対策）
        img_tag = c.select_one("img")
        image_url = img_tag.get("src", "") if img_tag else ""
        if image_url:
            # GASのencodeURIと同じ処理
            image_url = urllib.parse.quote(image_url, safe=':/%')

        # 詳細情報の取得
        info_tag = c.select_one(".eventCard__info")
        details = info_tag.get_text(" ", strip=True) if info_tag else "詳細はページを確認してください"

        events.append({
            "title": title,
            "date": details, 
            "url": url,
            "image": image_url
        })

    return events

def load_old_urls():
    """過去に通知したURLのリストを読み込む"""
    if not os.path.exists("events.json"):
        print("💡 履歴ファイル(events.json)が見つかりません。初回実行として進みます。")
        return []
    try:
        with open("events.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            # URLだけのリストにして返す
            return [normalize_url(e["url"]) for e in data]
    except Exception as e:
        print(f"⚠️ 履歴の読み込みに失敗しました: {e}")
        return []

def save_events(events):
    """今のイベント一覧を保存する"""
    try:
        with open("events.json", "w", encoding="utf-8") as f:
            json.dump(events, f, ensure_ascii=False, indent=2)
        print("✅ 履歴を events.json に保存しました。")
    except Exception as e:
        print(f"❌ 保存に失敗しました: {e}")

def send_email(event):
    """EmailJSを使ってメールを送る"""
    print(f"📨 メール送信中: {event['title']}")
    
    # 必須パラメータのチェック
    if not all([SERVICE_ID, TEMPLATE_ID, PUBLIC_KEY]):
        print("❌ エラー: EmailJSのIDまたはKeyが設定されていません。Secretsを確認してください。")
        return

    data = {
        "service_id": SERVICE_ID,
        "template_id": TEMPLATE_ID,
        "user_id": PUBLIC_KEY,
        "template_params": {
            "title": event["title"],
            "date": event["date"],
            "url": event["url"],
            "image": event["image"]
        }
    }
    
    # 403エラー対策でaccessTokenが必要な場合
    if PRIVATE_KEY:
        data["accessToken"] = PRIVATE_KEY

    try:
        response = requests.post(
            "https://api.emailjs.com/api/v1.0/email/send",
            json=data,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        if response.status_code == 200:
            print(f"  └ ✅ 送信成功！")
        else:
            print(f"  └ ❌ 送信失敗 ({response.status_code}): {response.text}")
    except Exception as e:
        print(f"  └ ❌ 送信中にエラーが発生しました: {e}")

def main():
    print("=== SUNABACO イベントチェッカー 開始 ===")
    
    # 1. サイトから取得
    current_events = get_events()
    print(f"現在のサイト上のイベント数: {len(current_events)} 件")

    # 2. 過去の履歴と比較
    old_urls = load_old_urls()
    
    new_events = []
    for e in current_events:
        if e["url"] not in old_urls:
            new_events.append(e)

    # 3. 通知の判定
    if new_events:
        print(f"🔥 新着が {len(new_events)} 件あります！")
        for e in new_events:
            send_email(e)
    else:
        # --- ここを修正：新着がない時用のメールを送る ---
        print("😴 新着イベントはありません。生存確認メールを送ります。")
        nothing_event = {
            "title": "【定期報告】新着イベントはありませんでした",
            "date": "サイトは正常にチェックされました。",
            "url": URL,
            "image": ""
        }
        send_email(nothing_event)
        # ------------------------------------------

    # 4. 履歴を更新
    save_events(current_events)
    print("=== 処理終了 ===")

if __name__ == "__main__":
    main()
