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
MW_H2O = 18.015  # 수화 반응(가수분해) 보정용 물 분자량

# 대표 평균 농도 상수
DEFAULT_REF_SUC, DEFAULT_REF_GLU, DEFAULT_REF_FRU = 6.12, 6.04, 6.36
DEFAULT_MOL_SUC, DEFAULT_MOL_GLU, DEFAULT_MOL_FRU = 24.80, 7.00, 8.20


# --- CSS (다크모드 및 UI 호환성 개선) ---
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
        margin-top: 15px;
        margin-bottom: 12px;
    }
    .step-card {
        background-color: #f8f9fa;
        color: #212529;
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
    .highlight-title { color: #264653; font-size: 1.1rem; font-weight: bold; }
    .highlight-value { color: #3867d6; font-size: 2.5rem; font-weight: 800; }
    .highlight-delta { font-size: 1.0rem; font-weight: bold; color: #20bf6b; }
    </style>
""",
    unsafe_allow_html=True,
)

# 메인 타이틀
st.title("🔬 당원 농도 역산 · 검증 시스템")
st.caption("실측 기반 당원 순도 역산 및 당 농도 검증 Tool (가수분해 H₂O 결합 보정 적용)")

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

    # ---------------------------------------------------------
    # Section 2. 당원별 설정 농도 입력
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

            st.success(
                f"🎯 **합산 목표 총당 농도**: **{sum_target_sugar:.2f} w/v%**"
            )
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
    c_ref_suc = c_ref_glu = c_ref_fru = 0.0
    c_mol_suc = c_mol_glu = c_mol_fru = 0.0
    correction_factor = 1.0

    if "포도당" in selected_sources:
        st.subheader("📌 포도당 스펙")
        p_glu = st.number_input(
            "포도당 순도 (%)", value=91.0, step=0.1, key="p_glu"
        )

    if "액당" in selected_sources:
        st.subheader("📌 액당 스펙")
        p_liq = st.number_input(
            "액당 순도/고형분 (%)", value=75.0, step=0.1, key="p_liq"
        )

    if "정제당" in selected_sources:
        st.subheader("📌 정제당 스펙")
        use_auto_ref = st.checkbox(
            "정제당 세부 스펙 미상 (평균값 사용)",
            value=False,
            key="check_auto_ref",
            help="체크 시 정제당의 대표 평균 스펙 농도로 자동 설정됩니다.",
        )

        if use_auto_ref:
            c_ref_suc, c_ref_glu, c_ref_fru = (
                DEFAULT_REF_SUC,
                DEFAULT_REF_GLU,
                DEFAULT_REF_FRU,
            )
            correction_factor = 1.030
            st.warning(
                "⚠️ 대표 평균 스펙 사용 시 분석 특성에 따라 소량의 오차가 발생할 수 있습니다."
            )
        else:
            col_ref1, col_ref2, col_ref3 = st.columns(3)
            c_ref_suc = col_ref1.number_input(
                "Sucrose (%)", value=DEFAULT_REF_SUC, step=0.01, key="ref_suc"
            )
            c_ref_glu = col_ref2.number_input(
                "Glucose (%)", value=DEFAULT_REF_GLU, step=0.01, key="ref_glu"
            )
            c_ref_fru = col_ref3.number_input(
                "Fructose (%)", value=DEFAULT_REF_FRU, step=0.01, key="ref_fru"
            )

        ref_spec_sum = c_ref_suc + c_ref_glu + c_ref_fru
        st.success(f"🏷️ **정제당 총 스펙 순도**: **{ref_spec_sum:.2f} %**")

    if "당밀" in selected_sources:
        st.subheader("📌 당밀 스펙")
        use_auto_mol = st.checkbox(
            "당밀 세부 스펙 미상 (평균값 사용)",
            value=False,
            key="check_auto_mol",
            help="체크 시 당밀의 대표 평균 스펙 농도로 자동 설정됩니다.",
        )

        if use_auto_mol:
            c_mol_suc, c_mol_glu, c_mol_fru = (
                DEFAULT_MOL_SUC,
                DEFAULT_MOL_GLU,
                DEFAULT_MOL_FRU,
            )
            correction_factor = 1.031
            st.warning(
                "⚠️ 대표 평균 스펙 사용 시 분석 특성에 따라 소량의 오차가 발생할 수 있습니다."
            )
        else:
            col_mol1, col_mol2, col_mol3 = st.columns(3)
            c_mol_suc = col_mol1.number_input(
                "Sucrose (%)", value=DEFAULT_MOL_SUC, step=0.01, key="mol_suc"
            )
            c_mol_glu = col_mol2.number_input(
                "Glucose (%)", value=DEFAULT_MOL_GLU, step=0.01, key="mol_glu"
            )
            c_mol_fru = col_mol3.number_input(
                "Fructose (%)", value=DEFAULT_MOL_FRU, step=0.01, key="mol_fru"
            )

        mol_spec_sum = c_mol_suc + c_mol_glu + c_mol_fru
        st.success(f"🏷️ **당밀 총 스펙 순도**: **{mol_spec_sum:.2f} %**")

    # ---------------------------------------------------------
    # Section 4. 배양액 0h 샘플 HPLC 측정 결과 입력
    # ---------------------------------------------------------
    st.markdown(
        '<div class="section-header">4. 멸균 후(0h) 배양액 HPLC 실측값 입력</div>',
        unsafe_allow_html=True,
    )
    col_h1, col_h2, col_h3 = st.columns(3)
    hplc_suc = col_h1.number_input(
        "Sucrose (w/v%)", value=1.00, step=0.1, key="hplc_suc"
    )
    hplc_glu = col_h2.number_input(
        "Glucose (w/v%)", value=4.76, step=0.1, key="hplc_glu"
    )
    hplc_fru = col_h3.number_input(
        "Fructose (w/v%)", value=1.76, step=0.1, key="hplc_fru"
    )


# --- 계산 및 결과 리포트 출력 ---
with col_report:
    st.subheader("📊 5. 실측 역산 결과 및 기여도 리포트")

    # 1. 예외 처리: 정제당과 당밀 동시 선택 시
    if "정제당" in selected_sources and "당밀" in selected_sources:
        st.error(
            "⚠️ **계산 불가**: '정제당'과 '당밀'이 동시에 투입된 경우 단일 역산이 불가능합니다. 둘 중 하나만 선택해 주세요."
        )
    elif not selected_sources:
        st.info("👈 좌측에서 1개 이상의 당원을 선택해 주세요.")
    else:
        target_glu = target_sugar_dict.get("포도당", 0.0)
        target_liq = target_sugar_dict.get("액당", 0.0)
        target_ref = target_sugar_dict.get("정제당", 0.0)
        target_mol = target_sugar_dict.get("당밀", 0.0)

        ref_nominal_total = c_ref_suc + c_ref_glu + c_ref_fru
        mol_nominal_total = c_mol_suc + c_mol_glu + c_mol_fru

        # 투입량 환산 (w/v% -> g/L)
        actual_glu_pct = (
            target_glu * (100.0 / p_glu) if p_glu > 0 else 0
        )
        actual_liq_pct = (
            target_liq * (100.0 / p_liq) if p_liq > 0 else 0
        )
        actual_ref_pct = (
            target_ref * (100.0 / ref_nominal_total)
            if ref_nominal_total > 0
            else 0
        )
        actual_mol_pct = (
            target_mol * (100.0 / mol_nominal_total)
            if mol_nominal_total > 0
            else 0
        )

        g_l_glu = actual_glu_pct * 10
        g_l_liq = actual_liq_pct * 10
        g_l_ref = actual_ref_pct * 10
        g_l_mol = actual_mol_pct * 10

        # HPLC 몰농도 계산 (mol/L)
        m_suc_meas = (hplc_suc * 10) / MW_SUC
        m_glu_meas = (hplc_glu * 10) / MW_GLU
        m_fru_meas = (hplc_fru * 10) / MW_FRU

        # 단일 당원 투입분 차감
        m_glu_powder = (
            (g_l_glu * (p_glu / 100.0)) / MW_GLU
            if "포도당" in selected_sources
            else 0
        )
        m_liq_contrib = (
            (g_l_liq * (p_liq / 100.0)) / MW_GLU
            if "액당" in selected_sources
            else 0
        )

        # 복합당원 명칭 및 스펙 할당
        complex_source_name = "복합당원"
        nominal_complex_purity = 0.0
        g_l_complex = 0.0

        if "정제당" in selected_sources:
            complex_source_name = "정제당"
            nominal_complex_purity = ref_nominal_total
            g_l_complex = g_l_ref
        elif "당밀" in selected_sources:
            complex_source_name = "당밀"
            nominal_complex_purity = mol_nominal_total
            g_l_complex = g_l_mol

        # =========================================================
        # 🧪 [수식 엄밀화] H2O 결합(질량 증가) 보정 역산 로직
        # =========================================================
        # 단당류 유래 몰수 중 단일 당원분을 차감한 '복합당원 유래 단당류 몰수'
        m_monosac_from_complex = max(
            0.0, (m_glu_meas + m_fru_meas) - m_glu_powder - m_liq_contrib
        )

        # 잔류 Sucrose 질량 (g/L)
        mass_suc_rem = m_suc_meas * MW_SUC

        # 단당류 유래 질량 계산 시 물 분자 결합분(18.015 g/mol) 제외 보정
        # 단당류 2몰당 물 1몰이 결합되었으므로, 몰당 평균 9.0075g 차감 효과
        mass_monosac_corrected = m_monosac_from_complex * (
            MW_GLU - (MW_H2O / 2.0)
        )

        # 복합당원 유래 정밀 역산 질량 (g/L)
        complex_actual_mass_g_l = mass_suc_rem + mass_monosac_corrected

        raw_actual_purity = (
            (complex_actual_mass_g_l / g_l_complex) * 100.0
            if g_l_complex > 0
            else 0.0
        )
        actual_complex_purity = raw_actual_purity * correction_factor
        abs_diff = actual_complex_purity - nominal_complex_purity

        # 역산 기반 기여 농도 산출
        real_sugar_contributions = {}
        total_measured_sugar = hplc_suc + hplc_glu + hplc_fru

        if "포도당" in selected_sources:
            real_sugar_contributions["포도당"] = actual_glu_pct * (
                p_glu / 100.0
            )
        if "액당" in selected_sources:
            real_sugar_contributions["액당"] = actual_liq_pct * (p_liq / 100.0)
        if "정제당" in selected_sources:
            real_sugar_contributions["정제당"] = actual_ref_pct * (
                actual_complex_purity / 100.0
            )
        if "당밀" in selected_sources:
            real_sugar_contributions["당밀"] = actual_mol_pct * (
                actual_complex_purity / 100.0
            )

        calc_total_real_sugar = sum(real_sugar_contributions.values())
        real_sugar_shares = {}
        if calc_total_real_sugar > 0:
            for src, val in real_sugar_contributions.items():
                real_sugar_shares[src] = (val / calc_total_real_sugar) * 100

        # 결과 카드 출력
        if complex_source_name != "복합당원":
            m1, m2 = st.columns([1, 1.3])
            with m1:
                st.metric(
                    f"{complex_source_name} 스펙 순도",
                    f"{nominal_complex_purity:.2f}%",
                )
            with m2:
                st.markdown(
                    f"""
                    <div class="highlight-card">
                        <div class="highlight-title">🎯 역산된 {complex_source_name} 실제 당농도</div>
                        <div class="highlight-value">{actual_complex_purity:.2f}%</div>
                        <div class="highlight-delta">스펙 대비 차이: {abs_diff:+.2f}%p</div>
                    </div>
                """,
                    unsafe_allow_html=True,
                )
        else:
            st.metric(
                "HPLC 실측 총 당농도",
                f"{total_measured_sugar:.2f}%",
            )

        st.write("")
        st.markdown("##### 📌 실제 역산 기반 당원별 기여 농도 및 비중")

        table_data = []
        if "포도당" in selected_sources:
            table_data.append(
                [
                    "포도당",
                    f"{actual_glu_pct:.4f} %",
                    f"{real_sugar_contributions.get('포도당', 0):.2f} %",
                    f"{real_sugar_shares.get('포도당', 0):.1f} %",
                ]
            )
        if "액당" in selected_sources:
            table_data.append(
                [
                    "액당",
                    f"{actual_liq_pct:.4f} %",
                    f"{real_sugar_contributions.get('액당', 0):.2f} %",
                    f"{real_sugar_shares.get('액당', 0):.1f} %",
                ]
            )
        if "정제당" in selected_sources:
            table_data.append(
                [
                    "정제당",
                    f"{actual_ref_pct:.4f} %",
                    f"{real_sugar_contributions.get('정제당', 0):.2f} %",
                    f"{real_sugar_shares.get('정제당', 0):.1f} %",
                ]
            )
        if "당밀" in selected_sources:
            table_data.append(
                [
                    "당밀",
                    f"{actual_mol_pct:.4f} %",
                    f"{real_sugar_contributions.get('당밀', 0):.2f} %",
                    f"{real_sugar_shares.get('당밀', 0):.1f} %",
                ]
            )

        df_res = pd.DataFrame(
            table_data,
            columns=[
                "당원",
                "칭량 투입량(w/v%)",
                "실제 기여 당농도(w/v%)",
                "실제 총당 내 비중(%)",
            ],
        )
        st.dataframe(df_res, use_container_width=True, hide_index=True)

        if real_sugar_shares:
            share_summary = " : ".join(
                [
                    f"{src} {val:.1f}%"
                    for src, val in real_sugar_shares.items()
                ]
            )
            st.info(f"💡 **실제 역산 기반 당원 구성 비중**: {share_summary}")

        st.markdown("---")

        # 공정 진단 리포트
        st.subheader("📋 공정 진단 및 원료 품질 종합 리포트")

        complex_suc_spec = (
            c_ref_suc if complex_source_name == "정제당" else c_mol_suc
        )
        complex_pct = (
            actual_ref_pct
            if complex_source_name == "정제당"
            else actual_mol_pct
        )
        expected_suc = complex_pct * (complex_suc_spec / 100.0)

        if expected_suc > 0:
            hydro_rate = max(
                0.0, min(100.0, (1 - (hplc_suc / expected_suc)) * 100.0)
            )
        else:
            hydro_rate = 100.0 if hplc_suc == 0 else 0.0

        st.markdown("#### 1️⃣ Sucrose 열가수분해 분석")
        st.markdown(
            f"- **추정 가수분해율**: **{hydro_rate:.1f}%** (이론 투입 추정치 {expected_suc:.2f}% 대비 실측 잔류량 {hplc_suc:.2f}%)"
        )
        if hydro_rate >= 95.0:
            st.caption(
                "🟢 **분석**: 멸균 공정 중 Sucrose가 Glucose와 Fructose로 거의 완전 전환되었습니다."
            )
        elif hydro_rate >= 50.0:
            st.caption(
                "🟡 **분석**: Sucrose 일부가 잔류된 부분 가수분해 상태입니다. 멸균 열이력(pH, 시간)을 점검하세요."
            )
        else:
            st.caption(
                "🔴 **분석**: 가수분해 진행률이 낮습니다. 멸균 조건 미달 또는 배지 pH 편차 가능성이 있습니다."
            )

        st.markdown("#### 2️⃣ 당원 품질 및 순도 변동 평가")
        if complex_source_name != "복합당원":
            st.markdown(
                f"- **스펙 순도**: `{nominal_complex_purity:.2f}%` ➡️ **H₂O 보정 역산 순도**: `{actual_complex_purity:.2f}%` (`{abs_diff:+.2f}%p` 변동)"
            )
            if abs(abs_diff) <= 2.0:
                st.caption(
                    "🟢 **분석**: 원료 스펙 오차 범위(±2%p) 내로 품질이 매우 안정적입니다."
                )
            elif abs_diff > 2.0:
                st.caption(
                    f"🔴 **분석**: 스펙 대비 당 함량이 **{abs_diff:.2f}%p 높게 역산**되었습니다. 원료 수분 증발(농축) 또는 제조사 품질 편차가 의심됩니다."
                )
            else:
                st.caption(
                    f"🔴 **분석**: 스펙 대비 당 함량이 **{abs(abs_diff):.2f}%p 낮게 역산**되었습니다. 원료 흡습, 열화 또는 고형분 침전 현상을 확인하세요."
                )

        st.markdown("#### 3️⃣ 공정 및 칭량 오차 검증")
        diff_total = total_measured_sugar - sum_target_sugar
        st.markdown(
            f"- **목표 설정 총당**: `{sum_target_sugar:.2f}%` ➡️ **HPLC 실측 총당**: `{total_measured_sugar:.2f}%` (`{diff_total:+.2f}%p` 차이)"
        )
        if abs(diff_total) > 0.5:
            st.caption(
                "⚠️ **주의**: 실측 총당과의 차이가 0.5%p 이상 발생했습니다. 칭량 스케일, 용수 부피 오차, 또는 멸균 후 증발 농축 여부를 재검증하세요."
            )

        st.markdown("---")

        # Step별 상세 계산 과정 토글
        with st.expander(
            "🔍 단계별 수식 및 검증 데이터 상세 보기 (클릭 시 펼침)",
            expanded=False,
        ):
            st.markdown("### 📐 H₂O 보정이 적용된 상세 역산 가이드")

            # Step 1
            st.markdown(
                """<div class="step-card">
                <div class="step-title">[Step 1] 원료 투입량 및 HPLC 실측 몰농도 산출</div>
                원료 순도를 고려한 실제 칭량 투입량(g/L)과 HPLC 측정값 기반의 몰농도를 구합니다.
            </div>""",
                unsafe_allow_html=True,
            )

            s1_col1, s1_col2 = st.columns(2)
            with s1_col1:
                st.caption("📌 **원료별 실제 칭량 투입량 (g/L)**")
                input_list = []
                if "포도당" in selected_sources:
                    input_list.append(
                        ["포도당", f"{actual_glu_pct:.4f} %", f"{g_l_glu:.2f} g/L"]
                    )
                if "액당" in selected_sources:
                    input_list.append(
                        ["액당", f"{actual_liq_pct:.4f} %", f"{g_l_liq:.2f} g/L"]
                    )
                if "정제당" in selected_sources:
                    input_list.append(
                        ["정제당", f"{actual_ref_pct:.4f} %", f"{g_l_ref:.2f} g/L"]
                    )
                if "당밀" in selected_sources:
                    input_list.append(
                        ["당밀", f"{actual_mol_pct:.4f} %", f"{g_l_mol:.2f} g/L"]
                    )

                df_step1_input = pd.DataFrame(
                    input_list,
                    columns=["당원", "칭량 비율(w/v%)", "칭량 농도(g/L)"],
                )
                st.dataframe(
                    df_step1_input, use_container_width=True, hide_index=True
                )

            with s1_col2:
                st.caption("📌 **HPLC 실측 몰농도 (mol/L)**")
                df_step1_hplc = pd.DataFrame(
                    [
                        [
                            "Sucrose",
                            f"{hplc_suc:.2f} %",
                            f"{m_suc_meas:.4f} mol/L",
                        ],
                        [
                            "Glucose",
                            f"{hplc_glu:.2f} %",
                            f"{m_glu_meas:.4f} mol/L",
                        ],
                        [
                            "Fructose",
                            f"{hplc_fru:.2f} %",
                            f"{m_fru_meas:.4f} mol/L",
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
                <div class="step-title">[Step 2] 복합당원 유래 몰농도 분리 & H₂O 보정 질량 환산</div>
                가수분해 시 결합한 H₂O 분자량(18.015 g/mol)의 영향을 제거하여 원래 당원 질량을 정밀 역산합니다.
            </div>""",
                unsafe_allow_html=True,
            )

            st.latex(
                r"\text{Mass}_{\text{단당류 보정}} = M_{\text{복합당원 단당류}} \times \left(180.16 - \frac{18.015}{2}\right)"
            )
            st.info(
                f"💡 **역산된 {complex_source_name} 유래 당 질량 농도**: `{complex_actual_mass_g_l:.2f} g/L`"
            )

            st.markdown("---")

            # Step 3
            st.markdown(
                f"""<div class="step-card">
                <div class="step-title">[Step 3] 최종 {complex_source_name} 순도 및 차이 산출</div>
                투입한 복합당원 질량 대비 실측 당 질량을 계산하여 실제 순도(%)를 도출합니다.
            </div>""",
                unsafe_allow_html=True,
            )
            s4_col1, s4_col2 = st.columns(2)
            with s4_col1:
                st.metric(
                    f"역산된 {complex_source_name} 당농도(순도)",
                    f"{actual_complex_purity:.2f}%",
                )
            with s4_col2:
                st.metric("스펙 대비 차이", f"{abs_diff:+.2f}%p")
