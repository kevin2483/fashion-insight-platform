import requests
import pandas as pd

def get_korean_holidays():
    print("🌐 공공데이터포털(한국천문연구원) API 호출 시작...")
    

    import os
    my_api_key = os.environ["HOLIDAY_API_KEY"]  # 환경변수에서 로드
    
    #분석 기준 연도 (2024년)
    year = "2024"
    
    #공공데이터포털 API 요청 주소 
    url = f"http://apis.data.go.kr/B090041/openapi/service/SpcdeInfoService/getRestDeInfo?solYear={year}&ServiceKey={my_api_key}&_type=json&numOfRows=100"
    
    try:
        res = requests.get(url)
        res.raise_for_status() # 에러 발생 시 멈춤
        
        #JSON 데이터 파싱
        json_data = res.json()
        
        #데이터가 정상적으로 들어왔는지 확인
        items = json_data['response']['body']['items']['item']
        print(f"✅ API 호출 성공! 총 {len(items)}개의 공휴일 데이터를 찾았습니다.")
        
        holiday_list = []
        for item in items:
            
            raw_date = str(item['locdate'])
            formatted_date = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:]}"
            
            holiday_list.append({
                "date": formatted_date,
                "holiday_name": item['dateName'],
                "is_holiday": item['isHoliday']
            })
            
        #Pandas 데이터프레임 변환
        df = pd.DataFrame(holiday_list)
        
        print("\n[데이터 미리보기]")
        print(df.head())
        
        #CSV 저장 (CASE 4 파이프라인 제출용)
        file_name = "holiday_api_data.csv"
        df.to_csv(file_name, index=False, encoding="utf-8-sig")
        print(f"\n💾 성공적으로 '{file_name}' 파일이 저장되었습니다")
        
    except Exception as e:
        print(f"에러가 발생했습니다: {e}")
        print("API 키를 제대로 넣었는지 확인하거나, 발급 직후라면 1~2분 정도 기다린 후 다시 실행해보세요.")

#실행
if __name__ == "__main__":
    get_korean_holidays()