from bs4 import BeautifulSoup
import pandas as pd

def parse_html_to_csv():
    print("🔍 저장된 HTML 파일에서 데이터를 추출합니다...")
    
    
    try:
        with open('musinsa_source.txt', 'r', encoding='utf-8') as f:
            html = f.read()
    except FileNotFoundError:
        print("'musinsa_source.txt' 파일을 찾을 수 없습니다. 같은 폴더에 있는지 확인해주세요!")
        return
        
    soup = BeautifulSoup(html, 'html.parser')
    
    #바뀐 무신사 구조에 맞춰 상품 정보가 담긴 태그 찾기
    items = soup.select('a.gtm-select-item')
    
    data_list = []
    seen_ids = set() # 중복 수집 방지용
    
    for item in items:
        #상품명이 들어있는 p 태그 확인
        title_p = item.find('p')
        if not title_p:
            continue
            
        product_id = item.get('data-item-id', '0')
        
        if product_id in seen_ids:
            continue
        seen_ids.add(product_id)
        
        #새로운 구조의 데이터 추출 (속성값에서 바로 가져옴)
        rank = item.get('data-item-list-index', 0)
        brand_name = item.get('data-item-brand', '')
        product_name = title_p.text.strip()
        original_price = item.get('data-original-price', 0)
        discount_price = item.get('data-price', 0)
        discount_rate = item.get('data-discount-rate', 0)
        
        data_list.append({
            "rank": int(rank),
            "product_id": product_id,
            "brand_name": brand_name,
            "product_name": product_name,
            "original_price": int(original_price),
            "discount_price": int(discount_price),
            "discount_rate": int(discount_rate)
        })
        
    #Pandas 데이터프레임 변환 및 정렬
    df = pd.DataFrame(data_list)
    
    if len(df) > 0:
        df = df.sort_values(by='rank').reset_index(drop=True)
        
        print(f"\n✅ 총 {len(df)}개의 트렌드 상품 데이터를 추출했습니다! (미리보기)")
        print(df.head())
        
        # 4. 분석용 CSV 저장 (1주차 과제용)
        file_name = "musinsa_ranking_data.csv"
        df.to_csv(file_name, index=False, encoding='utf-8-sig')
        print(f"\n💾 성공적으로 '{file_name}' 파일이 생성되었습니다! 파이프라인 수집 완료!")
    else:
        print("상품을 찾지 못했습니다.")

if __name__ == "__main__":
    parse_html_to_csv()