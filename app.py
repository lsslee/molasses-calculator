import pandas as pd
import streamlit as st

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="당밀류 원료 당농도 역산 계산기", page_icon="🧪", layout="wide"
)

# --- CORE LOGIC ---
MW_GLU = 180.16
MW_FRU = 180.16
MW_SUC = 342.30


def calculate_molasses_purity(
    target_glu,
    target_mol,
    p_glu,
    c_mol_suc,
    c_mol_glu,
    c_mol_fru,
    hplc_suc,
    hplc_glu,
    hplc_fru,
):
    c_mol_nominal_total = c_mol_suc + c_mol_glu + c_mol_fru
    w_glu_actual_percent = target_glu * (100.0 / p_glu) if p_glu > 0 else 0
    w_mol_actual_percent = (
        target_mol * (100.0 / c_mol_nominal_total)
        if c_mol_nominal_total > 0
        else 0
    )

    w_glu_actual_g_l = w_glu_actual_percent * 10
    w_mol_actual_g_l = w_mol_actual_percent * 10

    m_glu_powder = (w_glu_actual_g_l * (p_glu / 100.0)) / MW_GLU

    m_suc_meas = (hplc_suc * 10) / MW_SUC
    m_glu_meas = (hplc_glu * 10) / MW_GLU
    m_fru_meas = (hplc_fru * 10) / MW_FRU

    m_total_meas = (m_suc_meas * 2) + m_glu_meas + m_fru_meas
    m_mol_actual = max(0.0, m_total_meas - m_glu_powder)

    c_mol_actual_mass_g_l = m_mol_actual * MW_GLU
    actual_molasses_purity = (
        (c_mol_actual_mass_g_l / w_mol_actual_g_l) * 100.0
        if w_mol_actual_g_l > 0
        else 0.0
    )
    error_rate = (
        ((actual_molasses_purity - c_mol_nominal_total) / c_mol_nominal_total)
        * 100.0
        if c_mol_nominal_total > 0
        else 0.0
    )

    return {
        "actual_glu_input_percent": w_glu_actual_percent,
        "actual_mol_input_percent": w_mol_actual_percent,
        "measured_total_sugar_percent": hplc_suc + hplc_glu + hplc_fru,
        "m_glu_powder": m_glu_powder,
        "m_mol_actual": m_mol_actual,
        "c_mol_actual_mass_g_l": c_mol_actual_mass_g_l,
        "nominal_molasses_purity": c_mol_nominal_total,
        "actual_molasses_purity": actual_molasses_purity,
        "error_rate": error_rate,
    }


def generate_rule_based_report(
    res, hplc_suc, hplc_glu, hplc_fru, c_mol_suc, raw_material_type
):
    nominal = res["nominal_molasses_purity"]
    actual = res["actual_molasses_purity"]
    error = res["error_rate"]

    # 1. 원인 분석
    if abs(error) <= 5.0:
        cause_analysis = (
            f"역산된 실제 당농도({actual:.2f}%)가 스펙({nominal:.2f}%) 대비 "
            f"오차 범위 내({error:+.2f}%)로 안정적입니다. {raw_material_type} 원료의 품질 변동성이 적습니다."
        )
    elif error > 5.0:
        cause_analysis = (
            f"역산된 실제 당농도({actual:.2f}%)가 스펙({nominal:.2f}%) 대비 "
            f"{error:+.2f}% 높게 측정되었습니다. 원료의 농축/건조에 따른 당 함량 증가 또는 칭량 과정의 오차 가능성이 있습니다."
        )
    else:
        cause_analysis = (
            f"역산된 실제 당농도({actual:.2f}%)가 스펙({nominal:.2f}%) 대비 "
            f"{error:+.2f}% 낮게 측정되었습니다. {raw_material_type}의 실효 당 함량 감소, 수분 흡습 또는 보관 중 열열화 가능성이 있습니다."
        )

    # 2. Sucrose 가수분해 평가
    if hplc_suc == 0:
        hydrolysis_eval = (
            "HPLC 분석 결과 Sucrose가 전혀 검출되지 않았습니다(0%). "
            "멸균 과정 또는 산/열 조건에 의해 **Sucrose가 100% 완전 가수분해(Glucose + Fructose)**된 상태입니다."
        )
    else:
        hydrolysis_eval = (
            f"Sucrose 실측값이 {hplc_suc:.2f}%로 일부 잔류하고 있습니다. "
            "열처리/멸균 조건에 따라 분해가 완결되지 않았으며, 미생물의 소화/이용 속도 차이에 영향을 줄 수 있습니다."
        )

    # 3. 원료 특성별 리포트 (당밀 vs 정제당밀)
    if raw_material_type == "일반 당밀":
        molasses_info = (
            "📌 **일반 당밀(Molasses) 특성 가이드**:\n"
            "- 일반 당밀은 미네랄, 회분(Ash), 유기산 및 비당류 고형분이 포함되어 있어 멸균 시 메일라드(Maillard) 갈변 반응이 활발합니다.\n"
            "- 당 수치 외에 미네랄 함량에 의한 멸균 후 pH 변화 및 발효 저해 요소 점검이 권장됩니다."
        )
    else:
        molasses_info = (
            "📌 **정제당밀(Refined Molasses) 특성 가이드**:\n"
            "- 정제 공정을 거쳐 회분 및 탈색 처리가 완료된 원료로, 일반 당밀 대비 열열화 부반응 위험이 낮습니다.\n"
            "- 당 조성(Suc/Glc/Fru)의 일관성이 비교적 높으므로 오차 발생 시 칭량 조건 및 수분 함량(Brix)을 우선 확인하십시오."
        )

    # 4. 권고사항
    if abs(error) > 10.0:
        recommendation = f"⚠️ {raw_material_type} 당농도 오차율이 10%를 초과합니다. 원료 LOT 재검수 및 Brix/HPLC 재분석을 권장합니다."
    else:
        recommendation = "✅ 현 역산 수치를 바탕으로 차기 배지 조제 시 칭량 기준 스펙을 최적화하여 업데이트하십시오."

    return cause_analysis, hydrolysis_eval, molasses_info, recommendation


# --- UI LAYOUT ---
st.title("🧪 당밀류 원료 당농도 역산 & 자동 분석 시스템")
st.markdown(
    "당밀 및 정제당밀의 배지 조제 조건과 HPLC 실측 결과를 바탕으로 **원료의 실효 당농도**를 역산합니다."
)

st.sidebar.header("📋 1. 원료 및 배지 목표 설정")
raw_material_type = st.sidebar.selectbox(
    "사용 원료 유형 선택", ["정제당밀", "일반 당밀"], index=0
)

target_glu = st.sidebar.number_input(
    "포도당 목표 당농도 (w/v%)", value=3.35, step=0.1
)
target_mol = st.sidebar.number_input(
    f"{raw_material_type} 목표 당농도 (w/v%)", value=3.35, step=0.1
)
p_glu = st.sidebar.number_input("포도당 원료 순도 (%)", value=91.0, step=0.1)

st.sidebar.subheader(f"{raw_material_type} 스펙 (%)")
c_mol_suc = st.sidebar.number_input("Sucrose 스펙 (%)", value=5.8, step=0.1)
c_mol_glu = st.sidebar.number_input("Glucose 스펙 (%)", value=8.3, step=0.1)
c_mol_fru = st.sidebar.number_input("Fructose 스펙 (%)", value=9.7, step=0.1)

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("🔬 2. HPLC 측정 결과 입력")
    hplc_suc = st.number_input("Sucrose 실측값 (w/v%)", value=0.0, step=0.1)
    hplc_glu = st.number_input("Glucose 실측값 (w/v%)", value=4.76, step=0.1)
    hplc_fru = st.number_input("Fructose 실측값 (w/v%)", value=1.76, step=0.1)

    calc_button = st.button("🚀 당농도 역산 및 리포트 생성", use_container_width=True)

if calc_button or "res" in st.session_state:
    res = calculate_molasses_purity(
        target_glu,
        target_mol,
        p_glu,
        c_mol_suc,
        c_mol_glu,
        c_mol_fru,
        hplc_suc,
        hplc_glu,
        hplc_fru,
    )
    st.session_state["res"] = res

    with col2:
        st.subheader("📊 3. 역산 결과 리포트")
        m1, m2 = st.columns(2)
        m1.metric(
            f"{raw_material_type} 스펙 당농도",
            f"{res['nominal_molasses_purity']:.2f}%",
        )
        m2.metric(
            f"역산된 {raw_material_type} 실제 당농도",
            f"{res['actual_molasses_purity']:.2f}%",
            delta=f"{res['error_rate']:.2f}% (스펙 대비)",
        )

        df_res = pd.DataFrame(
            {
                "항목": [
                    "포도당 실제 칭량 투입량",
                    f"{raw_material_type} 실제 칭량 투입량",
                    "포도당 유래 몰농도",
                    f"{raw_material_type} 유래 실효 몰농도",
                    f"배지 내 {raw_material_type} 당 질량",
                    "HPLC 실측 총 당농도",
                ],
                "수치": [
                    f"{res['actual_glu_input_percent']:.4f} %",
                    f"{res['actual_mol_input_percent']:.4f} %",
                    f"{res['m_glu_powder']:.4f} mol/L",
                    f"{res['m_mol_actual']:.4f} mol/L",
                    f"{res['c_mol_actual_mass_g_l']:.2f} g/L",
                    f"{res['measured_total_sugar_percent']:.2f} %",
                ],
            }
        )
        st.dataframe(df_res, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("📋 4. 공정 및 원료 특성 리포트")

    cause, hydro, mol_info, reco = generate_rule_based_report(
        res, hplc_suc, hplc_glu, hplc_fru, c_mol_suc, raw_material_type
    )

    st.markdown(f"**1. 스펙 대비 역산 당농도 변동 분석**\n- {cause}")
    st.markdown(f"**2. Sucrose 가수분해 평가**\n- {hydro}")
    st.markdown(f"**3. {raw_material_type} 품질 및 공정 특성**\n{mol_info}")
    st.markdown(f"**4. 배지 조제 및 품질 관리 권고사항**\n- {reco}")
