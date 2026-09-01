import pandas as pd
import streamlit as st

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="다중 당원 배지 당농도 역산 & 분석 시스템",
    page_icon="🧪",
    layout="wide",
)

# --- CORE CONSTANTS ---
MW_GLU = 180.16
MW_FRU = 180.16
MW_SUC = 342.30

# --- UI LAYOUT ---
st.title("🧪 다중 당원 배지 당농도 역산 & 자동 분석 시스템")
st.markdown(
    "사용하는 당원을 자유롭게 선택하고, HPLC 실측 결과와 비교하여 **원료별 실효 당농도 및 오차**를 역산합니다."
)

st.sidebar.header("📋 1. 당원 선택 및 배지 목표 설정")
selected_sources = st.sidebar.multiselect(
    "사용할 당원 선택 (중복 선택 가능)",
    ["포도당", "액당", "정제당", "당밀"],
    default=["포도당", "당밀"],
)

# 기본값 초기화
target_glu, p_glu = 0.0, 91.0
target_liq, p_liq = 0.0, 75.0
target_ref, c_ref_suc, c_ref_glu, c_ref_fru = 0.0, 99.0, 0.5, 0.5
target_mol, c_mol_suc, c_mol_glu, c_mol_fru = 3.35, 5.8, 8.3, 9.7

if "포도당" in selected_sources:
    st.sidebar.subheader("포도당 설정")
    target_glu = st.sidebar.number_input(
        "포도당 목표 당농도 (w/v%)", value=3.35, step=0.1
    )
    p_glu = st.sidebar.number_input("포도당 순도 (%)", value=91.0, step=0.1)

if "액당" in selected_sources:
    st.sidebar.subheader("액당 설정")
    target_liq = st.sidebar.number_input(
        "액당 목표 당농도 (w/v%)", value=3.35, step=0.1
    )
    p_liq = st.sidebar.number_input(
        "액당 순도/고형분 (%)", value=75.0, step=0.1
    )

if "정제당" in selected_sources:
    st.sidebar.subheader("정제당 스펙 및 목표")
    target_ref = st.sidebar.number_input(
        "정제당 목표 당농도 (w/v%)", value=3.35, step=0.1
    )
    c_ref_suc = st.sidebar.number_input(
        "정제당 Sucrose 스펙 (%)", value=99.0, step=0.1
    )
    c_ref_glu = st.sidebar.number_input(
        "정제당 Glucose 스펙 (%)", value=0.5, step=0.1
    )
    c_ref_fru = st.sidebar.number_input(
        "정제당 Fructose 스펙 (%)", value=0.5, step=0.1
    )

if "당밀" in selected_sources:
    st.sidebar.subheader("당밀 스펙 및 목표")
    target_mol = st.sidebar.number_input(
        "당밀 목표 당농도 (w/v%)", value=3.35, step=0.1
    )
    c_mol_suc = st.sidebar.number_input(
        "당밀 Sucrose 스펙 (%)", value=5.8, step=0.1
    )
    c_mol_glu = st.sidebar.number_input(
        "당밀 Glucose 스펙 (%)", value=8.3, step=0.1
    )
    c_mol_fru = st.sidebar.number_input(
        "당밀 Fructose 스펙 (%)", value=9.7, step=0.1
    )

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("🔬 2. HPLC 측정 결과 입력")
    hplc_suc = st.number_input("Sucrose 실측값 (w/v%)", value=0.0, step=0.1)
    hplc_glu = st.number_input("Glucose 실측값 (w/v%)", value=4.76, step=0.1)
    hplc_fru = st.number_input("Fructose 실측값 (w/v%)", value=1.76, step=0.1)

    calc_button = st.button("🚀 당농도 역산 및 리포트 생성", use_container_width=True)

if calc_button or "res" in st.session_state:
    # 1. 실제 투입량 환산
    actual_glu_pct = target_glu * (100.0 / p_glu) if p_glu > 0 else 0
    actual_liq_pct = target_liq * (100.0 / p_liq) if p_liq > 0 else 0

    ref_nominal_total = c_ref_suc + c_ref_glu + c_ref_fru
    actual_ref_pct = (
        target_ref * (100.0 / ref_nominal_total)
        if ref_nominal_total > 0
        else 0
    )

    mol_nominal_total = c_mol_suc + c_mol_glu + c_mol_fru
    actual_mol_pct = (
        target_mol * (100.0 / mol_nominal_total)
        if mol_nominal_total > 0
        else 0
    )

    g_l_glu = actual_glu_pct * 10
    g_l_liq = actual_liq_pct * 10
    g_l_ref = actual_ref_pct * 10
    g_l_mol = actual_mol_pct * 10

    # 2. HPLC 실측 몰수 계산
    m_suc_meas = (hplc_suc * 10) / MW_SUC
    m_glu_meas = (hplc_glu * 10) / MW_GLU
    m_fru_meas = (hplc_fru * 10) / MW_FRU
    m_total_meas = (m_suc_meas * 2) + m_glu_meas + m_fru_meas

    # 단일 당원(포도당, 액당) 기여분 차감
    m_glu_powder = (
        (g_l_glu * (p_glu / 100.0)) / MW_GLU if "포도당" in selected_sources else 0
    )
    m_liq_contrib = (
        (g_l_liq * (p_liq / 100.0)) / MW_GLU if "액당" in selected_sources else 0
    )

    m_remaining = max(0.0, m_total_meas - m_glu_powder - m_liq_contrib)

    actual_molasses_purity = 0.0
    error_rate = 0.0
    actual_ref_purity = 0.0
    ref_error_rate = 0.0

    # 복합 당원(당밀/정제당) 역산
    if "당밀" in selected_sources and "정제당" not in selected_sources:
        c_mol_actual_mass_g_l = m_remaining * MW_GLU
        actual_molasses_purity = (
            (c_mol_actual_mass_g_l / g_l_mol) * 100.0 if g_l_mol > 0 else 0.0
        )
        error_rate = (
            ((actual_molasses_purity - mol_nominal_total) / mol_nominal_total)
            * 100.0
            if mol_nominal_total > 0
            else 0.0
        )
    elif "정제당" in selected_sources and "당밀" not in selected_sources:
        c_ref_actual_mass_g_l = m_remaining * MW_GLU
        actual_ref_purity = (
            (c_ref_actual_mass_g_l / g_l_ref) * 100.0 if g_l_ref > 0 else 0.0
        )
        error_rate = (
            ((actual_ref_purity - ref_nominal_total) / ref_nominal_total)
            * 100.0
            if ref_nominal_total > 0
            else 0.0
        )
    elif "당밀" in selected_sources and "정제당" in selected_sources:
        total_complex = target_mol + target_ref
        if total_complex > 0:
            mol_share = target_mol / total_complex
            mol_allocated_mass = (m_remaining * MW_GLU) * mol_share
            actual_molasses_purity = (
                (mol_allocated_mass / g_l_mol) * 100.0 if g_l_mol > 0 else 0.0
            )
            error_rate = (
                ((actual_molasses_purity - mol_nominal_total) / mol_nominal_total)
                * 100.0
                if mol_nominal_total > 0
                else 0.0
            )

    res = {
        "selected_sources": selected_sources,
        "measured_total_sugar_percent": hplc_suc + hplc_glu + hplc_fru,
        "nominal_molasses_purity": (
            mol_nominal_total if "당밀" in selected_sources else 0
        ),
        "actual_molasses_purity": actual_molasses_purity,
        "error_rate": error_rate,
    }
    st.session_state["res"] = res

    with col2:
        st.subheader("📊 3. 역산 결과 리포트")
        if "당밀" in selected_sources:
            m1, m2 = st.columns(2)
            m1.metric("당밀 스펙 당농도", f"{mol_nominal_total:.2f}%")
            m2.metric(
                "역산된 당밀 실제 당농도",
                f"{actual_molasses_purity:.2f}%",
                delta=f"{error_rate:.2f}% (스펙 대비)",
            )
        elif "정제당" in selected_sources:
            m1, m2 = st.columns(2)
            m1.metric("정제당 스펙 당농도", f"{ref_nominal_total:.2f}%")
            m2.metric(
                "역산된 정제당 실제 당농도",
                f"{actual_ref_purity:.2f}%",
                delta=f"{error_rate:.2f}% (스펙 대비)",
            )
        else:
            st.metric(
                "HPLC 실측 총 당농도",
                f"{res['measured_total_sugar_percent']:.2f}%",
            )

        table_data = []
        if "포도당" in selected_sources:
            table_data.append(
                ["포도당 실제 칭량 투입량", f"{actual_glu_pct:.4f} %"]
            )
        if "액당" in selected_sources:
            table_data.append(
                ["액당 실제 칭량 투입량", f"{actual_liq_pct:.4f} %"]
            )
        if "정제당" in selected_sources:
            table_data.append(
                ["정제당 실제 칭량 투입량", f"{actual_ref_pct:.4f} %"]
            )
        if "당밀" in selected_sources:
            table_data.append(
                ["당밀 실제 칭량 투입량", f"{actual_mol_pct:.4f} %"]
            )
        table_data.append(
            ["HPLC 실측 총 당농도", f"{res['measured_total_sugar_percent']:.2f} %"]
        )

        df_res = pd.DataFrame(table_data, columns=["항목", "수치"])
        st.dataframe(df_res, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("📋 4. 공정 및 당원 특성 리포트")

    sources_str = ", ".join(selected_sources)
    st.markdown(f"- **선택된 당원 구성**: `{sources_str}`")

    if hplc_suc == 0:
        hydro_text = "HPLC 분석 결과 Sucrose가 전혀 검출되지 않았습니다(0%). 멸균 및 조제 과정에서 **Sucrose가 100% 완전 가수분해(Glucose + Fructose)**되었습니다."
    else:
        hydro_text = f"Sucrose 실측값이 {hplc_suc:.2f}% 잔류하고 있습니다. 열처리 조건에 따라 부분 가수분해된 상태입니다."

    st.markdown(f"- **Sucrose 가수분해 평가**: {hydro_text}")

    if "당밀" in selected_sources or "정제당" in selected_sources:
        if abs(error_rate) <= 5.0:
            eval_msg = f"실효 당농도가 스펙 범위 내에서 안정적으로 유지되고 있습니다 (오차 {error_rate:+.2f}%)."
        elif error_rate > 5.0:
            eval_msg = f"실효 당농도가 스펙 대비 {error_rate:+.2f}% 높게 측정되었습니다. 원료 농축 상태 또는 칭량 오차를 확인하십시오."
        else:
            eval_msg = f"실효 당농도가 스펙 대비 {error_rate:+.2f}% 낮게 측정되었습니다. 수분 흡습 또는 열열화 가능성이 있습니다."
        st.markdown(f"- **복합 당원 품질 변동 분석**: {eval_msg}")

    st.markdown(
        "- **배지 조제 권고사항**: 선택된 당원의 투입 비율과 HPLC 측정된 당 조성 결과를 반영하여 차기 배지 칭량 레시피를 보정하십시오."
    )
