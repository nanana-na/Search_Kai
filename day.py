from datetime import datetime, timedelta

def check_reservations():
    # 1. 複数の指定した宿泊日（ここに好きな日付をいくつでも追加できます）
    target_dates = [
        "2026-12-14",
        "2026-12-15",
        "2027-01-10"
    ]
    
    print("=== 【1】指定した複数の宿泊日に対する予約解禁日（44日前） ===")
    for date_str in target_dates:
        stay_date = datetime.strptime(date_str, "%Y-%m-%d")
        reservation_date = stay_date - timedelta(days=44)
        print(f"・宿泊日: {stay_date.strftime('%Y年%m月%d日')}"
              f"  -> 予約解禁日: {reservation_date.strftime('%Y年%m月%d日')} 0:00（＝前夜の24:00）")

    print("\n=== 【2】本日の深夜24時（次の日）の判定と予約可能日 ===")
    
    # 現在の時刻を取得
    now = datetime.now()
    # 本日の深夜24:00 ＝ 次の日（明日）の 0:00
    tomorrow = now.date() + timedelta(days=1)
    
    print(f"・現在時刻: {now.strftime('%Y年%m月%d日 %H:%M:%S')}")
    print(f"・本日の深夜24:00 ＝ 【 {tomorrow.strftime('%Y年%m月%d日')} 0:00 】")
    
    # 今夜24:00（明日0:00）に解禁される宿泊日（＝明日から44日後）
    bookable_date = datetime(tomorrow.year, tomorrow.month, tomorrow.day) + timedelta(days=44)
    print(f"  -> 今夜の24:00にスタンバイして新たに予約できる宿泊日: 【 {bookable_date.strftime('%Y年%m月%d日')} 】の宿泊")

if __name__ == "__main__":
    check_reservations()