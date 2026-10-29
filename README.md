# Fashion Insight Platform

패션 이커머스 트렌드 데이터와 고객 행동 데이터를 수집·적재하고, **자연어로 BigQuery를 질의하는 MCP 서버**와 ML 고객 세분화까지 연결한 End-to-End 데이터 플랫폼.

> 수집(크롤링/API) → BigQuery 적재 → ① 자연어 MCP 분석 인터페이스 ② RFM/XGBoost 고객 세분화, 두 소비 경로를 하나의 파이프라인으로 통합했습니다.

---

## 핵심 차별점

- **직접 구현한 MCP 서버로 BigQuery를 자연어 질의**
  Claude Desktop ↔ stdio(JSON-RPC) ↔ BigQuery를 잇는 서버를 직접 구현했습니다. 기성 커넥터가 아니라 프로토콜(`initialize` / `tools/list` / `tools/call`)을 직접 처리하며, **읽기 전용(SELECT-only) 안전장치**로 데이터 변경 쿼리를 차단합니다.
- **평가 엄밀성 — "98% 정확도 착시"를 스스로 진단**
  클래스 불균형 데이터에서 보정 전 정확도 98.5%는 우수고객 Recall이 6%에 불과한 착시였음을 확인하고, `class_weight='balanced'` 적용으로 소수 클래스 Recall을 94%까지 끌어올렸습니다. 지표를 액면 그대로 믿지 않고 검증합니다.
- **방법론적 한계를 명시** — RFM 규칙으로 만든 등급 라벨을 다시 RFM 피처로 예측하는 순환 구조를 진단으로 해석하고, 개선 방향(미래 행동 타겟 재정의)을 문서화했습니다.

---

## 아키텍처

```
[무신사 랭킹]  --Selenium 렌더 → BS4 속성 파싱-->  ┐
                                                    ├--> [BigQuery] --┬--> MCP 서버 (자연어 질의)
[GA 고객 행동 데이터 (공개 데이터셋 프록시)] -------┘                 └--> RFM / XGBoost / SHAP 분석
```

두 데이터는 **별도 파이프라인**입니다. 고객 데이터는 실제 무신사 고객이 아니라 이커머스 고객 행동 분석의 프록시(GA 공개 데이터셋)로 사용했으며, 두 파이프라인은 현재 조인되지 않습니다. (아래 [한계](#한계와-다음-단계) 참고)

---

## MCP 서버 (`fashion_mcp_server.py`)

Claude Desktop에서 자연어로 질문하면, Claude가 아래 툴을 호출해 BigQuery를 질의합니다.

| 툴 | 역할 |
|---|---|
| `list_tables` | 분석 가능한 테이블 목록과 용도 반환 |
| `get_schema` | 특정 테이블의 컬럼·타입 반환 (SQL 작성 전 확인용) |
| `run_query` | SELECT 쿼리 실행 후 결과 반환 |

**안전장치 (`run_query`)**
- `SELECT` / `WITH`로 시작하는 쿼리만 허용
- `DROP` `DELETE` `UPDATE` `INSERT` `CREATE` `ALTER` `TRUNCATE` 등 변경 키워드 차단
- 세미콜론 다중 구문 차단, `LIMIT` 미지정 시 자동 부착

예: *"고객 등급별 인원이 어떻게 돼?"* → Claude가 RFMScore 기준 등급 분류 SQL을 생성 → `run_query` → BigQuery 집계 결과 반환.

---

## 데이터 수집 파이프라인

- **무신사 랭킹** — 페이지가 JavaScript로 동적 렌더링되어 정적 `requests`로는 파싱이 불가능함을 진단(`get_source.py`), Selenium으로 전체 페이지를 렌더한 뒤 `data-item-brand`, `data-discount-rate` 등 **태그 속성값에서 직접 추출**(`2_parse_musinsa.py`). `product_id` 기준 중복 제거 포함.
- **일일 수집 스케줄러** — `musinsa_scheduler.py`
- **공휴일 API** — 한국천문연구원 공휴일 데이터 수집(`holiday_api.py`). *현재 분석에는 미통합(보조 소스).*
- **BigQuery 적재** — 로컬 CSV를 네이티브 테이블로 적재(`reload_to_bq.py`)

---

## ML 고객 세분화

- `rfm_analysis.py` — RFM 점수화 및 4등급 분류(VIP/우수/일반/이탈위험)
- `week4_analysis_vscode.py` — 행동 데이터 확장(9개 변수), RandomForest / XGBoost, 클래스 불균형 보정, SHAP 방향성 해석

| 모델 | 전체 정확도 | 우수고객 Recall |
|---|---|---|
| RF (RFM 3변수) | 60.3% | — |
| RF (보정 전) | 98.5% | 6% |
| **RF (보정 후) ★채택** | 95.6% | **94%** |
| XGBoost (보정 후) | 95.4% | 100% |

> 정확도는 소폭 하락했지만 소수 클래스 탐지율이 급등. "놓치는 것보다 넓게 잡는" 마케팅 관점의 의도된 트레이드오프.

---

## 데이터 파일

| 파일 | 레포 포함 | 내용 |
|---|---|---|
| `musinsa_ranking_data.csv` | O | 무신사 랭킹 수집 결과 (rank, product_id, brand_name, product_name, original_price, discount_price, discount_rate, date) |
| `holiday_api_data.csv` | O | 공휴일 API 수집 결과 (date, holiday_name, is_holiday) |
| `ga_log_data.csv` | X (용량) | GA 기반 고객 행동 데이터 9,996행. 컬럼: fullVisitorId, RFMScore, LastVisitedDays, NumberOfTransactions, OrderedAmount, pageviews, medium, browser, operatingSystem, isMobile. `reload_to_bq.py`·`week4_analysis_vscode.py` 입력 |
| `bq_rfm_data.csv` | X | `ga_log_data`에서 fullVisitorId, last_visit_date(YYYYMMDD), frequency, monetary 를 뽑은 집계. `rfm_analysis.py` 입력 |

포함하지 않은 두 파일은 실제 무신사 고객이 아니라 공개 GA 데이터를 프록시로 쓴 것입니다. 스크립트는 같은 폴더에 두 파일이 있다고 가정합니다.

## 실행 방법

### 1. 의존성 설치
서버를 실행할 Python 환경에 설치 (Claude Desktop이 사용하는 인터프리터와 동일해야 함):
```bash
pip install google-cloud-bigquery db-dtypes pandas "numpy<2"
```
> `numpy<2` 고정: 일부 패키지가 NumPy 1.x로 컴파일되어 2.x와 충돌하므로 명시적으로 1.x 사용.

### 2. BigQuery 인증 (ADC)
```bash
gcloud auth application-default login
gcloud config set project <YOUR_PROJECT_ID>
```

### 3. 데이터 적재
```bash
python reload_to_bq.py
```

### 4. Claude Desktop 연결
`claude_desktop_config.json`에 등록:
```json
{
  "mcpServers": {
    "fashion-data": {
      "command": "/opt/anaconda3/bin/python3",
      "args": ["/절대경로/fashion_mcp_server.py"]
    }
  }
}
```
Claude Desktop 재시작 후 자연어로 질의.

### 5. 서버 단독 테스트 (선택)
```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | python fashion_mcp_server.py
```

---

## 기술 스택

`Python` · `Selenium` · `BeautifulSoup` · `BigQuery` · `MCP (JSON-RPC/stdio)` · `scikit-learn` · `XGBoost` · `SHAP` · `pandas`

---

## 파일 구조

```
fashion_mcp_server.py       # BigQuery MCP 서버 (3툴 + SELECT-only 가드)
reload_to_bq.py             # 로컬 CSV → BigQuery 적재
get_source.py               # 무신사 Selenium 렌더링 수집
2_parse_musinsa.py          # HTML 속성값 파싱
musinsa_scheduler.py        # 일일 수집 스케줄러
holiday_api.py              # 공휴일 API 수집 (키는 환경변수)
rfm_analysis.py             # RFM 분석
week4_analysis_vscode.py    # RF/XGBoost/SHAP 고객 세분화
musinsa_ranking_data.csv    # 무신사 랭킹 데이터 (재현용)
holiday_api_data.csv        # 공휴일 데이터 (재현용)
```

---

## 한계와 다음 단계

- **두 파이프라인 미조인** — GA 고객 데이터와 무신사 상품 데이터는 별도 파이프라인으로, 실제 조인 분석이 아닙니다. 동일 도메인(이커머스) 프록시 데이터로 세분화 방법론을 검증한 것에 의의를 둡니다.
- **라벨-피처 순환성** — 등급 라벨과 예측 피처 사이의 순환 구조. 타겟을 미래 실제 행동(재구매·이탈)으로 재정의하는 것이 근본 개선 방향입니다.
- **MCP는 읽기 전용** — 현재 조회·집계 중심이며 분석·예측 툴은 로드맵 단계입니다.
- **데이터 만료** — BigQuery 샌드박스 데이터는 60일 후 만료되므로, `reload_to_bq.py`로 재적재해 복구합니다.
- **XGBoost 조기 종료가 테스트 세트를 봄** — `week4_analysis_vscode.py`의 `eval_set`이 테스트 세트라 XGBoost 95.4%는 낙관적인 값입니다. 학습 세트에서 검증 세트를 따로 떼는 것이 맞으며, RF 수치에는 영향이 없습니다.
