"""
Fashion Commerce MCP Server (BigQuery 백엔드)
- Claude Desktop <-> stdio(JSON-RPC) <-> BigQuery
- 자연어 질의를 Claude가 tools/call로 라우팅 -> 서버가 BigQuery에 SELECT 실행
- 안전장치: SELECT/WITH로 시작하는 읽기 쿼리만 허용
"""
import sys
import json
import re
from google.cloud import bigquery

PROJECT = "fashion-commerce-analysis"
DATASET = "fashion_commerce_project"

client = bigquery.Client(project=PROJECT)


# ── SELECT-only 안전장치 ──────────────────────────────────
# 읽기 전용만 허용: DROP/DELETE/UPDATE/INSERT/CREATE/ALTER/TRUNCATE 차단
FORBIDDEN = re.compile(
    r"\b(DROP|DELETE|UPDATE|INSERT|CREATE|ALTER|TRUNCATE|MERGE|GRANT|REVOKE)\b",
    re.IGNORECASE,
)

def run_query(sql: str, limit: int = 100) -> str:
    """SELECT 쿼리만 실행하고 결과를 텍스트로 반환"""
    s = sql.strip().rstrip(";")
    low = s.lower()

    # 1) SELECT 또는 WITH로 시작하는지
    if not (low.startswith("select") or low.startswith("with")):
        return "거부됨: 읽기 전용(SELECT) 쿼리만 실행할 수 있습니다."
    # 2) 금지 키워드 포함 여부
    if FORBIDDEN.search(s):
        return "거부됨: 데이터를 변경하는 쿼리는 실행할 수 없습니다."
    # 3) 세미콜론 다중 구문 차단
    if ";" in s:
        return "거부됨: 한 번에 하나의 쿼리만 실행할 수 있습니다."

    # LIMIT 없으면 안전하게 부착
    if "limit" not in low:
        s = f"{s}\nLIMIT {limit}"

    try:
        df = client.query(s).to_dataframe()
    except Exception as e:
        return f"쿼리 오류: {e}"

    if len(df) == 0:
        return "결과 없음 (0행)"
    return f"{len(df)}행 반환:\n\n{df.to_string(index=False)}"


def process(req):
    method = req.get("method", "")
    rid = req.get("id")

    if method == "initialize":
        return {"jsonrpc":"2.0","id":rid,"result":{
            "protocolVersion":"2024-11-05",
            "capabilities":{"tools":{}},
            "serverInfo":{"name":"fashion-data","version":"2.0.0"}
        }}

    if method == "notifications/initialized":
        return None

    if method == "tools/list":
        return {"jsonrpc":"2.0","id":rid,"result":{"tools":[
            {
                "name":"list_tables",
                "description":"분석 가능한 BigQuery 테이블 목록과 각 테이블의 용도를 반환한다. 어떤 데이터가 있는지 먼저 파악할 때 사용.",
                "inputSchema":{"type":"object","properties":{}}
            },
            {
                "name":"get_schema",
                "description":"특정 테이블의 컬럼명과 타입을 반환한다. run_query로 SQL을 작성하기 전에 컬럼을 확인할 때 사용.",
                "inputSchema":{"type":"object","properties":{
                    "table":{"type":"string","description":"테이블명: ga_log_data / musinsa_ranking / holiday_info"}
                },"required":["table"]}
            },
            {
                "name":"run_query",
                "description":(
                    "BigQuery에 SELECT 쿼리를 실행해 고객 RFM 데이터와 무신사 랭킹 데이터를 분석한다. "
                    "읽기 전용(SELECT)만 허용된다. "
                    f"테이블: `{PROJECT}.{DATASET}.ga_log_data`(고객 RFM/행동), "
                    f"`{PROJECT}.{DATASET}.musinsa_ranking`(브랜드 랭킹/할인). "
                    "고객 등급은 RFMScore로 판단: 12+ VIP, 9-11 우수고객, 6-8 일반고객, 5이하 이탈위험."
                ),
                "inputSchema":{"type":"object","properties":{
                    "sql":{"type":"string","description":"실행할 SELECT 쿼리 (전체 테이블 경로 사용)"}
                },"required":["sql"]}
            }
        ]}}

    if method == "tools/call":
        name = req["params"]["name"]
        args = req["params"].get("arguments", {})

        if name == "list_tables":
            text = (
                f"프로젝트: {PROJECT} / 데이터셋: {DATASET}\n\n"
                "- ga_log_data : GA 고객 행동·RFM 데이터 (고객 세분화 분석용)\n"
                "- musinsa_ranking : 무신사 랭킹·브랜드·할인율 (트렌드 분석용)\n"
                "- holiday_info : 공휴일 정보\n\n"
                "쿼리 시 전체 경로 사용 예: "
                f"`{PROJECT}.{DATASET}.ga_log_data`"
            )
            return {"jsonrpc":"2.0","id":rid,"result":{"content":[{"type":"text","text":text}]}}

        if name == "get_schema":
            table = args.get("table","")
            allowed = {"ga_log_data","musinsa_ranking","holiday_info"}
            if table not in allowed:
                text = f"허용되지 않은 테이블. 다음 중 하나: {', '.join(allowed)}"
            else:
                t = client.get_table(f"{PROJECT}.{DATASET}.{table}")
                cols = "\n".join(f"  {f.name}: {f.field_type}" for f in t.schema)
                text = f"[{table}] {t.num_rows}행\n{cols}"
            return {"jsonrpc":"2.0","id":rid,"result":{"content":[{"type":"text","text":text}]}}

        if name == "run_query":
            text = run_query(args.get("sql",""))
            return {"jsonrpc":"2.0","id":rid,"result":{"content":[{"type":"text","text":text}]}}

    return {"jsonrpc":"2.0","id":rid,"result":{}}


for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    try:
        req = json.loads(line)
        res = process(req)
        if res:
            print(json.dumps(res, ensure_ascii=False), flush=True)
    except Exception as e:
        print(json.dumps({"jsonrpc":"2.0","id":None,"error":{"code":-32603,"message":str(e)}}), flush=True)
