from datetime import datetime
import json
import time
from playwright.sync_api import sync_playwright
from zoneinfo import ZoneInfo

# 日本時間のタイムゾーン定義
JST = ZoneInfo("Asia/Tokyo")


def load_config():
  """config.jsonを読み込む"""
  with open("config.json", "r", encoding="utf-8") as f:
    return json.load(f)


def check_facility_availability(page, facility_name, url, target_days):
  """動的カレンダーから空室状況（○、△、または各種ステータス）を確実にかぎ分ける"""
  print(
      f"[{datetime.now(JST).strftime('%Y-%m-%d %H:%M:%S')}]"
      f" チェック中: {facility_name}",
      flush=True,
  )
  available_dates = []

  try:
    page.goto(url, timeout=60000)
    page.wait_for_selector(".c-calendar", timeout=15000)

    # 念のためページの読み込み安定を少し待つ
    page.wait_for_timeout(2000)

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
          check_date = datetime.strptime(date_str, "%Y-%m-%d").date()

          # 日本時間の今日の日付を取得
          today = datetime.now(JST).date()
          delta_days = (check_date - today).days

          if 0 <= delta_days <= target_days:
            cell_text = cell.inner_text()
            cell_html = cell.inner_html()

            # 空室判定の条件を広く網羅（クラス名、テキストの○/△など）
            has_circle = (
                "circle" in cell_html.lower()
                or "○" in cell_text
                or "icon-circle" in cell_html
            )
            has_triangle = (
                "triangle" in cell_html.lower()
                or "△" in cell_text
                or "icon-triangle" in cell_html
            )

            # もし「×」や「満室」などの文字が明示されていなければ、空きマークの有無を判定
            is_booked_out = (
                "×" in cell_text or "満室" in cell_text or "受付終了" in cell_text
            )

            if (has_circle or has_triangle) and not is_booked_out:
              available_dates.append(date_str)
        except Exception:
          continue

  except Exception as e:
    print(f"エラー発生 ({facility_name}): {e}", flush=True)

  return sorted(list(set(available_dates)))


def format_date_str(date_str):
  """YYYY-MM-DD を M/D(曜日) に変換する"""
  try:
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    weekdays = ["月", "火", "水", "木", "金", "土", "日"]
    w = weekdays[dt.weekday()]
    return f"{dt.month}/{dt.day}({w})"
  except Exception:
    return date_str


def save_results_as_html(results, filename, config_facilities):
  """日付ありを優先表示し、月/日(曜日)形式でコンパクトなHTMLとして保存する"""
  url_map = {f["name"]: f["url"] for f in config_facilities}

  # 空室がある施設を上位にソートする
  sorted_results = sorted(
      results.items(), key=lambda item: (len(item[1]) > 0), reverse=True
  )

  # 日本時間の現在時刻を取得
  update_time_str = datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")

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
            padding: 20px;
            background-color: #ffffff;
            color: #111111;
            line-height: 1.5;
        }}
        h1 {{
            font-size: 1.4rem;
            font-weight: 600;
            margin-bottom: 4px;
            border-bottom: 2px solid #333333;
            padding-bottom: 8px;
        }}
        .meta {{
            font-size: 0.85rem;
            color: #666666;
            margin-bottom: 24px;
        }}
        .facility-block {{
            margin-bottom: 20px;
            border-bottom: 1px solid #e0e0e0;
            padding-bottom: 16px;
        }}
        .facility-name {{
            font-size: 1.05rem;
            font-weight: 600;
            margin-bottom: 10px;
        }}
        .facility-name a {{
            color: #000000;
            text-decoration: none;
            border-bottom: 1px solid #666666;
        }}
        .facility-name a:hover {{
            border-color: #000000;
        }}
        .date-list {{
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            list-style: none;
            padding: 0;
            margin: 0;
        }}
        .date-badge {{
            background-color: #f0f0f0;
            color: #111111;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.9rem;
            font-weight: 500;
        }}
        .no-room {{
            color: #888888;
            font-size: 0.9rem;
        }}
    </style>
</head>
<body>
    <h1>界タビ20s 空き状況</h1>
    <div class="meta">更新: {update_time_str}</div>
"""

  for facility_name, dates in sorted_results:
    facility_url = url_map.get(
        facility_name, "https://www.hoshinoresorts.com/sp/kaitabi20s/"
    )
    html_content += f"""
    <div class="facility-block">
        <div class="facility-name">
            <a href="{facility_url}" target="_blank">{facility_name} ↗</a>
        </div>
"""
    if dates:
      html_content += '        <ul class="date-list">\n'
      for d in dates:
        formatted_d = format_date_str(d)
        html_content += f'            <li class="date-badge">{formatted_d}</li>\n'
      html_content += "        </ul>\n"
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
  print(
      "界タビ20s 空き状況チェッカー（Playwright版）を開始します。", flush=True
  )
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
            "--disable-setuid-sandbox",
        ],
    )
    context = browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            " (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1280, "height": 800},
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