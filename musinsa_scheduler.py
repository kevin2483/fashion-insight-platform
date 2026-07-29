"""
무신사 랭킹 자동 크롤러 (스케줄러 버전)
- 매일 오전 10시에 자동 실행
- 날짜 컬럼 자동 추가 후 CSV에 누적 저장
- 실행: python musinsa_scheduler.py
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import pandas as pd
import schedule
import time
import os
from datetime import datetime

SAVE_FILE = "musinsa_ranking_data.csv"
URL = "https://www.musinsa.com/main/musinsa/ranking?gf=A&storeCode=musinsa&sectionId=200&contentsId=&categoryCode=000&ageBand=AGE_BAND_ALL"


def crawl_musinsa():
    today = datetime.today().strftime("%Y-%m-%d")
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 크롤링 시작 - {today}")

    # ── 1. Selenium으로 페이지 로드 ──────────────────────────
    options = Options()
    options.add_argument("--headless")           # 창 없이 백그라운드 실행
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

    try:
        driver = webdriver.Chrome(options=options)
        driver.get(URL)
        print("⏳ 페이지 로딩 대기 중... (7초)")
        time.sleep(7)
        html = driver.page_source
        driver.quit()
    except Exception as e:
        print(f"❌ 브라우저 오류: {e}")
        return

    # ── 2. BeautifulSoup 파싱 ────────────────────────────────
    soup = BeautifulSoup(html, "html.parser")
    items = soup.select("a.gtm-select-item")

    data_list = []
    seen_ids = set()

    for item in items:
        title_p = item.find("p")
        if not title_p:
            continue

        product_id = item.get("data-item-id", "0")
        if product_id in seen_ids:
            continue
        seen_ids.add(product_id)

        data_list.append({
            "date":           today,                                      # ← 날짜 컬럼 추가
            "rank":           int(item.get("data-item-list-index", 0)),
            "product_id":     product_id,
            "brand_name":     item.get("data-item-brand", ""),
            "product_name":   title_p.text.strip(),
            "original_price": int(item.get("data-original-price", 0)),
            "discount_price": int(item.get("data-price", 0)),
            "discount_rate":  int(item.get("data-discount-rate", 0)),
        })

    if not data_list:
        print("❌ 상품을 찾지 못했습니다. HTML 구조가 바뀌었을 수 있어요.")
        return

    df_new = pd.DataFrame(data_list).sort_values("rank").reset_index(drop=True)

    # ── 3. 기존 CSV에 누적 저장 (중복 날짜 방지) ─────────────
    if os.path.exists(SAVE_FILE):
        df_existing = pd.read_csv(SAVE_FILE, dtype=str)

        # 오늘 날짜 데이터가 이미 있으면 덮어쓰기
        df_existing = df_existing[df_existing["date"] != today]
        df_combined = pd.concat([df_existing, df_new], ignore_index=True)
    else:
        df_combined = df_new

    df_combined.to_csv(SAVE_FILE, index=False, encoding="utf-8-sig")

    print(f"✅ {today} 데이터 {len(df_new)}개 저장 완료!")
    print(f"   누적 데이터: 총 {len(df_combined)}행 / {df_combined['date'].nunique()}일치")
    print(df_new[["rank", "brand_name", "discount_rate"]].head())


# ── 스케줄 설정: 매일 오전 10:00 실행 ───────────────────────
schedule.every().day.at("10:00").do(crawl_musinsa)

if __name__ == "__main__":
    print("=" * 50)
    print("무신사 랭킹 자동 크롤러 시작")
    print(f"스케줄: 매일 오전 10:00 자동 실행")
    print(f"저장 파일: {SAVE_FILE}")
    print("=" * 50)

    # 시작하자마자 1회 즉시 실행
    print("\n▶ 지금 즉시 1회 실행합니다...")
    crawl_musinsa()

    print("\n⏰ 스케줄러 대기 중... (종료: Ctrl+C)")
    while True:
        schedule.run_pending()
        time.sleep(60)   # 1분마다 스케줄 체크