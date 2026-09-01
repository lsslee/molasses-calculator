import pandas as pd
import numpy as np
import streamlit as st

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="다중 Jar 배지 당농도 역산 & 통합 분석 시스템",
    page_icon="🧪",
    layout="wide",
)

# --- CORE CONSTANTS ---
MW_GLU = 180.16
MW_FRU = 180.16
MW_SUC = 342.30

# 대표 평균 농도 상수
DEFAULT_REF_SUC, DEFAULT_REF_GLU, DEFAULT_REF_FRU = 6.12, 6.04, 6.36
DEFAULT_MOL_SUC, DEFAULT_MOL_GLU, DEFAULT_MOL_FRU = 24.80, 7.00, 8.20

# --- CALLBACK FUNCTIONS ---
def update_ref_spec():
    if st.session_state.get("check_auto_ref", False):
        st.session_state["ref_suc"] = DEFAULT_REF_SUC
        st.session_state["ref_glu"] = DEFAULT_REF_GLU
        st.session_state["ref_fru"] = DEFAULT_REF_FRU

def update_mol_spec():
    if st.session_state.get("check_auto_mol", False):
        st.session_state["mol_suc"] = DEFAULT_MOL_SUC
        st.session_state["mol_glu"] = DEFAULT_MOL_GLU
        st.session_state["mol_fru"] = DEFAULT_MOL_FRU

# Custom CSS
st.markdown(
    """
    <style>
    .section-header {
        background-color: #2D98DA;
        color: white;
        padding: 8px 15px;
        border-radius: 6px;
        font-weight: bold;
        font-size: 1.1rem;
        margin-top: 20px;
        margin-bottom: 15px;
    }
    .highlight-card {
        background-color: #eef5ff;
        border: 2px solid #3867d6;
        border-radius: 12px;
        padding: 15px;
        text-align: center;
    }
    </style>
""",
    unsafe_allow_html=True,
)

st.title("🧪 Multi-Jar 배지 당농도 일괄 역산 & 통합 분석 시스템")
st.markdown("여러 대의 배양기(Jar) 조건을 한 번에 입력하고 일괄 분석 결과를 비교하세요.")

# ---------------------------------------------------------
# Section 1. 기본 설정을 위한 공통 조건
# ---------------------------------------------------------
st.markdown('<div class="section-header">1. 기본 공정 및 당원 선택</div>', unsafe_allow_html=True)

c1, c2 = st.columns([2, 1])
with c1:
    selected_sources = st.multiselect(
        "사용할 당원 선택 (중복 선택 가능)",
        ["포도당", "액당", "정제당", "당밀"],
        default=["포도당", "정제당"],
    )
with c2:
    num_jars = st.number_input("분석할 Jar(배양기) 개수", min_value=1, max_value=12, value=4, step=1)

# ---------------------------------------------------------
# Section 2. 당원 공통 스펙 입력
# ---------------------------------------------------------
st.markdown('<div class="section-header">2. 당원 스펙 설정</div>', unsafe_allow_html=True)

p_glu, p_liq = 91.0, 75.0
c_ref_suc, c_ref_glu, c_ref_fru = 0.0, 0.0, 0.0
c_mol_suc, c_mol_glu, c_mol_fru = 0.0, 0.0, 0.0
correction_factor = 1.0

spec_cols = st.columns(len(selected_sources) if selected_sources else 1)

for idx, src in enumerate(selected_sources):
    with spec_cols[idx]:
        if src == "포도당":
            st.subheader("📌 포도당 스펙")
            p_glu = st.number_input("순도 (%)", value=91.0, step=0.1, key="p_glu")
        elif src == "액당":
            st.subheader("📌 액당 스펙")
            p_liq = st.number_input("순도/고형분 (%)", value=75.0, step=0.1, key="p_liq")
        elif src == "정제당":
            st.subheader("📌 정제당 스펙")
            use_auto_ref_spec = st.checkbox(
                "대표 평균 스펙 사용",
                value=False,
                key="check_auto_ref",
                on_change=update_ref_spec,
            )
            c_ref_suc = st.number_input("Sucrose (%)", value=DEFAULT_REF_SUC, step=0.01, key="ref_suc", disabled=use_auto_ref_spec)
            c_ref_glu = st.number_input("Glucose (%)", value=DEFAULT_REF_GLU, step=0.01, key="ref_glu", disabled=use_auto_ref_spec)
            c_ref_fru = st.number_input("Fructose (%)", value=DEFAULT_REF_FRU, step=0.01, key="ref_fru", disabled=use_auto_ref_spec)
            if use_auto_ref_spec:
                correction_factor = 1.030
        elif src == "당밀":
            st.subheader("📌 당밀 스펙")
            use_auto_mol_spec = st.checkbox(
                "대표 평균 스펙 사용",
                value=False,
                key="check_auto_mol",
                on_change=update_mol_spec,
            )
            c_mol_suc = st.number_input("Sucrose (%)", value=DEFAULT_MOL_SUC, step=0.01, key="mol_suc", disabled=use_auto_mol_spec)
            c_mol_glu = st.number_input("Glucose (%)", value=DEFAULT_MOL_GLU, step=0.01, key="mol_glu", disabled=use_auto_mol_spec)
            c_mol_fru = st.number_input("Fructose (%)", value=DEFAULT_MOL_FRU, step=0.01, key="mol_fru", disabled=use_auto_mol_spec)
            if use_auto_mol_spec:
                correction_factor = 1.031

# ---------------------------------------------------------
# Section 3. Jar별 조건 및 HPLC 데이터 입력 (표 데이터 에디터)
# ---------------------------------------------------------
st.markdown('<div class="section-header">3. Jar별 당원 농도 및 0h HPLC 데이터 일괄 입력</div>', unsafe_allow_html=True)
st.caption("💡 엑셀처럼 각 Jar의 목표 투입 농도(%)와 HPLC 분석 결과(w/v%)를 수정 및 입력하세요.")

jar_names = [f"Jar #{i+1}" for i in range(num_jars)]

# 1) Jar별 목표 농도 데이터프레임 초기화
default_input_data = {"Jar": jar_names}
for src in selected_sources:
    default_input_data[f"{src}_농도(%)"] = [3.5] * num_jars

df_target_input = pd.DataFrame(default_input_data)

# 2) Jar별 HPLC 데이터프레임 초기화
df_hplc_input = pd.DataFrame({
    "Jar": jar_names,
    "Sucrose(w/v%)": [1.00] * num_jars,
    "Glucose(w/v%)": [4.76] * num_jars,
    "Fructose(w/v%)": [1.76] * num_jars,
})

col_ed1, col_ed2 = st.columns(2)

with col_ed1:
    st.subheader("📋 [입력] Jar별 당원 설정 농도")
    edited_target_df = st.data_editor(
        df_target_input,
        hide_index=True,
        use_container_width=True,
        key="target_editor"
    )

with col_ed2:
    st.subheader("🧪 [입력] 배양액 0h HPLC 실측 결과")
    edited_hplc_df = st.data_editor(
        df_hplc_input,
        hide_index=True,
        use_container_width=True,
        key="hplc_editor"
    )

calc_btn = st.button("🚀 전체 Jar 일괄 역산 및 비교 리포트 생성", use_container_width=True, type="primary")

# ---------------------------------------------------------
# Section 4. 일괄 역산 계산 Engine 및 결과
# ---------------------------------------------------------
if calc_btn or "multi_res" in st.session_state:
    results_list = []

    ref_nominal_total = c_ref_suc + c_ref_glu + c_ref_fru
    mol_nominal_total = c_mol_suc + c_mol_glu + c_mol_fru

    complex_source_name = "복합당원"
    nominal_purity = 0.0
    if "정제당" in selected_sources and "당밀" not in selected_sources:
        complex_source_name = "정제당"
        nominal_purity = ref_nominal_total
    elif "당밀" in selected_sources and "정제당" not in selected_sources:
        complex_source_name = "당밀"
        nominal_purity = mol_nominal_total

    for idx in range(num_jars):
        jar_name = jar_names[idx]
        
        # Jar별 Target 농도
        target_glu = edited_target_df.loc[idx, "포도당_농도(%)"] if "포도당" in selected_sources else 0.0
        target_liq = edited_target_df.loc[idx, "액당_농도(%)"] if "액당" in selected_sources else 0.0
        target_ref = edited_target_df.loc[idx, "정제당_농도(%)"] if "정제당" in selected_sources else 0.0
        target_mol = edited_target_df.loc[idx, "당밀_농도(%)"] if "당밀" in selected_sources else 0.0

        # Jar별 HPLC
        h_suc = edited_hplc_df.loc[idx, "Sucrose(w/v%)"]
        h_glu = edited_hplc_df.loc[idx, "Glucose(w/v%)"]
        h_fru = edited_hplc_df.loc[idx, "Fructose(w/v%)"]
        total_hplc = h_suc + h_glu + h_fru

        # g/L 환산
        act_glu_pct = target_glu * (100.0 / p_glu) if p_glu > 0 else 0
        act_liq_pct = target_liq * (100.0 / p_liq) if p_liq > 0 else 0
        act_ref_pct = target_ref * (100.0 / ref_nominal_total) if ref_nominal_total > 0 else 0
        act_mol_pct = target_mol * (100.0 / mol_nominal_total) if mol_nominal_total > 0 else 0

        g_l_glu = act_glu_pct * 10
        g_l_liq = act_liq_pct * 10
        g_l_ref = act_ref_pct * 10
        g_l_mol = act_mol_pct * 10

        # HPLC 몰농도
        m_suc_meas = (h_suc * 10) / MW_SUC
        m_glu_meas = (h_glu * 10) / MW_GLU
        m_fru_meas = (h_fru * 10) / MW_FRU
        m_total_meas = (m_suc_meas * 2) + m_glu_meas + m_fru_meas

        # 차감
        m_glu_powder = (g_l_glu * (p_glu / 100.0)) / MW_GLU if "포도당" in selected_sources else 0
        m_liq_contrib = (g_l_liq * (p_liq / 100.0)) / MW_GLU if "액당" in selected_sources else 0
        m_rem = max(0.0, m_total_meas - m_glu_powder - m_liq_contrib)

        # 복합당원 역산 순도
        act_complex_purity = 0.0
        if complex_source_name == "정제당" and g_l_ref > 0:
            c_mass = m_rem * MW_GLU
            act_complex_purity = ((c_mass / g_l_ref) * 100.0) * correction_factor
        elif complex_source_name == "당밀" and g_l_mol > 0:
            c_mass = m_rem * MW_GLU
            act_complex_purity = ((c_mass / g_l_mol) * 100.0) * correction_factor

        diff_purity = act_complex_purity - nominal_purity

        # 기여 농도
        c_glu_contrib = act_glu_pct * (p_glu / 100.0) if "포도당" in selected_sources else 0
        c_liq_contrib = act_liq_pct * (p_liq / 100.0) if "액당" in selected_sources else 0
        c_ref_contrib = act_ref_pct * (act_complex_purity / 100.0 if complex_source_name == "정제당" else ref_nominal_total / 100.0) if "정제당" in selected_sources else 0
        c_mol_contrib = act_mol_pct * (act_complex_purity / 100.0 if complex_source_name == "당밀" else mol_nominal_total / 100.0) if "당밀" in selected_sources else 0

        tot_contrib = c_glu_contrib + c_liq_contrib + c_ref_contrib + c_mol_contrib

        results_list.append({
            "Jar": jar_name,
            "HPLC 실측총당(%)": round(total_hplc, 2),
            f"역산 {complex_source_name} 순도(%)": round(act_complex_purity, 2),
            "스펙 대비 차이(%p)": round(diff_purity, 2),
            "포도당 기여당(%)": round(c_glu_contrib, 2),
            "정제당 기여당(%)": round(c_ref_contrib, 2),
            "당밀 기여당(%)": round(c_mol_contrib, 2),
            "실제 총 기여당(%)": round(tot_contrib, 2),
        })

    df_results = pd.DataFrame(results_list)
    st.session_state["multi_res"] = df_results

    # ---------------------------------------------------------
    # Section 5. 통합 비교 리포트 출력
    # ---------------------------------------------------------
    st.markdown('<div class="section-header">4. Multi-Jar 통합 분석 결과 비교</div>', unsafe_allow_html=True)

    st.subheader(f"📊 Jar별 {complex_source_name} 역산 순도 및 기여 농도 요약")
    st.dataframe(df_results, use_container_width=True, hide_index=True)

    # 차트 시각화
    st.subheader("📈 Jar별 주요 결과 비교 시각화")
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        st.caption(f"📌 Jar별 {complex_source_name} 역산 실제 순도 (%)")
        st.bar_chart(df_results.set_index("Jar")[f"역산 {complex_source_name} 순도(%)"])

    with chart_col2:
        st.caption("📌 Jar별 HPLC 실측 총당 vs 계산된 실제 총 기여당 (%)")
        st.line_chart(df_results.set_index("Jar")[["HPLC 실측총당(%)", "실제 총 기여당(%)"]])

    # 편차 및 균일성 종합 평가
    st.subheader("📋 Jar 간 균일성 및 공정 통계 평가")
    
    purity_vals = df_results[f"역산 {complex_source_name} 순도(%)"]
    mean_purity = np.mean(purity_vals)
    std_purity = np.std(purity_vals)

    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("평균 역산 순도", f"{mean_purity:.2f}%")
    with m2:
        st.metric("Jar 간 표준 편차", f"±{std_purity:.2f}%p")
    with m3:
        cv = (std_purity / mean_purity) * 100 if mean_purity > 0 else 0
        st.metric("변동 계수 (CV)", f"{cv:.1f}%")

    if cv <= 3.0:
        st.success("🟢 **공정 평가**: Jar 간 당농도 편차가 3% 이내로 배지 조제 및 멸균 재현성이 매우 우수합니다.")
    else:
        st.warning("⚠️ **공정 평가**: Jar 간 편차가 존재합니다. 배지 칭량 오차, 용수 충진량 차이 또는 Jar별 멸균 열이력 균일성을 점검하세요.")
