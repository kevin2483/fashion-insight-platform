import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import warnings
warnings.filterwarnings('ignore')

# 한글 폰트 설정 (맥 기준)
plt.rcParams['font.family'] = 'AppleGothic'
plt.rcParams['axes.unicode_minus'] = False

# ── 1. 데이터 로드 ──────────────────────────────────────────
df = pd.read_csv('bq_rfm_data.csv')
# 날짜 변환
df['last_visit_date'] = pd.to_datetime(df['last_visit_date'], format='%Y%m%d')
reference_date = df['last_visit_date'].max() + pd.Timedelta(days=1)

# ── 2. RFM 계산 ──────────────────────────────────────────────
df['Recency'] = (reference_date - df['last_visit_date']).dt.days
df['Frequency'] = df['frequency']
df['Monetary'] = df['monetary']

rfm = df[['fullVisitorId', 'Recency', 'Frequency', 'Monetary']].copy()

# ── 3. RFM 등급화 (1~5점, Recency는 낮을수록 좋으므로 역순) ──
rfm['R_score'] = pd.qcut(rfm['Recency'], q=5, labels=[5,4,3,2,1], duplicates='drop')
rfm['F_score'] = pd.qcut(rfm['Frequency'].rank(method='first'), q=5, labels=[1,2,3,4,5])
rfm['M_score'] = pd.qcut(rfm['Monetary'], q=5, labels=[1,2,3,4,5])

rfm['RFM_Score'] = rfm['R_score'].astype(int) + rfm['F_score'].astype(int) + rfm['M_score'].astype(int)

# ── 4. 고객 등급 분류 ─────────────────────────────────────────
def classify_customer(score):
    if score >= 12:
        return 'VIP'
    elif score >= 9:
        return '우수고객'
    elif score >= 6:
        return '일반고객'
    else:
        return '이탈위험'

rfm['등급'] = rfm['RFM_Score'].apply(classify_customer)

print("=" * 50)
print("고객 등급 분포")
print("=" * 50)
print(rfm['등급'].value_counts())
print()
print("등급별 RFM 평균값")
print(rfm.groupby('등급')[['Recency','Frequency','Monetary']].mean().round(2))

# ── 5. 시각화 ────────────────────────────────────────────────
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle('RFM 고객 분석 대시보드', fontsize=16, fontweight='bold')

# 차트1: 고객 등급 분포 (원형)
grade_counts = rfm['등급'].value_counts()
colors = ['#2E75B6', '#70AD47', '#FFC000', '#FF4B4B']
axes[0,0].pie(grade_counts.values, labels=grade_counts.index,
              autopct='%1.1f%%', colors=colors, startangle=90)
axes[0,0].set_title('고객 등급 분포')

# 차트2: 등급별 평균 구매금액 (막대)
grade_monetary = rfm.groupby('등급')['Monetary'].mean().reindex(['VIP','우수고객','일반고객','이탈위험'])
axes[0,1].bar(grade_monetary.index, grade_monetary.values, color=colors)
axes[0,1].set_title('등급별 평균 구매금액')
axes[0,1].set_ylabel('평균 구매금액 ($)')
for i, v in enumerate(grade_monetary.values):
    axes[0,1].text(i, v + 5, f'${v:.0f}', ha='center', fontweight='bold')

# 차트3: 등급별 평균 방문 빈도 (막대)
grade_freq = rfm.groupby('등급')['Frequency'].mean().reindex(['VIP','우수고객','일반고객','이탈위험'])
axes[1,0].bar(grade_freq.index, grade_freq.values, color=colors)
axes[1,0].set_title('등급별 평균 방문 빈도')
axes[1,0].set_ylabel('평균 방문 횟수')
for i, v in enumerate(grade_freq.values):
    axes[1,0].text(i, v + 0.05, f'{v:.1f}회', ha='center', fontweight='bold')

# 차트4: RFM 점수 분포 (히스토그램)
axes[1,1].hist(rfm['RFM_Score'], bins=12, color='#2E75B6', edgecolor='white')
axes[1,1].set_title('RFM 점수 분포')
axes[1,1].set_xlabel('RFM 점수')
axes[1,1].set_ylabel('고객 수')
axes[1,1].axvline(x=12, color='red', linestyle='--', label='VIP 기준(12점)')
axes[1,1].axvline(x=9, color='orange', linestyle='--', label='우수 기준(9점)')
axes[1,1].legend()

plt.tight_layout()
plt.savefig('/home/claude/rfm_dashboard.png', dpi=150, bbox_inches='tight')
plt.close()
print("\n✅ RFM 대시보드 저장 완료: rfm_dashboard.png")

# ── 6. 머신러닝: 고객 등급 예측 (RandomForest) ────────────────
print("\n" + "=" * 50)
print("머신러닝 분석 (RandomForest)")
print("=" * 50)

X = rfm[['Recency', 'Frequency', 'Monetary']]
y = rfm['등급']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

print(f"\n모델 정확도: {model.score(X_test, y_test):.2%}")

# 변수 중요도
importances = pd.Series(model.feature_importances_, index=X.columns)
print("\n변수 중요도 (랭킹에 영향을 주는 요소):")
print(importances.sort_values(ascending=False))

# 변수 중요도 시각화
fig2, ax = plt.subplots(figsize=(8, 5))
importances.sort_values().plot(kind='barh', ax=ax, color=['#FFC000','#70AD47','#2E75B6'])
ax.set_title('고객 등급 결정 변수 중요도 (RandomForest)', fontsize=13)
ax.set_xlabel('중요도')
for i, v in enumerate(importances.sort_values().values):
    ax.text(v + 0.001, i, f'{v:.3f}', va='center', fontweight='bold')
plt.tight_layout()
plt.savefig('/home/claude/feature_importance.png', dpi=150, bbox_inches='tight')
plt.close()
print("\n변수 중요도 차트 저장 완료: feature_importance.png")

# ── 7. 등급별 특징 요약 ──────────────────────────────────────
print("\n" + "=" * 50)
print("등급별 고객 특징 요약")
print("=" * 50)
summary = rfm.groupby('등급').agg(
    고객수=('fullVisitorId','count'),
    평균_최근방문일=('Recency','mean'),
    평균_방문횟수=('Frequency','mean'),
    평균_구매금액=('Monetary','mean')
).round(2)
print(summary)
summary.to_csv('/home/claude/rfm_summary.csv', encoding='utf-8-sig')
print("\n요약 데이터 저장 완료: rfm_summary.csv")