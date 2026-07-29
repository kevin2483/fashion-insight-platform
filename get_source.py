from selenium import webdriver
import time

print("🔍 크롬 브라우저를 띄우고 무신사 페이지를 분석합니다...")

# 크롬 브라우저 실행
driver = webdriver.Chrome()

# 방금 알려주신 최신 무신사 랭킹 주소 접속
url = "https://www.musinsa.com/main/musinsa/ranking?gf=A&storeCode=musinsa&sectionId=200&contentsId=&categoryCode=000&ageBand=AGE_BAND_ALL"
driver.get(url)

# 자바스크립트가 상품 목록을 다 그릴 때까지 5초 대기
print("⏳ 상품 데이터를 불러오는 중... (5초 대기)")
time.sleep(5) 

# 현재 로딩된 웹페이지의 전체 소스코드를 가져옴
html_source = driver.page_source

# 메모장 파일로 저장
file_name = "musinsa_source.txt"
with open(file_name, "w", encoding="utf-8") as f:
    f.write(html_source)

driver.quit()
print(f"✅ 완료! 현재 폴더에 '{file_name}' 파일이 저장되었습니다.")