"""Bills search page."""

import asyncio
import pandas as pd
import plotly.express as px
import streamlit as st

from client import AssemblyClient

st.set_page_config(page_title="Bills · Assembly Explorer", page_icon="📜", layout="wide")

API_KEY = st.secrets.get("ASSEMBLY_API_KEY", "") or __import__("os").getenv("ASSEMBLY_API_KEY", "")

st.title("📜 Bill Search")
st.caption("Search member-sponsored bills from the 열린국회정보 API in real time.")

# ── Sidebar filters ────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Filters")
    age = st.selectbox("Assembly (대수)", ["22", "21", "20", "19", "18"], index=0)
    bill_name = st.text_input("Bill keyword (법률안명)", placeholder="예: 인공지능, 반도체")
    proposer  = st.text_input("Lead proposer (대표발의자)", placeholder="예: 홍길동")
    committee = st.text_input("Committee (소관위원회)", placeholder="예: 법제사법위원회")
    proc_result = st.selectbox(
        "Processing result (처리결과)",
        ["(all)", "원안가결", "수정가결", "부결", "폐기", "철회"],
        index=0,
    )
    page_size = st.slider("Results per query", min_value=10, max_value=100, value=20, step=10)
    search_btn = st.button("Search", type="primary", use_container_width=True)

# ── Main area ─────────────────────────────────────────────────────────────────
if not API_KEY:
    st.warning(
        "No API key found. Set `ASSEMBLY_API_KEY` in `.streamlit/secrets.toml` "
        "or as an environment variable."
    )
    st.stop()

if search_btn:
    with st.spinner("Querying 열린국회정보 API..."):
        async def fetch():
            async with AssemblyClient(API_KEY) as client:
                return await client.search_bills(
                    age=age,
                    bill_name=bill_name or None,
                    proposer=proposer or None,
                    committee=committee or None,
                    proc_result=None if proc_result == "(all)" else proc_result,
                    page_size=page_size,
                )
        try:
            rows = asyncio.run(fetch())
        except Exception as e:
            st.error(f"API error: {e}")
            st.stop()

    if not rows:
        st.info("No bills found. Try different filters.")
        st.stop()

    df = pd.DataFrame(rows)

    # ── Summary metrics ───────────────────────────────────────────────────────
    st.markdown(f"### {len(df)} bills found — {age}th Assembly")
    m1, m2, m3, m4 = st.columns(4)
    result_counts = df["PROC_RESULT"].value_counts() if "PROC_RESULT" in df.columns else pd.Series()
    m1.metric("Total", len(df))
    m2.metric("Passed (원안가결)", int(result_counts.get("원안가결", 0)))
    m3.metric("Amended (수정가결)", int(result_counts.get("수정가결", 0)))
    m4.metric("Scrapped (폐기)", int(result_counts.get("폐기", 0)))

    # ── Result distribution chart ─────────────────────────────────────────────
    if not result_counts.empty:
        col_chart, col_table = st.columns([1, 2])
        with col_chart:
            fig = px.pie(
                values=result_counts.values,
                names=result_counts.index,
                title="Processing outcomes",
                color_discrete_sequence=px.colors.qualitative.Set2,
                hole=0.35,
            )
            fig.update_layout(margin=dict(t=40, b=0, l=0, r=0), height=320)
            st.plotly_chart(fig, use_container_width=True)
    else:
        col_table = st.container()

    # ── Table ─────────────────────────────────────────────────────────────────
    display_cols = [c for c in ["BILL_NO", "BILL_NAME", "RST_PROPOSER", "COMMITTEE",
                                "PROPOSE_DT", "PROC_RESULT"] if c in df.columns]
    rename_map = {
        "BILL_NO": "Bill No.", "BILL_NAME": "Bill Name",
        "RST_PROPOSER": "Lead Proposer", "COMMITTEE": "Committee",
        "PROPOSE_DT": "Date Filed", "PROC_RESULT": "Result",
    }

    with col_table if "col_chart" in dir() else st.container():
        st.dataframe(
            df[display_cols].rename(columns=rename_map),
            use_container_width=True,
            height=320,
        )

    # ── Download ──────────────────────────────────────────────────────────────
    st.download_button(
        label="Download CSV",
        data=df.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"assembly_{age}_bills.csv",
        mime="text/csv",
    )

    # ── Bill detail expander ──────────────────────────────────────────────────
    if "BILL_NAME" in df.columns and "BILL_ID" in df.columns:
        st.markdown("---")
        st.markdown("#### Bill details & co-sponsors")
        selected = st.selectbox("Select a bill", df["BILL_NAME"].tolist())
        row = df[df["BILL_NAME"] == selected].iloc[0]
        bill_id = row.get("BILL_ID", "")

        cols = st.columns(2)
        with cols[0]:
            for k, label in [("BILL_NO","Bill No."),("RST_PROPOSER","Lead proposer"),
                              ("COMMITTEE","Committee"),("PROPOSE_DT","Filed"),
                              ("PROC_RESULT","Result")]:
                if k in row:
                    st.markdown(f"**{label}**: {row[k]}")
        with cols[1]:
            if "DETAIL_LINK" in row and row["DETAIL_LINK"]:
                st.link_button("Open in Assembly system", row["DETAIL_LINK"])
            if bill_id:
                if st.button("Load co-sponsors"):
                    async def fetch_proposers():
                        async with AssemblyClient(API_KEY) as client:
                            return await client.get_bill_proposers(bill_id)
                    try:
                        proposers = asyncio.run(fetch_proposers())
                        if proposers:
                            st.dataframe(pd.DataFrame(proposers)[
                                [c for c in ["PPSR_NM","PPSR_POLY_NM","REP_DIV"]
                                 if c in pd.DataFrame(proposers).columns]
                            ].rename(columns={"PPSR_NM":"Name",
                                              "PPSR_POLY_NM":"Party","REP_DIV":"Role"}),
                                use_container_width=True)
                        else:
                            st.info("No co-sponsor data available.")
                    except Exception as e:
                        st.error(str(e))
else:
    st.info("Set filters in the sidebar and click **Search**.")
