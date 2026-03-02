"""Members page."""

import asyncio
import pandas as pd
import plotly.express as px
import streamlit as st

from client import AGE_OPTIONS, AssemblyClient

st.set_page_config(page_title="Members · Assembly Explorer", page_icon="👤", layout="wide")

API_KEY = st.secrets.get("ASSEMBLY_API_KEY", "") or __import__("os").getenv("ASSEMBLY_API_KEY", "")


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_members(api_key, age, name, party, district, committee, page_size):
    async def _run():
        async with AssemblyClient(api_key) as c:
            return await c.get_member_info(
                age=age, name=name or None, party=party or None,
                district=district or None, committee=committee or None,
                page_size=page_size,
            )
    return asyncio.run(_run())


st.title("👤 Assembly Members")
st.caption("Browse National Assembly member rosters from the 열린국회정보 API.")

with st.sidebar:
    st.header("Filters")
    age       = st.selectbox("Assembly (대수)", AGE_OPTIONS, index=0)
    name      = st.text_input("Name (이름)", placeholder="예: 홍길동")
    party     = st.text_input("Party (정당)", placeholder="예: 더불어민주당, 국민의힘")
    district  = st.text_input("District (선거구)", placeholder="예: 서울 강남갑, 비례대표")
    committee = st.text_input("Committee (위원회)", placeholder="예: 법제사법위원회")
    page_size = st.slider("Results", 10, 300, 50, 10)
    search_btn = st.button("Search", type="primary", use_container_width=True)

if not API_KEY:
    st.warning("No API key found.")
    st.stop()

if search_btn:
    with st.spinner("Querying..."):
        try:
            rows, total = fetch_members(API_KEY, age, name, party, district, committee, page_size)
        except Exception as e:
            st.error(str(e))
            st.stop()

    if not rows:
        st.info("No members found.")
        st.stop()

    df = pd.DataFrame(rows)

    has_more = total > page_size
    caption = f"Showing {len(df)} of **{total:,}** members — {age}th Assembly"
    if has_more:
        caption += "  _(increase 'Results' to load more)_"
    st.markdown(f"### {caption}")

    # ── Party distribution ────────────────────────────────────────────────────
    if "POLY_NM" in df.columns:
        party_counts = df["POLY_NM"].value_counts()
        col_pie, col_bar = st.columns(2)

        with col_pie:
            fig = px.pie(
                values=party_counts.values,
                names=party_counts.index,
                title="Party distribution",
                hole=0.35,
                color_discrete_sequence=px.colors.qualitative.Pastel,
            )
            fig.update_layout(margin=dict(t=40, b=0, l=0, r=0), height=320)
            st.plotly_chart(fig, use_container_width=True)

        with col_bar:
            fig2 = px.bar(
                x=party_counts.index,
                y=party_counts.values,
                title="Seats by party",
                labels={"x": "Party", "y": "Seats"},
                color=party_counts.index,
                color_discrete_sequence=px.colors.qualitative.Pastel,
            )
            fig2.update_layout(showlegend=False, height=320,
                               margin=dict(t=40, b=60, l=40, r=10))
            fig2.update_xaxes(tickangle=-30)
            st.plotly_chart(fig2, use_container_width=True)

    # ── Member table ──────────────────────────────────────────────────────────
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
        f"assembly_{age}_members.csv",
        "text/csv",
    )

    # ── Election type breakdown ───────────────────────────────────────────────
    if "REELE_GBN_NM" in df.columns:
        st.markdown("#### Election type breakdown")
        term_counts = df["REELE_GBN_NM"].value_counts().reset_index()
        term_counts.columns = ["Term", "Count"]
        fig3 = px.bar(term_counts, x="Term", y="Count",
                      color="Term", title="Members by election term")
        fig3.update_layout(showlegend=False, height=280)
        st.plotly_chart(fig3, use_container_width=True)
else:
    st.info("Set filters in the sidebar and click **Search**.")
