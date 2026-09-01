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

# Custom CSS
st.markdown(
    """
    <style>
    .step-card {
        background-color: #f8f9fa;
        border-left: 5px solid #4B7BEC;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 15px;
    }
    .step-title {
        color: #2D98DA;
        font-weight: bold;
        font-size: 1.1rem;
        margin-bottom: 8px;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# --- UI LAYOUT ---
st.title("🧪 다중 당원 배지 당농도 역산 & 자동 분석 시스템")
st.markdown(
    "사용하는 당원을 자유롭게 선택하고, HPLC 실측 결과와 비교하여 **원료별 실효 당농도 및 오차**를 역산합니다."
)

st.sidebar.header("📋 1. 당원 선택 및 배지 목표 설정")
selected_sources = st.sidebar.multiselect(
    "사용할 당원 선택 (중복 선택 가능)",
    ["포도당", "액당", "정제당", "당밀"],
    default=["포도당", "정제당"],
)

# 오차 표시 방식 선택 (절대 차이 vs 상대 오차)
diff_mode = st.sidebar.radio(
    "오차율 표시 방식 선택",
    ["절대 차이 (%p)", "상대 오차 (%)"],
    index=0,
    help="절대 차이: 실제 농도 - 스펙 농도 (%p)\n상대 오차: (실제 농도 - 스펙 농도) / 스펙 농도 * 100 (%)",
)

# 기본값 초기화
target_glu, p_glu = 0.0, 91.0
target_liq, p_liq = 0.0, 75.0
target_ref, c_ref_suc, c_ref_glu, c_ref_fru = 0.0, 99.0, 0.5, 0.5
target_mol, c_mol_suc, c_mol_glu, c_mol_fru = 0.0, 5.8, 8.3, 9.7

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
        "정제당 Sucrose 스펙 (%)", value=12.0, step=0.1
    )
    c_ref_glu = st.sidebar.number_input(
        "정제당 Glucose 스펙 (%)", value=5.0, step=0.1
    )
    c_ref_fru = st.sidebar.number_input(
        "정제당 Fructose 스펙 (%)", value=8.0, step=0.1
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
    hplc_suc = st.number_input("Sucrose 실측값 (w/v%)", value=1.00, step=0.1)
    hplc_glu = st.number_input("Glucose 실측값 (w/v%)", value=4.76, step=0.1)
    hplc_fru = st.number_input("Fructose 실측값 (w/v%)", value=1.76, step=0.1)

    calc_button = st.button("🚀 당농도 역산 및 리포트 생성", use_container_width=True)

if calc_button or "res" in st.session_state:
    # 1. 실제 투입량 환산 (w/v% -> g/L)
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

    # 2. HPLC 실측 몰농도 계산
    m_suc_meas = (hplc_suc * 10) / MW_SUC
    m_glu_meas = (hplc_glu * 10) / MW_GLU
    m_fru_meas = (hplc_fru * 10) / MW_FRU

    m_total_meas = (m_suc_meas * 2) + m_glu_meas + m_fru_meas

    # 단일 당원 차감
    m_glu_powder = (
        (g_l_glu * (p_glu / 100.0)) / MW_GLU if "포도당" in selected_sources else 0
    )
    m_liq_contrib = (
        (g_l_liq * (p_liq / 100.0)) / MW_GLU if "액당" in selected_sources else 0
    )

    m_remaining = max(0.0, m_total_meas - m_glu_powder - m_liq_contrib)

    # 복합 당원 명칭 및 계산 동기화
    complex_source_name = "복합당원"
    nominal_complex_purity = 0.0
    actual_complex_purity = 0.0
    g_l_complex = 0.0

    if "정제당" in selected_sources and "당밀" not in selected_sources:
        complex_source_name = "정제당"
        nominal_complex_purity = ref_nominal_total
        g_l_complex = g_l_ref
        c_ref_actual_mass = m_remaining * MW_GLU
        actual_complex_purity = (
            (c_ref_actual_mass / g_l_ref) * 100.0 if g_l_ref > 0 else 0.0
        )
    elif "당밀" in selected_sources and "정제당" not in selected_sources:
        complex_source_name = "당밀"
        nominal_complex_purity = mol_nominal_total
        g_l_complex = g_l_mol
        c_mol_actual_mass = m_remaining * MW_GLU
        actual_complex_purity = (
            (c_mol_actual_mass / g_l_mol) * 100.0 if g_l_mol > 0 else 0.0
        )
    elif "당밀" in selected_sources and "정제당" in selected_sources:
        complex_source_name = "당밀/정제당"
        nominal_complex_purity = mol_nominal_total
        g_l_complex = g_l_mol
        mol_share = target_mol / (target_mol + target_ref)
        mol_allocated_mass = (m_remaining * MW_GLU) * mol_share
        actual_complex_purity = (
            (mol_allocated_mass / g_l_mol) * 100.0 if g_l_mol > 0 else 0.0
        )

    # 오차율 계산 (선택한 옵션에 따라)
    abs_diff = actual_complex_purity - nominal_complex_purity
    rel_error = (
        (abs_diff / nominal_complex_purity) * 100.0
        if nominal_complex_purity > 0
        else 0.0
    )

    if diff_mode == "절대 차이 (%p)":
        delta_str = f"{abs_diff:+.2f}%p (스펙 대비)"
    else:
        delta_str = f"{rel_error:+.2f}% (스펙 대비)"

    res = {
        "selected_sources": selected_sources,
        "measured_total_sugar_percent": hplc_suc + hplc_glu + hplc_fru,
        "complex_source_name": complex_source_name,
        "nominal_complex_purity": nominal_complex_purity,
        "actual_complex_purity": actual_complex_purity,
        "abs_diff": abs_diff,
        "rel_error": rel_error,
        "delta_str": delta_str,
        "m_suc_meas": m_suc_meas,
        "m_glu_meas": m_glu_meas,
        "m_fru_meas": m_fru_meas,
        "m_total_meas": m_total_meas,
        "m_glu_powder": m_glu_powder,
        "m_liq_contrib": m_liq_contrib,
        "m_remaining": m_remaining,
        "actual_glu_pct": actual_glu_pct,
        "actual_liq_pct": actual_liq_pct,
        "actual_ref_pct": actual_ref_pct,
        "actual_mol_pct": actual_mol_pct,
        "g_l_glu": g_l_glu,
        "g_l_liq": g_l_liq,
        "g_l_ref": g_l_ref,
        "g_l_mol": g_l_mol,
        "g_l_complex": g_l_complex,
    }
    st.session_state["res"] = res

    # --- 3. 역산 결과 리포트 (우측 칼럼) ---
    with col2:
        st.subheader("📊 3. 역산 결과 리포트")
        if complex_source_name != "복합당원":
            m1, m2 = st.columns(2)
            m1.metric(
                f"{complex_source_name} 스펙 당농도",
                f"{nominal_complex_purity:.2f}%",
            )
            m2.metric(
                f"역산된 {complex_source_name} 실제 당농도",
                f"{actual_complex_purity:.2f}%",
                delta=delta_str,
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

    # --- 4. 공정 및 당원 특성 리포트 ---
    st.subheader("📋 4. 공정 및 당원 특성 리포트")

    sources_str = ", ".join(selected_sources)
    st.markdown(f"- **선택된 당원 구성**: `{sources_str}`")

    if hplc_suc == 0:
        hydro_text = "HPLC 분석 결과 Sucrose가 전혀 검출되지 않았습니다(0%). 멸균 및 조제 과정에서 **Sucrose가 100% 완전 가수분해(Glucose + Fructose)**되었습니다."
    else:
        hydro_text = f"Sucrose 실측값이 {hplc_suc:.2f}% 잔류하고 있습니다. 열처리 조건에 따라 부분 가수분해된 상태입니다."

    st.markdown(f"- **Sucrose 가수분해 평가**: {hydro_text}")

    if complex_source_name != "복합당원":
        if abs(abs_diff) <= 2.0:
            eval_msg = f"실효 당농도가 스펙 범위 내에서 안정적으로 유지되고 있습니다 (차이: {abs_diff:+.2f}%p)."
        elif abs_diff > 2.0:
            eval_msg = f"실효 당농도가 스펙 대비 {abs_diff:+.2f}%p 높게 측정되었습니다. 원료 농축 상태 또는 칭량 오차를 확인하십시오."
        else:
            eval_msg = f"실효 당농도가 스펙 대비 {abs_diff:+.2f}%p 낮게 측정되었습니다. 수분 흡습 또는 열열화 가능성이 있습니다."
        st.markdown(
            f"- **{complex_source_name} 품질 변동 분석**: {eval_msg}"
        )

    st.markdown(
        "- **배지 조제 권고사항**: 선택된 당원의 투입 비율과 HPLC 측정된 당 조성 결과를 반영하여 차기 배지 칭량 레시피를 보정하십시오."
    )

    st.markdown("---")

    # --- 5. Step별 상세 계산 과정 ---
    with st.expander(
        "🔍 자세한 Step별 계산 과정 및 데이터 보기 (클릭 시 펼침)",
        expanded=False,
    ):
        st.markdown("### 📐 단계별 상세 역산 가이드")

        # Step 1
        st.markdown(
            """<div class="step-card">
            <div class="step-title">[Step 1] 원료 투입량 및 멸균 후 총 당 몰수 산출</div>
            선택된 원료의 순도를 감안한 실제 칭량 투입량(g/L)과 HPLC 측정값 기반의 몰농도를 산출합니다.
        </div>""",
            unsafe_allow_html=True,
        )

        s1_col1, s1_col2 = st.columns(2)
        with s1_col1:
            st.caption("📌 **원료별 실제 칭량 투입량 (g/L)**")
            input_list = []
            if "포도당" in selected_sources:
                input_list.append(
                    [
                        "포도당",
                        f"{res['actual_glu_pct']:.4f} %",
                        f"{res['g_l_glu']:.2f} g/L",
                    ]
                )
            if "액당" in selected_sources:
                input_list.append(
                    [
                        "액당",
                        f"{res['actual_liq_pct']:.4f} %",
                        f"{res['g_l_liq']:.2f} g/L",
                    ]
                )
            if "정제당" in selected_sources:
                input_list.append(
                    [
                        "정제당",
                        f"{res['actual_ref_pct']:.4f} %",
                        f"{res['g_l_ref']:.2f} g/L",
                    ]
                )
            if "당밀" in selected_sources:
                input_list.append(
                    [
                        "당밀",
                        f"{res['actual_mol_pct']:.4f} %",
                        f"{res['g_l_mol']:.2f} g/L",
                    ]
                )

            df_step1_input = pd.DataFrame(
                input_list, columns=["당원", "칭량 비율(w/v%)", "칭량 농도(g/L)"]
            )
            st.dataframe(
                df_step1_input, use_container_width=True, hide_index=True
            )

        with s1_col2:
            st.caption("📌 **HPLC 실측 당의 C6 등가 몰농도 (mol/L)**")
            df_step1_hplc = pd.DataFrame(
                [
                    ["Sucrose", f"{hplc_suc:.2f} %", f"{res['m_suc_meas']:.4f} mol/L"],
                    ["Glucose", f"{hplc_glu:.2f} %", f"{res['m_glu_meas']:.4f} mol/L"],
                    [
                        "Fructose",
                        f"{hplc_fru:.2f} %",
                        f"{res['m_fru_meas']:.4f} mol/L",
                    ],
                    [
                        "총 C6 등가 몰수합",
                        "-",
                        f"**{res['m_total_meas']:.4f} mol/L**",
                    ],
                ],
                columns=["성분", "HPLC 측정값", "몰농도 (mol/L)"],
            )
            st.dataframe(
                df_step1_hplc, use_container_width=True, hide_index=True
            )

        st.markdown("---")

        # Step 2
        st.markdown(
            f"""<div class="step-card">
            <div class="step-title">[Step 2] 단일 당원 유래 몰농도 분리 & 차감</div>
            HPLC 총 몰수에서 단일 당원(포도당/액당) 투입분을 차감하여 {complex_source_name} 유래 몰수만 추출합니다.
        </div>""",
            unsafe_allow_html=True,
        )

        s2_col1, s2_col2 = st.columns([2, 1])
        with s2_col1:
            st.latex(
                r"M_{\text{"
                + complex_source_name
                + r" 유래}} = M_{\text{HPLC 총몰수}} - M_{\text{포도당}} - M_{\text{액당}}"
            )
            step2_list = [
                ["HPLC 총 C6 등가 몰수", f"{res['m_total_meas']:.4f} mol/L"]
            ]
            if "포도당" in selected_sources:
                step2_list.append(
                    ["포도당 유래 몰수 차감액", f"- {res['m_glu_powder']:.4f} mol/L"]
                )
            if "액당" in selected_sources:
                step2_list.append(
                    ["액당 유래 몰수 차감액", f"- {res['m_liq_contrib']:.4f} mol/L"]
                )

            step2_list.append(
                [
                    f"{complex_source_name} 유래 순수 몰수",
                    f"**{res['m_remaining']:.4f} mol/L**",
                ]
            )

            df_step2 = pd.DataFrame(step2_list, columns=["구분", "몰농도 (mol/L)"])
            st.dataframe(df_step2, use_container_width=True, hide_index=True)

        st.markdown("---")

        # Step 3
        st.markdown(
            f"""<div class="step-card">
            <div class="step-title">[Step 3] {complex_source_name} 유래 당 농도 역산 (g/L)</div>
            차감 후 잔여 몰농도를 질량 농도(g/L)로 환산합니다.
        </div>""",
            unsafe_allow_html=True,
        )
        st.latex(
            r"\text{"
            + complex_source_name
            + r" 유래 당 농도 (g/L)} = M_{\text{"
            + complex_source_name
            + r" 유래 (mol/L)}} \times 180.16"
        )
        complex_g_l = res["m_remaining"] * MW_GLU
        st.info(
            f"💡 **역산된 {complex_source_name} 유래 당 농도**: `{complex_g_l:.2f} g/L`"
        )

        st.markdown("---")

        # Step 4
        st.markdown(
            f"""<div class="step-card">
            <div class="step-title">[Step 4] 최종 {complex_source_name} 당농도 순도 및 오차 산출 (%)</div>
            {complex_source_name} 투입량 대비 역산된 당 질량을 통해 실제 농도(순도) 및 스펙 대비 오차율을 최종 계산합니다.
        </div>""",
            unsafe_allow_html=True,
        )
        s4_col1, s4_col2 = st.columns(2)
        with s4_col1:
            st.metric(
                f"역산된 {complex_source_name} 당농도(순도)",
                f"{res['actual_complex_purity']:.2f}%",
            )
        with s4_col2:
            st.metric("스펙 대비 차이/오차", delta_str)
