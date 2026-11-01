import json
import time
from datetime import datetime
from playwright.sync_api import sync_playwright

def load_config():
    """config.jsonを読み込む"""
    with open("config.json", "r", encoding="utf-8") as f:
        return json.load(f)

def check_facility_availability(page, facility_name, url, target_days):
    """
    Playwrightを使用して動的カレンダーから空き状況（● または ▲）を正確に取得する
    """
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] チェック中: {facility_name}", flush=True)
    available_dates = []
    
    try:
        page.goto(url, timeout=60000)
        page.wait_for_selector(".c-calendar", timeout=15000)
        
        calendars = page.locator(".c-calendar").all()
        
        for cal in calendars:
            year_text = cal.locator(".header").inner_text()
            if "年" in year_text and "月" in year_text:
                year_str = year_text.split("年")[0].strip()
                month_str = year_text.split("年")[1].split("月")[0].strip()
                target_year = int(year_str)
                target_month = int(month_str)
            else:
                continue

            cells = cal.locator(".content > div").all()
            for cell in cells:
                if cell.locator(".date").count() == 0:
                    continue
                
                try:
                    day_text = cell.locator(".date").inner_text().strip()
                    if not day_text.isdigit():
                        continue
                    day = int(day_text)
                    
                    date_str = f"{target_year}-{target_month:02d}-{day:02d}"
                    check_date = datetime.strptime(date_str, "%Y-%m-%d")
                    
                    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                    delta_days = (check_date - today).days
                    
                    if 0 <= delta_days <= target_days:
                        has_triangle = cell.locator(".triangle").count() > 0
                        has_circle = cell.locator(".circle").count() > 0
                        
                        if has_triangle or has_circle:
                            available_dates.append(date_str)
                except Exception:
                    continue
                    
    except Exception as e:
        print(f"エラー発生 ({facility_name}): {e}", flush=True)
        
    return sorted(list(set(available_dates)))

def save_results_as_html(results, filename, config_facilities):
    """シンプル・白黒グレーのコンパクトなHTMLとして保存する"""
    url_map = {f["name"]: f["url"] for f in config_facilities}
    
    html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>界タビ20s 空き状況</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            max-width: 650px;
            margin: 0 auto;
            padding: 16px;
            background-color: #ffffff;
            color: #111111;
            line-height: 1.4;
        }}
        h1 {{
            font-size: 1.25rem;
            font-weight: 600;
            margin-bottom: 4px;
            border-bottom: 1px solid #e0e0e0;
            padding-bottom: 8px;
        }}
        .meta {{
            font-size: 0.75rem;
            color: #666666;
            margin-bottom: 24px;
        }}
        .facility-block {{
            margin-bottom: 20px;
            border-bottom: 1px solid #eeeeee;
            padding-bottom: 16px;
        }}
        .facility-name {{
            font-size: 0.95rem;
            font-weight: 600;
            margin-bottom: 8px;
        }}
        .facility-name a {{
            color: #000000;
            text-decoration: none;
            border-bottom: 1px solid #999999;
        }}
        .facility-name a:hover {{
            border-color: #000000;
        }}
        .date-list {{
            display: flex;
            flex-wrap: wrap;
            gap: 4px;
            list-style: none;
            padding: 0;
            margin: 0;
        }}
        .date-badge {{
            background-color: #f4f4f4;
            color: #222222;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 0.8rem;
            font-family: monospace;
        }}
        .no-room {{
            color: #888888;
            font-size: 0.8rem;
        }}
    </style>
</head>
<body>
    <h1>界タビ20s 空き状況</h1>
    <div class="meta">更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
"""

    for facility_name, dates in results.items():
        facility_url = url_map.get(facility_name, "https://www.hoshinoresorts.com/sp/kaitabi20s/")
        html_content += f"""
    <div class="facility-block">
        <div class="facility-name">
            <a href="{facility_url}" target="_blank">{facility_name}↗</a>
        </div>
"""
        if dates:
            html_content += '        <ul class="date-list">\n'
            for d in dates:
                html_content += f'            <li class="date-badge">{d}</li>\n'
            html_content += '        </ul>\n'
        else:
            html_content += '        <div class="no-room">空室なし</div>\n'
            
        html_content += "    </div>\n"

    html_content += """
</body>
</html>
"""

    with open(filename, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"結果をHTMLファイル ({filename}) に保存しました。", flush=True)

def main():
    print("界タビ20s 空き状況チェッカー（Playwright版）を開始します。", flush=True)
    config = load_config()
    target_days = config.get("target_days", 44)
    output_file = "index.html"
    
    all_results = {}
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox"
            ]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = context.new_page()
        
        for facility in config["facilities"]:
            name = facility["name"]
            url = facility["url"]
            
            dates = check_facility_availability(page, name, url, target_days)
            all_results[name] = dates
            
            time.sleep(2)
            
        browser.close()
        
    save_results_as_html(all_results, output_file, config["facilities"])
    print("すべての処理が完了しました。", flush=True)

if __name__ == "__main__":
    main()