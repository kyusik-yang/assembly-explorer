"""Committee Explorer page."""

import asyncio
import pandas as pd
import plotly.express as px
import streamlit as st

from client import AGE_OPTIONS, AssemblyClient

st.set_page_config(page_title="Committees · Assembly Explorer", page_icon="🏛️", layout="wide")

API_KEY = st.secrets.get("ASSEMBLY_API_KEY", "") or __import__("os").getenv("ASSEMBLY_API_KEY", "")

COMMITTEES_22 = [
    "국회운영위원회",
    "법제사법위원회",
    "정무위원회",
    "기획재정위원회",
    "교육위원회",
    "과학기술정보방송통신위원회",
    "외교통일위원회",
    "국방위원회",
    "행정안전위원회",
    "문화체육관광위원회",
    "농림축산식품해양수산위원회",
    "산업통상자원중소벤처기업위원회",
    "보건복지위원회",
    "환경노동위원회",
    "국토교통위원회",
    "정보위원회",
    "여성가족위원회",
    "예산결산특별위원회",
]


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_committee(api_key, age, committee, page_size):
    async def _run():
        async with AssemblyClient(api_key) as c:
            return await c.get_member_info(
                age=age, committee=committee, page_size=page_size,
            )
    return asyncio.run(_run())


st.title("🏛️ Committee Explorer")
st.caption("Browse committee rosters and party composition from the 열린국회정보 API.")

with st.sidebar:
    st.header("Filters")
    age = st.selectbox("Assembly (대수)", AGE_OPTIONS, index=0)
    committee_preset = st.selectbox(
        "Committee (위원회)",
        ["(type below)"] + COMMITTEES_22,
        index=0,
    )
    committee_custom = st.text_input(
        "Or type committee name",
        placeholder="예: 법제사법위원회",
        disabled=(committee_preset != "(type below)"),
    )
    committee = committee_custom if committee_preset == "(type below)" else committee_preset
    page_size = st.slider("Max members", 10, 100, 50, 10)
    search_btn = st.button("Search", type="primary", use_container_width=True)

if not API_KEY:
    st.warning("No API key found.")
    st.stop()

if search_btn:
    if not committee:
        st.warning("Please select or type a committee name.")
        st.stop()

    with st.spinner(f"Loading {committee} members..."):
        try:
            rows, total = fetch_committee(API_KEY, age, committee, page_size)
        except Exception as e:
            st.error(str(e))
            st.stop()

    if not rows:
        st.info(f"No members found for '{committee}' in the {age}th Assembly.")
        st.stop()

    df = pd.DataFrame(rows)

    st.markdown(f"### {committee} — {age}th Assembly")
    st.caption(f"{len(df)} members found")

    # ── Party composition ─────────────────────────────────────────────────────
    if "POLY_NM" in df.columns:
        party_counts = df["POLY_NM"].value_counts()
        total_members = party_counts.sum()

        col_pie, col_stats = st.columns([1, 1])

        with col_pie:
            fig = px.pie(
                values=party_counts.values,
                names=party_counts.index,
                title="Party composition",
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            fig.update_layout(margin=dict(t=40, b=0, l=0, r=0), height=320)
            st.plotly_chart(fig, use_container_width=True)

        with col_stats:
            st.markdown("**Seat counts by party**")
            for party_name, count in party_counts.items():
                pct = count / total_members * 100
                st.markdown(f"- **{party_name}**: {count} seats ({pct:.1f}%)")

            # Majority check
            if len(party_counts) > 0:
                top_party = party_counts.index[0]
                top_count = party_counts.iloc[0]
                majority = top_count / total_members * 100
                if majority > 50:
                    st.success(f"**{top_party}** holds a majority ({majority:.1f}%)")
                else:
                    st.info(f"No single-party majority. Largest: **{top_party}** ({majority:.1f}%)")

    # ── Member table ──────────────────────────────────────────────────────────
    st.markdown("#### Members")
    display_cols = [c for c in ["HG_NM", "POLY_NM", "ORIG_NM", "CMIT_NM",
                                "REELE_GBN_NM", "SEX_GBN_NM"] if c in df.columns]
    rename_map = {
        "HG_NM": "Name", "POLY_NM": "Party", "ORIG_NM": "District",
        "CMIT_NM": "Committee", "REELE_GBN_NM": "Term", "SEX_GBN_NM": "Gender",
    }
    st.dataframe(
        df[display_cols].rename(columns=rename_map),
        use_container_width=True,
        height=400,
    )

    st.download_button(
        "Download CSV",
        df.to_csv(index=False).encode("utf-8-sig"),
        f"assembly_{age}_{committee}.csv",
        "text/csv",
    )
else:
    st.info("Select a committee and assembly in the sidebar, then click **Search**.")

    with st.expander("Main standing committees (22nd Assembly)", expanded=True):
        for c in COMMITTEES_22:
            st.markdown(f"- {c}")
