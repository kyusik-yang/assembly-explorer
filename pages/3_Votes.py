"""Vote results page."""

import asyncio
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

from client import AGE_OPTIONS, AssemblyClient
from utils import compute_rice_index, inject_mobile_css

st.set_page_config(page_title="Votes · Assembly Explorer", page_icon="🗳️", layout="wide")

API_KEY = st.secrets.get("ASSEMBLY_API_KEY", "") or __import__("os").getenv("ASSEMBLY_API_KEY", "")


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_votes(api_key, age, bill_name, page_size):
    async def _run():
        async with AssemblyClient(api_key) as c:
            return await c.get_vote_results(
                age=age, bill_name=bill_name or None, page_size=page_size,
            )
    return asyncio.run(_run())


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_member_votes(api_key, bill_id, age):
    async def _run():
        async with AssemblyClient(api_key) as c:
            return await c.get_member_votes(bill_id=bill_id, age=age)
    return asyncio.run(_run())


inject_mobile_css()
st.title("🗳️ Plenary Vote Results")
st.caption("Query bill-level vote tallies from the National Assembly floor.")

with st.sidebar:
    st.header("Filters")
    age       = st.selectbox("Assembly (대수)", AGE_OPTIONS, index=0)
    bill_name = st.text_input("Bill keyword", placeholder="예: 반도체, 의료법, AI")
    page_size = st.slider("Results", 5, 50, 10, 5)
    search_btn = st.button("Search", type="primary", use_container_width=True)

if not API_KEY:
    st.warning("No API key found.")
    st.stop()

if search_btn:
    with st.spinner("Querying..."):
        try:
            rows, total = fetch_votes(API_KEY, age, bill_name, page_size)
        except Exception as e:
            st.error(str(e))
            st.stop()

    if not rows:
        st.info("No vote results found.")
        st.stop()

    df = pd.DataFrame(rows)

    # Coerce numeric columns
    for col in ["YES_TCNT", "NO_TCNT", "BLANK_TCNT", "MEMBER_TCNT", "VOTE_TCNT"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    has_more = total > page_size
    caption = f"Showing {len(df)} of **{total:,}** votes — {age}th Assembly"
    if has_more:
        caption += "  _(increase 'Results' to load more)_"
    st.markdown(f"### {caption}")

    # ── Stacked bar chart ─────────────────────────────────────────────────────
    if {"YES_TCNT", "NO_TCNT", "BLANK_TCNT"}.issubset(df.columns) and "BILL_NAME" in df.columns:
        labels = df["BILL_NAME"].str[:30] + df["BILL_NAME"].str[30:].apply(
            lambda x: "..." if x else ""
        )
        fig = go.Figure()
        fig.add_bar(name="Yes (찬성)", x=labels, y=df["YES_TCNT"], marker_color="#2ECC71")
        fig.add_bar(name="No (반대)",  x=labels, y=df["NO_TCNT"],  marker_color="#E74C3C")
        fig.add_bar(name="Abstain (기권)", x=labels, y=df["BLANK_TCNT"], marker_color="#BDC3C7")
        fig.update_layout(
            barmode="stack",
            title="Vote breakdown by bill",
            xaxis_title="",
            yaxis_title="Votes",
            legend=dict(orientation="h", y=1.1),
            height=420,
            margin=dict(t=60, b=120, l=50, r=20),
        )
        fig.update_xaxes(tickangle=-35)
        st.plotly_chart(fig, use_container_width=True)

    # ── Result expanders with member votes drill-down ─────────────────────────
    for _, row in df.iterrows():
        result = row.get("PROC_RESULT_CD", "")
        result_label = f"[{result}]" if result else ""

        with st.expander(f"{row.get('BILL_NAME', '—')}  {result_label}"):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Yes 찬성",    int(row.get("YES_TCNT", 0)))
            c2.metric("No 반대",     int(row.get("NO_TCNT", 0)))
            c3.metric("Abstain 기권", int(row.get("BLANK_TCNT", 0)))
            c4.metric("Result",      result or "—")

            if "PROC_DT" in row and pd.notna(row["PROC_DT"]):
                st.caption(f"Vote date: {row['PROC_DT']}")
            if "LINK_URL" in row and row["LINK_URL"]:
                st.link_button("Full record", row["LINK_URL"])

            # Per-member vote breakdown (requires BILL_ID)
            bill_id = row.get("BILL_ID", "")
            if bill_id:
                st.markdown("**Party-level breakdown (개인별 표결)**")
                with st.spinner("Loading member votes..."):
                    try:
                        votes, vote_total = fetch_member_votes(API_KEY, bill_id, age)
                        if votes:
                            vdf = pd.DataFrame(votes)
                            st.caption(f"{vote_total} member votes")
                            if "POLY_NM" in vdf.columns and "RESULT_VOTE_MOD" in vdf.columns:
                                breakdown = (
                                    vdf.groupby(["POLY_NM", "RESULT_VOTE_MOD"])
                                    .size()
                                    .reset_index(name="count")
                                )
                                fig_v = px.bar(
                                    breakdown, x="POLY_NM", y="count",
                                    color="RESULT_VOTE_MOD",
                                    title="Party-level vote breakdown",
                                    labels={"POLY_NM": "Party", "count": "Members",
                                            "RESULT_VOTE_MOD": "Vote"},
                                    color_discrete_map={
                                        "찬성": "#2ECC71", "반대": "#E74C3C",
                                        "기권": "#BDC3C7", "불참": "#ECF0F1",
                                    },
                                    barmode="group",
                                    height=280,
                                )
                                fig_v.update_layout(margin=dict(t=40, b=80))
                                fig_v.update_xaxes(tickangle=-30)
                                st.plotly_chart(fig_v, use_container_width=True)
                            # Rice index
                            if "POLY_NM" in vdf.columns and "RESULT_VOTE_MOD" in vdf.columns:
                                rice_df = compute_rice_index(vdf)
                                with st.expander("Party cohesion (Rice index)"):
                                    st.dataframe(rice_df, use_container_width=True, hide_index=True)
                                    st.caption(
                                        "Rice index = |Yea − Nay| / (Yea + Nay) × 100. "
                                        "100 = unanimous, 0 = perfectly split."
                                    )
                        else:
                            st.caption("No individual vote records for this bill.")
                    except Exception as e:
                        st.caption(f"Could not load member votes: {e}")

    # ── Download ──────────────────────────────────────────────────────────────
    st.download_button(
        "Download CSV",
        df.to_csv(index=False).encode("utf-8-sig"),
        f"assembly_{age}_votes.csv",
        "text/csv",
    )
else:
    st.info("Set filters in the sidebar and click **Search**. (On mobile, tap **>>** at the top left to open the sidebar.)")
