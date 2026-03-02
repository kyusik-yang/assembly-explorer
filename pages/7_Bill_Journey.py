"""Bill Journey page — full legislative timeline for a single bill."""

import asyncio
import pandas as pd
import streamlit as st

from client import AGE_OPTIONS, AssemblyClient
from utils import VOTE_COLORS, journey_figure

st.set_page_config(
    page_title="Bill Journey · Assembly Explorer",
    page_icon="🗺️", layout="wide",
)

API_KEY = st.secrets.get("ASSEMBLY_API_KEY", "") or __import__("os").getenv("ASSEMBLY_API_KEY", "")


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_bill_journey(api_key, age, bill_no):
    async def _run():
        async with AssemblyClient(api_key) as c:
            return await c.get_bill_review(age=age, bill_no=bill_no, page_size=5)
    return asyncio.run(_run())


@st.cache_data(ttl=3600, show_spinner=False)
def search_bills_by_keyword(api_key, age, keyword, page_size):
    async def _run():
        async with AssemblyClient(api_key) as c:
            return await c.search_bills(age=age, bill_name=keyword, page_size=page_size)
    return asyncio.run(_run())


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_proposers(api_key, bill_id):
    async def _run():
        async with AssemblyClient(api_key) as c:
            return await c.get_bill_proposers(bill_id)
    return asyncio.run(_run())


st.title("🗺️ Bill Journey")
st.caption(
    "Full legislative timeline for a single bill — "
    "from filing through committee review to plenary vote and promulgation."
)

with st.sidebar:
    st.header("Find a bill")
    age = st.selectbox("Assembly (대수)", AGE_OPTIONS, index=0)
    st.markdown("**Option A — direct lookup**")
    bill_no_input = st.text_input(
        "Bill number (의안번호)",
        placeholder="예: 2216983",
        help="8-digit number from the Bills page (BILL_NO column).",
    )
    st.markdown("**Option B — keyword search**")
    keyword = st.text_input("Bill keyword", placeholder="예: 반도체특별법")
    search_btn = st.button("Search", type="secondary", use_container_width=True)

if not API_KEY:
    st.warning("No API key found.")
    st.stop()

# ── Option B: keyword search to pick bill number ───────────────────────────────
if search_btn and keyword and not bill_no_input:
    with st.spinner("Searching bills..."):
        try:
            kw_bills, kw_total = search_bills_by_keyword(API_KEY, age, keyword, page_size=20)
        except Exception as e:
            st.error(str(e))
            st.stop()

    if not kw_bills:
        st.warning("No bills found for that keyword.")
        st.stop()

    # Persist results so they survive the on_select rerun
    st.session_state["journey_search_results"] = (kw_bills, kw_total)
    st.session_state.pop("journey_selected_bill_no", None)

if "journey_search_results" in st.session_state and not bill_no_input:
    kw_bills, kw_total = st.session_state["journey_search_results"]
    kdf = pd.DataFrame(kw_bills)
    st.markdown(f"**{kw_total} bills found** — select one to view its journey:")
    display_cols = [c for c in ["BILL_NO", "BILL_NAME", "RST_PROPOSER",
                                "PROPOSE_DT", "PROC_RESULT"] if c in kdf.columns]
    selected_row = st.dataframe(
        kdf[display_cols].rename(columns={
            "BILL_NO": "Bill No.", "BILL_NAME": "Bill Name",
            "RST_PROPOSER": "Proposer", "PROPOSE_DT": "Filed", "PROC_RESULT": "Result",
        }),
        use_container_width=True,
        height=280,
        on_select="rerun",
        selection_mode="single-row",
    )
    if selected_row and selected_row.get("selection", {}).get("rows"):
        idx = selected_row["selection"]["rows"][0]
        st.session_state["journey_selected_bill_no"] = str(kdf.iloc[idx]["BILL_NO"])
        st.success(f"Selected: {kdf.iloc[idx].get('BILL_NAME', '')}")

# ── Resolve bill_no ────────────────────────────────────────────────────────────
# Direct text input takes priority; otherwise use keyword-search selection
bill_no = (
    bill_no_input.strip()
    if bill_no_input.strip()
    else st.session_state.get("journey_selected_bill_no", "")
)

if not bill_no:
    st.info(
        "Enter a bill number in the sidebar, "
        "or use keyword search to find and select a bill."
    )
    st.stop()

# ── Fetch journey data ─────────────────────────────────────────────────────────
with st.spinner(f"Loading journey for bill {bill_no}..."):
    try:
        rows, _ = fetch_bill_journey(API_KEY, age, bill_no)
    except Exception as e:
        st.error(f"API error: {e}")
        st.stop()

if not rows:
    st.warning(
        f"No journey data found for bill **{bill_no}** in the {age}th Assembly. "
        "Check the bill number or try a different assembly."
    )
    st.stop()

row = rows[0]

# ── Header ─────────────────────────────────────────────────────────────────────
bill_name = row.get("BILL_NM", f"Bill {bill_no}")
result    = row.get("PROC_RESULT_CD", "")
result_color = "#2ECC71" if "가결" in str(result) else "#E74C3C" if "부결" in str(result) else "#F39C12"

st.markdown(f"## {bill_name}")

col_meta, col_result = st.columns([3, 1])
with col_meta:
    st.markdown(f"**Bill No.**: {row.get('BILL_NO', bill_no)}")
    st.markdown(f"**Proposer**: {row.get('PROPOSER', '—')}")
    st.markdown(f"**Committee**: {row.get('COMMITTEE_NM', '—')}")
    if row.get("LINK_URL"):
        st.link_button("Open in Assembly system", row["LINK_URL"])
with col_result:
    st.markdown(
        f"<div style='background:{result_color};color:white;padding:12px 16px;"
        f"border-radius:8px;text-align:center;font-size:1.1em;font-weight:bold'>"
        f"{result or 'Pending'}</div>",
        unsafe_allow_html=True,
    )

st.markdown("---")

# ── Timeline + vote results ────────────────────────────────────────────────────
col_timeline, col_vote = st.columns([1, 1])

with col_timeline:
    st.markdown("#### Legislative timeline")
    fig = journey_figure(row)
    st.plotly_chart(fig, use_container_width=True)

with col_vote:
    st.markdown("#### Plenary vote")
    yes   = row.get("YES_TCNT", 0) or 0
    nay   = row.get("NO_TCNT", 0) or 0
    blank = row.get("BLANK_TCNT", 0) or 0
    total = row.get("VOTE_TCNT", 0) or 0

    if int(yes) + int(nay) + int(blank) > 0:
        m1, m2, m3 = st.columns(3)
        m1.metric("Yes 찬성",    int(yes))
        m2.metric("No 반대",     int(nay))
        m3.metric("Abstain 기권", int(blank))

        import plotly.express as px
        vote_df = pd.DataFrame({
            "Vote": ["찬성", "반대", "기권"],
            "Count": [int(yes), int(nay), int(blank)],
        })
        vote_df = vote_df[vote_df["Count"] > 0]
        fig_v = px.pie(
            vote_df, values="Count", names="Vote",
            color="Vote",
            color_discrete_map={"찬성": "#2ECC71", "반대": "#E74C3C", "기권": "#BDC3C7"},
            hole=0.45, height=260,
        )
        fig_v.update_layout(margin=dict(t=10, b=0, l=0, r=0), showlegend=True)
        st.plotly_chart(fig_v, use_container_width=True)
        if row.get("LAW_PROC_DT"):
            st.caption(f"Vote date: {row['LAW_PROC_DT']}")
    else:
        st.info("No plenary vote data available.")

# ── Co-sponsors ────────────────────────────────────────────────────────────────
bill_id = row.get("BILL_ID", "")
if bill_id:
    st.markdown("---")
    st.markdown("#### Co-sponsors")
    with st.spinner("Loading co-sponsors..."):
        try:
            prop_rows, _ = fetch_proposers(API_KEY, bill_id)
            if prop_rows:
                pdf = pd.DataFrame(prop_rows)
                show_cols = [c for c in ["PPSR_NM", "PPSR_POLY_NM", "REP_DIV"]
                             if c in pdf.columns]
                st.dataframe(
                    pdf[show_cols].rename(columns={
                        "PPSR_NM": "Name", "PPSR_POLY_NM": "Party", "REP_DIV": "Role",
                    }),
                    use_container_width=True, height=280,
                )
            else:
                st.info("No co-sponsor data available.")
        except Exception as e:
            st.caption(f"Could not load co-sponsors: {e}")

# ── Raw data ───────────────────────────────────────────────────────────────────
with st.expander("Raw API data (all fields)"):
    st.json(row)
