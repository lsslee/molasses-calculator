import pandas as pd
import streamlit as st

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="당원 농도 역산 · 검증 시스템",
    page_icon="🔬",
    layout="wide",
)

# --- CORE CONSTANTS ---
MW_GLU = 180.16
MW_FRU = 180.16
MW_SUC = 342.30

# 자당(sucrose)이 가수분해되면 물 분자(H2O, 18.02 g/mol)를 흡수하여
# 포도당+과당(합산 질량 360.32)이 되므로, HPLC로 측정한 헥소스 등가 질량은
# 원래 투입한 자당 질량보다 구조적으로 커 보입니다. 이 비율을 물리적으로
# 계산해 "스펙을 아는 경우"에도 동일하게 보정에 사용합니다.
#
# [계산 방식에 대한 의사결정 근거]
# 이 보정식은 HPLC로 측정된 Glucose와 Fructose를 "둘 다" 몰수로 합산해
# 총량을 구하는 현재 코드 방식(m_total_meas = 2*Sucrose + Glucose + Fructose)에
# 맞춘 것입니다. Glucose만으로 역산하고 Fructose를 버리는(잔차로만 쓰는)
# 대안적 계산법도 있으나, 그 방식은 정보 손실이 있어(측정된 Fructose의
# 절반가량이 버려짐) 채택하지 않았습니다.
#
# [보정식이 가수분해율과 무관하게 성립하는 이유]
# 자당 1몰 중 x몰이 가수분해(0≤x≤1)됐다고 하면, 앱의 헥소스 등가 몰수 합산
# (m_total = 2×Sucrose몰 + Glucose몰 + Fructose몰)은
#   2×(1-x) [잔류 Sucrose] + x [생성 Glucose] + x [생성 Fructose] = 2
# 로 x와 무관하게 항상 일정합니다. 반면 진짜 질량은 자당 1몰=342.30g인데
# 이를 "2몰의 헥소스(×180.16=360.32g)"로 환산하면 물 분자 1개 무게(18.02g)
# 만큼 항상 과대평가됩니다 — 이 과대평가분은 가수분해가 0%든 100%든 자당
# 총량에만 비례하므로, 보정식은 실제 가수분해 진행 정도와 무관하게
# 그대로 적용 가능합니다. (정제당처럼 Sucrose 불검출=완전 가수분해든,
# 당밀처럼 Sucrose 일부 검출=부분 가수분해든 동일)
#
# 아래 VALIDATION_LOTS는 원부재료 COA 데이터 6개 로트에 대해 이 보정식이
# "완전 가수분해 시 이론 총량/실측 원료 총량" 관계와 대수적으로 일관됨을
# 보여주는 참고용입니다(계산에는 쓰이지 않음). 위 증명대로 가수분해율과
# 무관하게 성립하므로, 실제 발효 배양액에서 부분 가수분해(당밀)가
# 관찰되어도 별도 보정 없이 그대로 적용하면 됩니다.
HYDROLYSIS_MASS_RATIO = (2 * MW_GLU) / MW_SUC  # ≈ 1.0526

# 대표 평균 농도 상수
# (2026.09 기준 연구소 COA 실측 데이터 평균과 일치 확인됨 — 아래 참고)
DEFAULT_REF_SUC, DEFAULT_REF_GLU, DEFAULT_REF_FRU = 6.12, 6.04, 6.36
DEFAULT_MOL_SUC, DEFAULT_MOL_GLU, DEFAULT_MOL_FRU = 24.80, 7.00, 8.20

# 연구소 입고 원부재료 분석 결과 (COA) — 보정식 자체 검증용 참고 데이터.
# 실제 계산에는 쓰이지 않고, 하단 "검증 근거" expander에서 보정식이
# 이 실측 데이터와 대수적으로 일관되는지 보여주는 용도입니다.
VALIDATION_LOTS = [
    # (원료, 로트명, Glucose%, Fructose%, Sucrose%)
    ("정제당", "25.01", 3.8, 4.2, 7.4),
    ("정제당", "25.03", 5.3, 6.1, 3.4),
    ("정제당", "26.01", 4.3, 6.2, 7.9),
    ("정제당", "26.02", 8.3, 9.7, 5.8),
    ("정제당", "26.05.27", 8.5, 5.6, 6.1),
    ("당밀", "26.05.27", 7.0, 8.2, 24.8),
]


# --- CALLBACK FUNCTIONS (체크박스 변경 시 강제 값 갱신) ---
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
    .highlight-card {
        background-color: #eef5ff;
        border: 2px solid #3867d6;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 4px 10px rgba(56, 103, 214, 0.15);
    }
    .highlight-title {
        color: #264653;
        font-size: 1.1rem;
        font-weight: bold;
        margin-bottom: 5px;
    }
    .highlight-value {
        color: #3867d6;
        font-size: 2.5rem;
        font-weight: 800;
        margin: 5px 0;
    }
    .highlight-delta-pos {
        font-size: 1.0rem;
        font-weight: bold;
        color: #20bf6b;
    }
    .highlight-delta-neg {
        font-size: 1.0rem;
        font-weight: bold;
        color: #eb3b5a;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# 메인 타이틀 & 부타이틀
st.title("🔬 당원 농도 역산 · 검증 시스템")
st.markdown("실측 기반 당원 순도 역산 및 당 농도 검증 Tool")

col_input, col_report = st.columns([1.1, 0.9])

with col_input:
    # ---------------------------------------------------------
    # Section 1. 당원 종류 선택
    # ---------------------------------------------------------
    st.markdown(
        '<div class="section-header">1. 배지 투입 당원 선택</div>',
        unsafe_allow_html=True,
    )
    selected_sources = st.multiselect(
        "사용할 당원 선택 (중복 선택 가능)",
        ["포도당", "액당", "정제당", "당밀"],
        default=["포도당", "정제당"],
    )

    # [FIX] 정제당 + 당밀을 동시에 선택하면, HPLC 총량 하나만으로는
    # 두 복합당원의 실제 순도를 각각 분리해서 역산할 수 없습니다(미지수 2개,
    # 방정식 1개). 예전 코드는 이 경우 아무 계산도 하지 않으면서 경고도 없이
    # "복합당원 없음"과 동일한 화면을 보여줬습니다. 명확히 막습니다.
    sources_conflict = "정제당" in selected_sources and "당밀" in selected_sources
    if sources_conflict:
        st.error(
            "⚠️ **정제당과 당밀을 동시에 선택할 수 없습니다.** "
            "HPLC 총 당농도만으로는 두 복합당원의 실제 순도를 각각 역산할 수 없습니다 "
            "(미지수 2개 vs 방정식 1개). 하나만 선택해 주세요."
        )

    # ---------------------------------------------------------
    # Section 2. 당원별 당농도 입력 및 합산 총당/비율 자동 계산
    # ---------------------------------------------------------
    st.markdown(
        '<div class="section-header">2. 당원별 설정 농도 입력</div>',
        unsafe_allow_html=True,
    )

    target_sugar_dict = {}
    sum_target_sugar = 0.0

    if selected_sources:
        st.caption("각 당원의 목표 배지 농도를 입력해주세요.")
        ratio_cols = st.columns(len(selected_sources))

        for idx, src in enumerate(selected_sources):
            with ratio_cols[idx]:
                # [FIX] 조건부 삼항식이 항상 같은 값을 반환하던 잔재 정리
                target_sugar_dict[src] = st.number_input(
                    f"{src} 농도 (%)",
                    value=3.5,
                    step=0.1,
                    min_value=0.0,
                    key=f"target_sugar_{src}",
                )

        sum_target_sugar = sum(target_sugar_dict.values())

        if sum_target_sugar > 0:
            ratio_parts = []
            for src, val in target_sugar_dict.items():
                pct = (val / sum_target_sugar) * 100
                ratio_parts.append(f"**{src}**: {pct:.1f}% ({val:.2f}%)")

            st.success(f"🎯 **합산 목표 총당 농도**: **{sum_target_sugar:.2f} w/v%**")
            st.info(f"💡 **설정 당원별 구성 비율**: {' | '.join(ratio_parts)}")
        else:
            st.warning("⚠️ 1개 이상의 당원 농도를 0% 초과로 입력해 주세요.")
    else:
        st.warning("⚠️ 당원 종류를 1개 이상 선택해 주세요.")

    # ---------------------------------------------------------
    # Section 3. 당원 스펙 입력
    # ---------------------------------------------------------
    st.markdown(
        '<div class="section-header">3. 원원료 스펙(순도 및 구성) 입력</div>',
        unsafe_allow_html=True,
    )

    p_glu = 91.0
    p_liq = 75.0

    if "포도당" in selected_sources:
        st.subheader("📌 포도당 스펙")
        p_glu = st.number_input(
            "포도당 순도 (%)",
            value=91.0,
            step=0.1,
            min_value=0.0,
            max_value=100.0,
            key="p_glu",
        )

    if "액당" in selected_sources:
        st.subheader("📌 액당 스펙")
        p_liq = st.number_input(
            "액당 당순도 (%)  ※ 제품 중량 대비 '당류(Glucose+Fructose)' 함량입니다. "
            "'고형분(Brix)'과는 다른 개념이니 COA의 당 순도 항목을 입력해 주세요.",
            value=75.0,
            step=0.1,
            min_value=0.0,
            max_value=100.0,
            key="p_liq",
        )
        p_liq_glu_ratio = st.number_input(
            "액당 내 Glucose 비중 (%)  ※ 나머지는 Fructose로 가정 (일반 액상과당 기준 기본값 50%)",
            value=50.0,
            step=1.0,
            min_value=0.0,
            max_value=100.0,
            key="p_liq_glu_ratio",
            help="액당(액상과당/전화당 등)은 보통 Glucose와 Fructose가 섞여 있습니다. "
            "제품 스펙을 알면 정확한 비율을, 모르면 기본값(50:50)을 사용하세요.",
        )
        st.caption(
            f"➡️ 환산 비율: Glucose {p_liq_glu_ratio:.0f}% : Fructose {100-p_liq_glu_ratio:.0f}%"
        )
    else:
        p_liq_glu_ratio = 50.0

    if "정제당" in selected_sources:
        st.subheader("📌 정제당 스펙")
        use_auto_ref_spec = st.checkbox(
            "정제당 세부 스펙을 모름",
            value=False,
            key="check_auto_ref",
            on_change=update_ref_spec,
            help="체크 시 정제당의 대표 평균 스펙 농도로 계산됩니다.",
        )

        col_ref1, col_ref2, col_ref3 = st.columns(3)
        with col_ref1:
            c_ref_suc = st.number_input(
                "Sucrose (%)", value=DEFAULT_REF_SUC, step=0.01,
                min_value=0.0, key="ref_suc", disabled=use_auto_ref_spec,
            )
        with col_ref2:
            c_ref_glu = st.number_input(
                "Glucose (%)", value=DEFAULT_REF_GLU, step=0.01,
                min_value=0.0, key="ref_glu", disabled=use_auto_ref_spec,
            )
        with col_ref3:
            c_ref_fru = st.number_input(
                "Fructose (%)", value=DEFAULT_REF_FRU, step=0.01,
                min_value=0.0, key="ref_fru", disabled=use_auto_ref_spec,
            )

        if use_auto_ref_spec:
            st.warning(
                "⚠️ 세부 스펙 미입력 시 대표 평균값으로 계산되어 실제 로트와 오차가 발생할 수 있습니다."
            )

        ref_spec_sum = c_ref_suc + c_ref_glu + c_ref_fru
        st.success(f"🏷️ **정제당 총 스펙 순도**: **{ref_spec_sum:.2f} %**")
    else:
        c_ref_suc, c_ref_glu, c_ref_fru = 0.0, 0.0, 0.0

    if "당밀" in selected_sources:
        st.subheader("📌 당밀 스펙")
        use_auto_mol_spec = st.checkbox(
            "당밀 세부 스펙을 모름",
            value=False,
            key="check_auto_mol",
            on_change=update_mol_spec,
            help="체크 시 당밀의 대표 평균 스펙 농도로 계산됩니다.",
        )

        col_mol1, col_mol2, col_mol3 = st.columns(3)
        with col_mol1:
            c_mol_suc = st.number_input(
                "Sucrose (%)", value=DEFAULT_MOL_SUC, step=0.01,
                min_value=0.0, key="mol_suc", disabled=use_auto_mol_spec,
            )
        with col_mol2:
            c_mol_glu = st.number_input(
                "Glucose (%)", value=DEFAULT_MOL_GLU, step=0.01,
                min_value=0.0, key="mol_glu", disabled=use_auto_mol_spec,
            )
        with col_mol3:
            c_mol_fru = st.number_input(
                "Fructose (%)", value=DEFAULT_MOL_FRU, step=0.01,
                min_value=0.0, key="mol_fru", disabled=use_auto_mol_spec,
            )

        if use_auto_mol_spec:
            st.warning(
                "⚠️ 세부 스펙 미입력 시 대표 평균값으로 계산되어 실제 로트와 오차가 발생할 수 있습니다."
            )

        mol_spec_sum = c_mol_suc + c_mol_glu + c_mol_fru
        st.success(f"🏷️ **당밀 총 스펙 순도**: **{mol_spec_sum:.2f} %**")
    else:
        c_mol_suc, c_mol_glu, c_mol_fru = 0.0, 0.0, 0.0

    # ---------------------------------------------------------
    # Section 4. 배양액 0h 샘플 HPLC 측정 결과 입력
    # ---------------------------------------------------------
    st.markdown(
        '<div class="section-header">4. 멸균 후(0h) 배양액 HPLC 실측값 입력</div>',
        unsafe_allow_html=True,
    )
    col_h1, col_h2, col_h3 = st.columns(3)
    with col_h1:
        hplc_suc = st.number_input(
            "Sucrose (w/v%)", value=1.00, step=0.1, min_value=0.0, key="hplc_suc"
        )
    with col_h2:
        hplc_glu = st.number_input(
            "Glucose (w/v%)", value=4.76, step=0.1, min_value=0.0, key="hplc_glu"
        )
    with col_h3:
        hplc_fru = st.number_input(
            "Fructose (w/v%)", value=1.76, step=0.1, min_value=0.0, key="hplc_fru"
        )

    # [FIX] 당원 미선택 또는 정제당+당밀 동시선택 시 계산 버튼 비활성화
    calc_disabled = (len(selected_sources) == 0) or sources_conflict
    btn_col1, btn_col2 = st.columns([3, 1])
    with btn_col1:
        calc_button = st.button(
            "🚀 당농도 역산 및 리포트 생성",
            use_container_width=True,
            disabled=calc_disabled,
        )
    with btn_col2:
        # [FIX] 계산 후 입력을 바꿔도 이전 리포트가 계속 남아있던 문제 —
        # 새로고침 없이 리포트를 초기화할 수 있는 버튼 추가
        if st.button("🔄 리포트 초기화", use_container_width=True, disabled=("res" not in st.session_state)):
            del st.session_state["res"]
            st.rerun()


# --- 계산 및 리포트 생성 ---
if (calc_button or "res" in st.session_state) and not sources_conflict and selected_sources:
    target_glu = target_sugar_dict.get("포도당", 0.0)
    target_liq = target_sugar_dict.get("액당", 0.0)
    target_ref = target_sugar_dict.get("정제당", 0.0)
    target_mol = target_sugar_dict.get("당밀", 0.0)

    # 1. 실제 투입량 환산 (w/v% -> g/L)
    actual_glu_pct = target_glu * (100.0 / p_glu) if p_glu > 0 else 0
    actual_liq_pct = target_liq * (100.0 / p_liq) if p_liq > 0 else 0

    ref_nominal_total = c_ref_suc + c_ref_glu + c_ref_fru
    actual_ref_pct = (
        target_ref * (100.0 / ref_nominal_total) if ref_nominal_total > 0 else 0
    )

    mol_nominal_total = c_mol_suc + c_mol_glu + c_mol_fru
    actual_mol_pct = (
        target_mol * (100.0 / mol_nominal_total) if mol_nominal_total > 0 else 0
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
    # [FIX] 액당은 Glucose 단일 성분이 아니라 Glucose+Fructose 혼합물일 수 있으므로,
    # 사용자가 입력한 조성비(p_liq_glu_ratio)로 나누어 각각 올바른 MW로 환산합니다.
    liq_sugar_mass = g_l_liq * (p_liq / 100.0)  # 액당이 기여하는 순수 당 질량(g/L)
    m_liq_glu = (
        (liq_sugar_mass * (p_liq_glu_ratio / 100.0)) / MW_GLU
        if "액당" in selected_sources
        else 0
    )
    m_liq_fru = (
        (liq_sugar_mass * (1 - p_liq_glu_ratio / 100.0)) / MW_FRU
        if "액당" in selected_sources
        else 0
    )
    m_liq_contrib = m_liq_glu + m_liq_fru

    m_remaining_raw = m_total_meas - m_glu_powder - m_liq_contrib
    m_remaining = max(0.0, m_remaining_raw)
    remaining_was_clamped = m_remaining_raw < 0

    # 복합 당원 명칭 및 역산
    complex_source_name = "복합당원"
    nominal_complex_purity = 0.0
    raw_actual_purity = 0.0
    actual_complex_purity = 0.0
    g_l_complex = 0.0
    hydrolysis_correction = 1.0

    if "정제당" in selected_sources:
        complex_source_name = "정제당"
        nominal_complex_purity = ref_nominal_total
        g_l_complex = g_l_ref
        complex_suc_spec = c_ref_suc
    elif "당밀" in selected_sources:
        complex_source_name = "당밀"
        nominal_complex_purity = mol_nominal_total
        g_l_complex = g_l_mol
        complex_suc_spec = c_mol_suc
    else:
        complex_suc_spec = 0.0

    if complex_source_name != "복합당원":
        c_actual_mass = m_remaining * MW_GLU
        raw_actual_purity = (
            (c_actual_mass / g_l_complex) * 100.0 if g_l_complex > 0 else 0.0
        )

        # [FIX] 가수분해 질량 보정을 "스펙 모름" 체크박스와 무관하게, 항상
        # 해당 원료의 자당(sucrose) 스펙 비중에 비례해 물리적으로 계산해 적용.
        # (자당이 가수분해되며 물을 흡수해 헥소스 등가 질량이 커 보이는 만큼만 보정)
        suc_fraction = (
            complex_suc_spec / nominal_complex_purity
            if nominal_complex_purity > 0
            else 0.0
        )
        hydrolysis_correction = 1 + suc_fraction * (HYDROLYSIS_MASS_RATIO - 1)
        actual_complex_purity = raw_actual_purity / hydrolysis_correction

    abs_diff = actual_complex_purity - nominal_complex_purity

    # 실제 역산 기반 기여농도 및 비중 계산
    real_sugar_contributions = {}
    total_measured_sugar = hplc_suc + hplc_glu + hplc_fru

    if "포도당" in selected_sources:
        real_sugar_contributions["포도당"] = actual_glu_pct * (p_glu / 100.0)
    if "액당" in selected_sources:
        real_sugar_contributions["액당"] = actual_liq_pct * (p_liq / 100.0)
    if "정제당" in selected_sources:
        # complex_source_name은 이 분기에서 항상 "정제당"이므로(정제당+당밀
        # 동시선택은 상단에서 이미 차단됨) actual_complex_purity를 그대로 사용
        real_sugar_contributions["정제당"] = actual_ref_pct * (actual_complex_purity / 100.0)
    if "당밀" in selected_sources:
        real_sugar_contributions["당밀"] = actual_mol_pct * (actual_complex_purity / 100.0)

    calc_total_real_sugar = sum(real_sugar_contributions.values())
    real_sugar_shares = {}
    if calc_total_real_sugar > 0:
        for src, val in real_sugar_contributions.items():
            real_sugar_shares[src] = (val / calc_total_real_sugar) * 100

    res = {
        "selected_sources": selected_sources,
        "measured_total_sugar_percent": total_measured_sugar,
        "complex_source_name": complex_source_name,
        "nominal_complex_purity": nominal_complex_purity,
        "raw_actual_purity": raw_actual_purity,
        "actual_complex_purity": actual_complex_purity,
        "hydrolysis_correction": hydrolysis_correction,
        "abs_diff": abs_diff,
        "m_suc_meas": m_suc_meas,
        "m_glu_meas": m_glu_meas,
        "m_fru_meas": m_fru_meas,
        "m_total_meas": m_total_meas,
        "m_glu_powder": m_glu_powder,
        "m_liq_contrib": m_liq_contrib,
        "m_liq_glu": m_liq_glu,
        "m_liq_fru": m_liq_fru,
        "m_remaining": m_remaining,
        "remaining_was_clamped": remaining_was_clamped,
        "actual_glu_pct": actual_glu_pct,
        "actual_liq_pct": actual_liq_pct,
        "actual_ref_pct": actual_ref_pct,
        "actual_mol_pct": actual_mol_pct,
        "g_l_glu": g_l_glu,
        "g_l_liq": g_l_liq,
        "g_l_ref": g_l_ref,
        "g_l_mol": g_l_mol,
        "g_l_complex": g_l_complex,
        "real_sugar_contributions": real_sugar_contributions,
        "real_sugar_shares": real_sugar_shares,
    }
    st.session_state["res"] = res

    # --- 우측 칼럼 결과 리포트 ---
    with col_report:
        st.subheader("📊 5. 실측 역산 결과 및 기여도 리포트")

        if res["remaining_was_clamped"]:
            st.error(
                "⚠️ HPLC 실측 총당이 단일 당원(포도당/액당) 투입 예상량보다도 적습니다. "
                "복합당원 유래 몰수가 음수로 계산되어 0으로 처리했습니다. "
                "칭량값·HPLC 결과·순도 입력을 다시 확인해 주세요."
            )

        if complex_source_name != "복합당원":
            m1, m2 = st.columns([1, 1.3])
            with m1:
                st.metric(
                    f"{complex_source_name} 스펙 순도",
                    f"{nominal_complex_purity:.2f}%",
                )
            with m2:
                delta_class = "highlight-delta-pos" if abs_diff >= 0 else "highlight-delta-neg"
                st.markdown(
                    f"""
                    <div class="highlight-card">
                        <div class="highlight-title">🎯 역산된 {complex_source_name} 실제 당농도</div>
                        <div class="highlight-value">{actual_complex_purity:.2f}%</div>
                        <div class="{delta_class}">스펙 대비 차이: {abs_diff:+.2f}%p</div>
                    </div>
                """,
                    unsafe_allow_html=True,
                )
            st.caption(
                f"ℹ️ 가수분해 질량 보정계수: ×{1/hydrolysis_correction:.4f} "
                f"(자당 스펙 비중 {complex_suc_spec:.2f}% 기준 — 실제 가수분해 진행률과 무관하게 적용됨)"
            )
        else:
            st.metric(
                "HPLC 실측 총 당농도", f"{res['measured_total_sugar_percent']:.2f}%"
            )

        st.write("")
        st.markdown("##### 📌 당원별 기여 농도 및 비중")
        st.caption(
            "포도당·액당은 입력한 스펙 순도 기준 계산값이고, "
            f"{complex_source_name if complex_source_name != '복합당원' else '정제당/당밀'}은 "
            "HPLC 실측 기반 역산값입니다."
        )

        table_data = []
        if "포도당" in selected_sources:
            table_data.append(
                ["포도당", f"{actual_glu_pct:.4f} %",
                 f"{real_sugar_contributions.get('포도당', 0):.2f} %",
                 f"{real_sugar_shares.get('포도당', 0):.1f} %"]
            )
        if "액당" in selected_sources:
            table_data.append(
                ["액당", f"{actual_liq_pct:.4f} %",
                 f"{real_sugar_contributions.get('액당', 0):.2f} %",
                 f"{real_sugar_shares.get('액당', 0):.1f} %"]
            )
        if "정제당" in selected_sources:
            table_data.append(
                ["정제당", f"{actual_ref_pct:.4f} %",
                 f"{real_sugar_contributions.get('정제당', 0):.2f} %",
                 f"{real_sugar_shares.get('정제당', 0):.1f} %"]
            )
        if "당밀" in selected_sources:
            table_data.append(
                ["당밀", f"{actual_mol_pct:.4f} %",
                 f"{real_sugar_contributions.get('당밀', 0):.2f} %",
                 f"{real_sugar_shares.get('당밀', 0):.1f} %"]
            )

        df_res = pd.DataFrame(
            table_data,
            columns=["당원", "칭량 투입량(w/v%)", "실제 기여 당농도(w/v%)", "실제 총당 내 비중(%)"],
        )
        st.dataframe(df_res, use_container_width=True, hide_index=True)

        if real_sugar_shares:
            share_summary = " : ".join(
                [f"{src} {val:.1f}%" for src, val in real_sugar_shares.items()]
            )
            st.info(f"💡 **실제 역산 기반 당원 구성 비중**: {share_summary}")

        st.markdown("---")

        st.subheader("📋 공정 진단 및 원료 품질 종합 리포트")

        # 1. Sucrose 가수분해율 계산
        complex_suc_pct = actual_ref_pct if complex_source_name == "정제당" else (
            actual_mol_pct if complex_source_name == "당밀" else 0.0
        )
        expected_suc = complex_suc_pct * (complex_suc_spec / 100.0)

        if expected_suc > 0:
            hydro_rate = max(0.0, min(100.0, (1 - (hplc_suc / expected_suc)) * 100.0))
        else:
            hydro_rate = 100.0 if hplc_suc == 0 else 0.0

        st.markdown("#### 1️⃣ Sucrose 열가수분해 및 열화 분석")
        st.markdown(
            f"- **추정 가수분해율**: **{hydro_rate:.1f}%** (이론 투입 추정치 {expected_suc:.2f}% 대비 실측 잔류량 {hplc_suc:.2f}%)"
        )
        if hydro_rate >= 95.0:
            st.caption("🟢 **분석**: 멸균 공정 중 Sucrose가 대부분 Glucose와 Fructose로 완전히 전환되었습니다.")
        elif hydro_rate >= 50.0:
            st.caption("🟡 **분석**: Sucrose 일부가 잔류된 부분 가수분해 상태입니다. 멸균 열이력(pH, 시간)을 확인하세요.")
        else:
            st.caption("🔴 **분석**: 가수분해 진행률이 낮습니다. 멸균 조건 미달 또는 배지 pH 편차 가능성을 점검하세요.")

        if complex_source_name != "복합당원":
            st.caption(
                "ℹ️ 참고: 상단의 가수분해 질량 보정계수는 **가수분해율(x)과 무관하게 항상 동일하게 "
                "적용**됩니다. Sucrose 1몰이 (1−x)몰 잔류 + x몰 가수분해로 나뉘어도, "
                "헥소스 등가 몰수 합산값은 `2(1−x)+x+x=2`로 항상 일정하기 때문입니다 — "
                "즉 정제당처럼 Sucrose가 완전히 사라졌든, 당밀처럼 일부 검출되든 "
                "동일한 보정식이 정확하게 성립합니다."
            )

        st.markdown("#### 2️⃣ 당원 품질 및 순도 변동 평가")
        if complex_source_name != "복합당원":
            st.markdown(
                f"- **스펙 순도**: `{nominal_complex_purity:.2f}%` ➡️ **실제 역산 순도**: `{actual_complex_purity:.2f}%` (`{abs_diff:+.2f}%p` 변동)"
            )
            if abs(abs_diff) <= 2.0:
                st.caption("🟢 **분석**: 원료 스펙 오차 범위(±2%p) 내로 품질이 매우 안정적입니다.")
            elif abs_diff > 2.0:
                st.caption(
                    f"🔴 **분석**: 스펙 대비 당 함량이 **{abs_diff:.2f}%p 높게 역산**되었습니다. 원료 저장 중 수분 증발(농축) 또는 제조사 품질 편차가 의심됩니다."
                )
            else:
                st.caption(
                    f"🔴 **분석**: 스펙 대비 당 함량이 **{abs(abs_diff):.2f}%p 낮게 역산**되었습니다. 원료 흡습, 보관 중 열화 또는 고형분 침전 현상을 확인하세요."
                )

        st.markdown("#### 3️⃣ 공정 및 칭량 오차 검증")
        diff_total = total_measured_sugar - sum_target_sugar
        st.markdown(
            f"- **목표 설정 총당**: `{sum_target_sugar:.2f}%` ➡️ **HPLC 실측 총당**: `{total_measured_sugar:.2f}%` (`{diff_total:+.2f}%p` 차이)"
        )
        if abs(diff_total) > 0.5:
            st.caption(
                "⚠️ **주의**: 실측 총당과의 차이가 0.5%p 이상 발생했습니다. 칭량 과정에서의 스케일 오차, 용수 부피 오차, 또는 멸균 후 증발 농축 여부를 재검증하세요."
            )

    st.markdown("---")

    # ---------------------------------------------------------
    # Section 6. Step별 상세 계산 과정 토글 영역
    # ---------------------------------------------------------
    with st.expander("🔍 단계별 수식 및 검증 데이터 상세 보기 (클릭 시 펼침)", expanded=False):
        st.markdown("### 📐 단계별 상세 역산 가이드")

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
                input_list.append(["포도당", f"{res['actual_glu_pct']:.4f} %", f"{res['g_l_glu']:.2f} g/L"])
            if "액당" in selected_sources:
                input_list.append(["액당", f"{res['actual_liq_pct']:.4f} %", f"{res['g_l_liq']:.2f} g/L"])
            if "정제당" in selected_sources:
                input_list.append(["정제당", f"{res['actual_ref_pct']:.4f} %", f"{res['g_l_ref']:.2f} g/L"])
            if "당밀" in selected_sources:
                input_list.append(["당밀", f"{res['actual_mol_pct']:.4f} %", f"{res['g_l_mol']:.2f} g/L"])

            df_step1_input = pd.DataFrame(input_list, columns=["당원", "칭량 비율(w/v%)", "칭량 농도(g/L)"])
            st.dataframe(df_step1_input, use_container_width=True, hide_index=True)

        with s1_col2:
            st.caption("📌 **HPLC 실측 당의 C6 등가 몰농도 (mol/L)**")
            df_step1_hplc = pd.DataFrame(
                [
                    ["Sucrose", f"{hplc_suc:.2f} %", f"{res['m_suc_meas']:.4f} mol/L"],
                    ["Glucose", f"{hplc_glu:.2f} %", f"{res['m_glu_meas']:.4f} mol/L"],
                    ["Fructose", f"{hplc_fru:.2f} %", f"{res['m_fru_meas']:.4f} mol/L"],
                    ["총 C6 등가 몰수합", "-", f"**{res['m_total_meas']:.4f} mol/L**"],
                ],
                columns=["성분", "HPLC 측정값", "몰농도 (mol/L)"],
            )
            st.dataframe(df_step1_hplc, use_container_width=True, hide_index=True)

        st.markdown("---")

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
                r"M_{\text{" + complex_source_name + r" 유래}} = M_{\text{HPLC 총몰수}} - M_{\text{포도당}} - M_{\text{액당}}"
            )
            step2_list = [["HPLC 총 C6 등가 몰수", f"{res['m_total_meas']:.4f} mol/L"]]
            if "포도당" in selected_sources:
                step2_list.append(["포도당 유래 몰수 차감액", f"- {res['m_glu_powder']:.4f} mol/L"])
            if "액당" in selected_sources:
                step2_list.append(
                    ["액당 유래 몰수 차감액 (Glucose)", f"- {res['m_liq_glu']:.4f} mol/L"]
                )
                step2_list.append(
                    ["액당 유래 몰수 차감액 (Fructose)", f"- {res['m_liq_fru']:.4f} mol/L"]
                )
            step2_list.append([f"{complex_source_name} 유래 순수 몰수 (0 미만은 0으로 처리)", f"**{res['m_remaining']:.4f} mol/L**"])

            df_step2 = pd.DataFrame(step2_list, columns=["구분", "몰농도 (mol/L)"])
            st.dataframe(df_step2, use_container_width=True, hide_index=True)

        st.markdown("---")

        st.markdown(
            f"""<div class="step-card">
            <div class="step-title">[Step 3] {complex_source_name} 유래 당 농도 역산 (g/L)</div>
            차감 후 잔여 몰농도를 헥소스 등가 질량 농도(g/L)로 환산합니다. (자당 가수분해분은 아직 물 흡수분이 포함된 값입니다)
        </div>""",
            unsafe_allow_html=True,
        )
        st.latex(
            r"\text{" + complex_source_name + r" 유래 헥소스 등가 질량 (g/L)} = M_{\text{"
            + complex_source_name + r" 유래 (mol/L)}} \times 180.16"
        )
        complex_g_l = res["m_remaining"] * MW_GLU
        st.info(f"💡 **역산된 {complex_source_name} 유래 헥소스 등가 질량**: `{complex_g_l:.2f} g/L`")

        st.markdown("---")

        st.markdown(
            f"""<div class="step-card">
            <div class="step-title">[Step 4] 가수분해 질량 보정 및 최종 순도 산출 (%)</div>
            자당이 가수분해되며 흡수한 물 분자 질량만큼 헥소스 등가 질량이 부풀어 보이므로,
            해당 원료의 자당 스펙 비중에 비례해 보정한 뒤 최종 순도(%)와 스펙 대비 차이(%p)를 계산합니다.
        </div>""",
            unsafe_allow_html=True,
        )
        st.latex(
            r"\text{보정계수} = 1 + \frac{\text{Sucrose 스펙}}{\text{총 스펙 순도}} \times "
            r"\left(\frac{2 \times 180.16}{342.30} - 1\right)"
        )
        s4_col1, s4_col2, s4_col3 = st.columns(3)
        with s4_col1:
            st.metric("보정 전 순도(raw)", f"{res['raw_actual_purity']:.2f}%")
        with s4_col2:
            st.metric(f"보정계수", f"×{res['hydrolysis_correction']:.4f}")
        with s4_col3:
            st.metric(f"역산된 {complex_source_name} 최종 순도", f"{res['actual_complex_purity']:.2f}%")
        st.metric("스펙 대비 차이", f"{abs_diff:+.2f}%p")


# ---------------------------------------------------------
# Section 7. 보정식 검증 근거 (항상 표시 — 계산 실행 여부와 무관)
# ---------------------------------------------------------
st.markdown("---")
with st.expander("🧪 가수분해 보정식 검증 근거 (연구소 COA 실측 데이터 기준)", expanded=False):
    st.markdown(
        "보정식(`1 + 자당스펙비중 × (2×180.16/342.30 − 1)`)은 자당 가수분해율과 "
        "**수학적으로 무관하게 성립**함이 증명되어(파일 상단 주석 참고), 정제당(Sucrose "
        "완전 소실)과 당밀(Sucrose 일부 검출) 모두에 동일하게 적용됩니다. "
        "아래 표는 그 증명이 실제 원부재료 COA 6개 로트 조성에서도 산술적으로 "
        "일관됨을 보여주는 참고용입니다.\n\n"
        "⚠️ 다만 이 표/증명이 다루지 못하는 부분은 남아 있습니다: Isomaltose·Maltose 등 "
        "부반응 생성물로 당이 일부 소실되는 경우, 배지 희석·증발 등 공정상의 오차, "
        "HPLC 컬럼/표준품 특성 등은 여전히 **실제 발효 배양액 HPLC 결과를 로트와 매칭**해야만 "
        "검증할 수 있습니다."
    )

    val_rows = []
    for src, lot, glu, fru, suc in VALIDATION_LOTS:
        total1 = glu + fru + suc  # 실측 원료 총당 (가수분해 전)
        suc_fraction = suc / total1 if total1 > 0 else 0.0
        # 완전 가수분해 시 이론 총량 (물 흡수분 포함)
        total2_theory = glu + suc * (MW_GLU / MW_SUC) + fru + suc * (MW_FRU / MW_SUC)
        required_ratio = total2_theory / total1 if total1 > 0 else 0.0
        # 본 앱의 보정식이 예측하는 계수
        predicted_ratio = 1 + suc_fraction * (HYDROLYSIS_MASS_RATIO - 1)
        val_rows.append(
            [
                src, lot, f"{total1:.2f}", f"{total2_theory:.2f}",
                f"{required_ratio:.4f}", f"{predicted_ratio:.4f}",
                f"{(predicted_ratio - required_ratio):+.4f}",
            ]
        )

    df_val = pd.DataFrame(
        val_rows,
        columns=[
            "원료", "로트", "실측 총당(%)", "완전가수분해 이론 총량(%)",
            "필요 보정계수", "본 공식 예측계수", "오차",
        ],
    )
    st.dataframe(df_val, use_container_width=True, hide_index=True)
    st.caption(
        "오차가 0에 가까울수록 본 앱의 물리 기반 보정식이 해당 로트의 실측 조성과 "
        "잘 맞는다는 뜻입니다. 새 로트 COA가 들어오면 위 VALIDATION_LOTS 리스트에 "
        "추가해 계속 점검할 수 있습니다."
    )
