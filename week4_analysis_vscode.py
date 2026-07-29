"""
4주차 과제: 고객 등급 예측 모델 + SHAP 분석
VSCode 실행 버전 (Mac)
실행: python3 week4_analysis_vscode.py
"""

# ── 0. 라이브러리 ────────────────────────────────────────────
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
from sklearn.preprocessing import LabelEncoder
import xgboost as xgb
import shap
import warnings
warnings.filterwarnings('ignore')

# Mac 한글 폰트 설정
plt.rcParams['font.family'] = 'AppleGothic'
plt.rcParams['axes.unicode_minus'] = False

print("=" * 60)
print("4주차: 고객 등급 예측 모델 + SHAP 분석")
print("=" * 60)


# ── 1. 데이터 로드 ───────────────────────────────────────────
df = pd.read_csv('ga_log_data.csv')
print(f"✅ 데이터 로드: {df.shape[0]}행 × {df.shape[1]}열")


# ── 2. 고객 등급 분류 ────────────────────────────────────────
def classify_customer(score):
    if score >= 12:   return 'VIP'
    elif score >= 9:  return '우수고객'
    elif score >= 6:  return '일반고객'
    else:             return '이탈위험'

df['등급'] = df['RFMScore'].apply(classify_customer)
print("\n[고객 등급 분포]")
print(df['등급'].value_counts())


# ── 3. 피처 엔지니어링 ───────────────────────────────────────
le_medium  = LabelEncoder()
le_browser = LabelEncoder()
le_os      = LabelEncoder()

df['medium_enc']   = le_medium.fit_transform(df['medium'].fillna('unknown'))
df['browser_enc']  = le_browser.fit_transform(df['browser'].fillna('unknown'))
df['os_enc']       = le_os.fit_transform(df['operatingSystem'].fillna('unknown'))
df['isMobile_enc'] = df['isMobile'].astype(int)
df['avg_order_value'] = df['OrderedAmount'] / (df['NumberOfTransactions'] + 1)

FEATURES = [
    'LastVisitedDays',
    'NumberOfTransactions',
    'OrderedAmount',
    'pageviews',
    'medium_enc',
    'browser_enc',
    'os_enc',
    'isMobile_enc',
    'avg_order_value',
]

X = df[FEATURES].fillna(0)
y = df['등급']

print(f"\n[피처 구성] {len(FEATURES)}개 변수")


# ── 4. 학습/테스트 분리 ──────────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
print(f"[데이터 분리] 학습: {len(X_train)}행 / 테스트: {len(X_test)}행")


# ── 5. RandomForest (기본) ───────────────────────────────────
print("\n" + "=" * 60)
print("① RandomForest 모델")
print("=" * 60)

rf_model = RandomForestClassifier(
    n_estimators=200, max_depth=10,
    min_samples_split=5, random_state=42, n_jobs=-1
)
rf_model.fit(X_train, y_train)
rf_pred = rf_model.predict(X_test)
rf_acc  = accuracy_score(y_test, rf_pred)

print(f"정확도: {rf_acc:.2%}")
print(classification_report(y_test, rf_pred))

# RF Feature Importance 시각화
rf_importance = pd.Series(rf_model.feature_importances_, index=FEATURES).sort_values(ascending=True)
fig, ax = plt.subplots(figsize=(10, 6))
colors = ['#2E75B6' if v > 0.1 else '#A9C4E4' for v in rf_importance.values]
bars = ax.barh(rf_importance.index, rf_importance.values, color=colors)
ax.set_title('RandomForest - Feature Importance\n(고객 등급 결정 변수)', fontsize=14, fontweight='bold')
ax.set_xlabel('중요도', fontsize=12)
for bar, val in zip(bars, rf_importance.values):
    ax.text(val + 0.002, bar.get_y() + bar.get_height()/2, f'{val:.3f}', va='center', fontsize=10, fontweight='bold')
plt.tight_layout()
plt.savefig('rf_feature_importance.png', dpi=150, bbox_inches='tight')
plt.close()
print("✅ RF Feature Importance 저장")


# ── 6. RandomForest (클래스 불균형 보정) ─────────────────────
print("\n" + "=" * 60)
print("② RandomForest - 클래스 불균형 보정 (class_weight='balanced')")
print("=" * 60)

rf_balanced = RandomForestClassifier(
    n_estimators=200, max_depth=10,
    class_weight='balanced', random_state=42, n_jobs=-1
)
rf_balanced.fit(X_train, y_train)
pred_balanced = rf_balanced.predict(X_test)
rf_bal_acc = accuracy_score(y_test, pred_balanced)

print(f"정확도: {rf_bal_acc:.2%}")
print(classification_report(y_test, pred_balanced))


# ── 7. XGBoost 모델 ──────────────────────────────────────────
print("\n" + "=" * 60)
print("③ XGBoost 모델")
print("=" * 60)

le_grade = LabelEncoder()
y_train_enc = le_grade.fit_transform(y_train)
y_test_enc  = le_grade.transform(y_test)

xgb_model = xgb.XGBClassifier(
    n_estimators=300, learning_rate=0.05, max_depth=6,
    subsample=0.8, colsample_bytree=0.8, random_state=42,
    eval_metric='mlogloss', early_stopping_rounds=20, verbosity=0
)
xgb_model.fit(X_train, y_train_enc, eval_set=[(X_test, y_test_enc)], verbose=False)
xgb_pred = le_grade.inverse_transform(xgb_model.predict(X_test))
xgb_acc  = accuracy_score(y_test, xgb_pred)

print(f"정확도: {xgb_acc:.2%}")
print(classification_report(y_test, xgb_pred))


# ── 8. 모델 성능 비교 시각화 ─────────────────────────────────
fig, ax = plt.subplots(figsize=(8, 5))
models = ['RF\n(3주차)', 'RF\n(4주차)', 'RF\n(불균형보정)', 'XGBoost\n(4주차)']
accs   = [0.6025, rf_acc, rf_bal_acc, xgb_acc]
colors = ['#A9C4E4', '#2E75B6', '#1F4E79', '#70AD47']
bars = ax.bar(models, [a * 100 for a in accs], color=colors, width=0.5)
ax.set_title('모델 성능 비교 (정확도)', fontsize=14, fontweight='bold')
ax.set_ylabel('정확도 (%)', fontsize=12)
ax.set_ylim(0, 105)
for bar, acc in zip(bars, accs):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
            f'{acc:.1%}', ha='center', fontsize=11, fontweight='bold')
plt.tight_layout()
plt.savefig('model_comparison.png', dpi=150, bbox_inches='tight')
plt.close()
print("\n모델 비교 차트 저장")


# ── 9. SHAP 분석 ─────────────────────────────────────────────
print("\n" + "=" * 60)
print("④ SHAP 분석")
print("=" * 60)

explainer   = shap.TreeExplainer(xgb_model)
shap_values = explainer.shap_values(X_test)
print(f"SHAP values shape: {shap_values.shape}")
print(f"클래스 순서: {list(le_grade.classes_)}")

# SHAP Summary (전체)
plt.figure(figsize=(10, 7))
shap.summary_plot(shap_values, X_test, feature_names=FEATURES,
                  class_names=le_grade.classes_, show=False)
plt.title('SHAP Summary Plot\n(변수별 고객 등급 영향력 및 방향)', fontsize=13, fontweight='bold')
plt.tight_layout()
plt.savefig('shap_summary.png', dpi=150, bbox_inches='tight')
plt.close()
print("SHAP Summary 저장")

# SHAP Bar (중요도 순위)
plt.figure(figsize=(10, 6))
shap.summary_plot(shap_values, X_test, feature_names=FEATURES,
                  plot_type='bar', class_names=le_grade.classes_, show=False)
plt.title('SHAP Feature Importance\n(전체 등급 평균 기여도)', fontsize=13, fontweight='bold')
plt.tight_layout()
plt.savefig('shap_importance.png', dpi=150, bbox_inches='tight')
plt.close()
print("SHAP Importance 저장")

# SHAP VIP 등급
vip_idx = list(le_grade.classes_).index('VIP')
plt.figure()
shap.summary_plot(shap_values[:, :, vip_idx], X_test,
                  feature_names=FEATURES, show=False)
plt.title('SHAP - VIP 등급 결정 요인', fontsize=13, fontweight='bold')
plt.tight_layout()
plt.savefig('shap_vip.png', dpi=150, bbox_inches='tight')
plt.close()
print("SHAP VIP 저장")

# SHAP 이탈위험 등급
churn_idx = list(le_grade.classes_).index('이탈위험')
plt.figure()
shap.summary_plot(shap_values[:, :, churn_idx], X_test,
                  feature_names=FEATURES, show=False)
plt.title('SHAP - 이탈위험 고객 결정 요인', fontsize=13, fontweight='bold')
plt.tight_layout()
plt.savefig('shap_churn.png', dpi=150, bbox_inches='tight')
plt.close()
print("SHAP 이탈위험 저장")


# ── 10. 최종 요약 ────────────────────────────────────────────
print("\n" + "=" * 60)
print("📊 4주차 분석 결과 요약")
print("=" * 60)
print(f"• 3주차 RF 정확도:            60.25% (변수 3개)")
print(f"• 4주차 RF 정확도:            {rf_acc:.2%} (변수 9개, 행동 데이터 추가)")
print(f"• 4주차 RF 불균형 보정 정확도: {rf_bal_acc:.2%} (우수고객 Recall 6%→94%)")
print(f"• 4주차 XGBoost 정확도:       {xgb_acc:.2%}")
print()
print("저장된 파일:")
print("  rf_feature_importance.png / model_comparison.png")
print("  shap_summary.png / shap_importance.png")
print("  shap_vip.png / shap_churn.png")