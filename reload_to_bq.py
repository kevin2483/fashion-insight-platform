"""로컬 CSV 3개를 BigQuery에 네이티브 테이블로 재적재 (기존 EXTERNAL 테이블 삭제 후 생성)"""
from google.cloud import bigquery

PROJECT = "fashion-commerce-analysis"
DATASET = "fashion_commerce_project"
client = bigquery.Client(project=PROJECT)

jobs = [
    ("ga_log_data.csv",          "ga_log_data"),
    ("musinsa_ranking_data.csv", "musinsa_ranking"),
    ("holiday_api_data.csv",     "holiday_info"),
]

for csv_file, table in jobs:
    table_id = f"{PROJECT}.{DATASET}.{table}"

    # 1) 기존 테이블(EXTERNAL 포함) 삭제 — 없어도 에러 안 남
    client.delete_table(table_id, not_found_ok=True)
    print(f"    기존 {table} 삭제")

    # 2) CSV를 네이티브 테이블로 새로 적재
    config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV,
        skip_leading_rows=1,
        autodetect=True,
    )
    with open(csv_file, "rb") as f:
        job = client.load_table_from_file(f, table_id, job_config=config)
    job.result()
    n = client.get_table(table_id).num_rows
    print(f"OK  {csv_file:28s} -> {table:16s}  {n}행 적재")

print("\n재적재 완료")
