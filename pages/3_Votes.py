"""Vote results page."""

import asyncio
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

from client import AssemblyClient

st.set_page_config(page_title="Votes · Assembly Explorer", page_icon="🗳️", layout="wide")

API_KEY = st.secrets.get("ASSEMBLY_API_KEY", "") or __import__("os").getenv("ASSEMBLY_API_KEY", "")

st.title("🗳️ Plenary Vote Results")
st.caption("Query bill-level vote tallies from the National Assembly floor.")

with st.sidebar:
    st.header("Filters")
    age       = st.selectbox("Assembly (대수)", ["22", "21", "20", "19", "18"], index=0)
    bill_name = st.text_input("Bill keyword", placeholder="예: 반도체, 의료법, AI")
    page_size = st.slider("Results", 5, 50, 10, 5)
    search_btn = st.button("Search", type="primary", use_container_width=True)

if not API_KEY:
    st.warning("No API key found.")
    st.stop()

if search_btn:
    with st.spinner("Querying..."):
        async def fetch():
            async with AssemblyClient(API_KEY) as c:
                return await c.get_vote_results(
                    age=age,
                    bill_name=bill_name or None,
                    page_size=page_size,
                )
        try:
            rows = asyncio.run(fetch())
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

    st.markdown(f"### {len(df)} bills — {age}th Assembly")

    # ── Stacked bar chart ─────────────────────────────────────────────────────
    if {"YES_TCNT", "NO_TCNT", "BLANK_TCNT"}.issubset(df.columns) and "BILL_NAME" in df.columns:
        labels = df["BILL_NAME"].str[:30] + ("..." if df["BILL_NAME"].str.len().max() > 30 else "")

        fig = go.Figure()
        fig.add_bar(name="Yes (찬성)", x=labels, y=df["YES_TCNT"],
                    marker_color="#2ECC71")
        fig.add_bar(name="No (반대)", x=labels, y=df["NO_TCNT"],
                    marker_color="#E74C3C")
        fig.add_bar(name="Abstain (기권)", x=labels, y=df["BLANK_TCNT"],
                    marker_color="#BDC3C7")
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

    # ── Result badges + detail expander ──────────────────────────────────────
    for _, row in df.iterrows():
        result = row.get("PROC_RESULT_CD", "")
        color = "#2ECC71" if "가결" in str(result) else "#E74C3C" if "부결" in str(result) else "#95A5A6"
        badge = f'<span style="background:{color};color:white;padding:2px 8px;border-radius:4px;font-size:0.8em">{result}</span>'

        with st.expander(f"{row.get('BILL_NAME','—')}  {badge}", unsafe_allow_html=False):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Yes 찬성", int(row.get("YES_TCNT", 0)))
            c2.metric("No 반대",  int(row.get("NO_TCNT", 0)))
            c3.metric("Abstain 기권", int(row.get("BLANK_TCNT", 0)))
            c4.metric("Result", result or "—")

            if "PROC_DT" in row:
                st.caption(f"Vote date: {row['PROC_DT']}")
            if "LINK_URL" in row and row["LINK_URL"]:
                st.link_button("Full record", row["LINK_URL"])

    # ── Download ──────────────────────────────────────────────────────────────
    st.download_button(
        "Download CSV",
        df.to_csv(index=False).encode("utf-8-sig"),
        f"assembly_{age}_votes.csv",
        "text/csv",
    )
else:
    st.info("Set filters in the sidebar and click **Search**.")
