"""Member Profile page — legislative activity for a single member."""

import asyncio
import pandas as pd
import plotly.express as px
import streamlit as st

from client import AGE_OPTIONS, AssemblyClient

st.set_page_config(
    page_title="Member Profile · Assembly Explorer", page_icon="👤", layout="wide"
)

API_KEY = st.secrets.get("ASSEMBLY_API_KEY", "") or __import__("os").getenv("ASSEMBLY_API_KEY", "")


# ── Cached fetchers ────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_member_info(api_key, age, name):
    async def _run():
        async with AssemblyClient(api_key) as c:
            return await c.get_member_info(age=age, name=name, page_size=10)
    return asyncio.run(_run())


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_proposed_bills_bulk(api_key, age, proposer, max_records=1000):
    """Collect all bills lead-proposed by this member (auto-paginated)."""
    async def _run():
        all_rows = []
        page = 1
        PAGE_SIZE = 100
        async with AssemblyClient(api_key) as c:
            while len(all_rows) < max_records:
                rows, total = await c.search_bills(
                    age=age, proposer=proposer, page=page, page_size=PAGE_SIZE,
                )
                all_rows.extend(rows)
                if len(all_rows) >= total or not rows:
                    break
                page += 1
        return all_rows, total
    return asyncio.run(_run())


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_vote_history(api_key, member_name, age, n_bills=30):
    """
    Get this member's votes on the n_bills most recently voted bills.
    Uses asyncio.gather to fan out calls in parallel.
    """
    async def _run():
        async with AssemblyClient(api_key) as c:
            voted_bills, _ = await c.get_vote_results(age=age, page_size=n_bills)
            if not voted_bills:
                return []

            bill_ids = [b["BILL_ID"] for b in voted_bills if "BILL_ID" in b]
            tasks = [
                c.get_member_votes(bill_id=bid, age=age, member_name=member_name)
                for bid in bill_ids
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            records = []
            for bill, result in zip(voted_bills, results):
                if isinstance(result, Exception) or not result:
                    continue
                votes, _ = result
                if not votes:
                    continue
                # Filter to only this member's vote (API may return others too)
                member_votes = [v for v in votes if v.get("HG_NM") == member_name]
                if not member_votes:
                    continue
                v = member_votes[0]
                records.append({
                    "BILL_NAME":    bill.get("BILL_NAME", ""),
                    "PROC_DT":      bill.get("PROC_DT", ""),
                    "BILL_RESULT":  bill.get("PROC_RESULT_CD", ""),
                    "MEMBER_VOTE":  v.get("RESULT_VOTE_MOD", ""),
                    "PARTY":        v.get("POLY_NM", ""),
                    "BILL_ID":      bill.get("BILL_ID", ""),
                })
            return records
    return asyncio.run(_run())


# ── UI ────────────────────────────────────────────────────────────────────────

st.title("👤 Member Profile")
st.caption(
    "Legislative activity for a single National Assembly member — "
    "bills proposed, vote record, and committee affiliation."
)

with st.sidebar:
    st.header("Search")
    name       = st.text_input("Member name (의원 이름)", placeholder="예: 이준석, 홍길동")
    age        = st.selectbox("Assembly (대수)", AGE_OPTIONS, index=0)
    search_btn = st.button("Search", type="primary", use_container_width=True)
    st.markdown("---")
    st.caption(
        "Tip: names must match exactly as registered in the National Assembly system. "
        "Use the Members page to look up the exact spelling first."
    )

if not API_KEY:
    st.warning("No API key found.")
    st.stop()

if not search_btn:
    st.info("Enter a member name in the sidebar and click **Search**.")
    st.stop()

if not name.strip():
    st.warning("Please enter a member name.")
    st.stop()

# ── 1. Basic profile ──────────────────────────────────────────────────────────
with st.spinner("Loading member profile..."):
    try:
        members, _ = fetch_member_info(API_KEY, age, name.strip())
    except Exception as e:
        st.error(f"API error: {e}")
        st.stop()

if not members:
    st.warning(
        f"No member found with name **{name}** in the {age}th Assembly. "
        "Check spelling or try a different assembly."
    )
    st.stop()

member = members[0]
party    = member.get("POLY_NM", "—")
district = member.get("ORIG_NM", "—")
cmit     = member.get("CMIT_NM", "—")
term     = member.get("REELE_GBN_NM", "—")
gender   = member.get("SEX_GBN_NM", "—")

st.markdown(f"## {name}  ·  {age}th National Assembly")

col_info, col_meta = st.columns([2, 1])
with col_info:
    st.markdown(f"**Party**: {party}")
    st.markdown(f"**District**: {district}")
    st.markdown(f"**Committee**: {cmit}")
    st.markdown(f"**Term**: {term}  ·  **Gender**: {gender}")
with col_meta:
    if "NAAS_PIC" in member and member["NAAS_PIC"]:
        st.image(member["NAAS_PIC"], width=120)

st.markdown("---")

# ── 2. Bills proposed ─────────────────────────────────────────────────────────
st.markdown("### 📜 Bills Proposed")

with st.spinner(f"Collecting all bills proposed by {name}..."):
    try:
        bill_rows, bill_total = fetch_proposed_bills_bulk(API_KEY, age, name.strip())
    except Exception as e:
        st.error(f"Failed to load bills: {e}")
        bill_rows, bill_total = [], 0

if not bill_rows:
    st.info(f"No bills found with {name} as lead proposer in the {age}th Assembly.")
else:
    bdf = pd.DataFrame(bill_rows)

    # Summary metrics
    result_counts = bdf["PROC_RESULT"].value_counts() if "PROC_RESULT" in bdf.columns else pd.Series()
    passed   = int(result_counts.get("원안가결", 0)) + int(result_counts.get("수정가결", 0))
    pending  = int((bdf["PROC_RESULT"].isna() | (bdf["PROC_RESULT"] == "")).sum()) if "PROC_RESULT" in bdf.columns else 0
    pass_rate = passed / len(bdf) * 100 if len(bdf) > 0 else 0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total bills",    len(bdf))
    m2.metric("Passed",         passed)
    m3.metric("Pending",        pending)
    m4.metric("Pass rate",      f"{pass_rate:.1f}%")

    # Charts
    if not result_counts.empty:
        col_pie, col_cmit = st.columns(2)
        with col_pie:
            fig_res = px.pie(
                values=result_counts.values, names=result_counts.index,
                title="Bills by outcome",
                color_discrete_sequence=px.colors.qualitative.Set2,
                hole=0.4,
            )
            fig_res.update_layout(margin=dict(t=40, b=0, l=0, r=0), height=280)
            st.plotly_chart(fig_res, use_container_width=True)

        with col_cmit:
            if "COMMITTEE" in bdf.columns:
                cmit_counts = bdf["COMMITTEE"].value_counts().head(8)
                fig_cmit = px.bar(
                    x=cmit_counts.values, y=cmit_counts.index,
                    orientation="h",
                    title="Bills by committee",
                    labels={"x": "Bills", "y": ""},
                )
                fig_cmit.update_layout(height=280, margin=dict(t=40, b=10, l=5, r=10))
                st.plotly_chart(fig_cmit, use_container_width=True)

    # Bill table
    display_cols = [c for c in ["BILL_NO", "BILL_NAME", "COMMITTEE",
                                "PROPOSE_DT", "PROC_RESULT"] if c in bdf.columns]
    rename_map = {
        "BILL_NO": "Bill No.", "BILL_NAME": "Bill Name", "COMMITTEE": "Committee",
        "PROPOSE_DT": "Date Filed", "PROC_RESULT": "Result",
    }
    st.dataframe(
        bdf[display_cols].rename(columns=rename_map),
        use_container_width=True, height=360,
    )

    # Download
    st.download_button(
        label=f"⬇ Download all {len(bdf)} bills (CSV)",
        data=bdf.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"{name}_{age}대_proposed_bills.csv",
        mime="text/csv",
    )

st.markdown("---")

# ── 3. Vote record ────────────────────────────────────────────────────────────
st.markdown("### 🗳️ Recent Vote Record")
st.caption(
    "Shows this member's votes on the 30 most recently voted bills in this assembly. "
    "For a complete vote record, use the bulk export on the Votes page."
)

with st.spinner(f"Fetching vote history for {name}..."):
    try:
        vote_records = fetch_vote_history(API_KEY, name.strip(), age, n_bills=30)
    except Exception as e:
        st.error(f"Failed to load vote history: {e}")
        vote_records = []

if not vote_records:
    st.info(
        f"No vote records found for {name} in the {age}th Assembly. "
        "This may mean the member did not vote on recent bills, or the name spelling differs."
    )
else:
    vdf = pd.DataFrame(vote_records)

    # Vote summary
    vote_counts = vdf["MEMBER_VOTE"].value_counts()
    total_votes = len(vdf)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Bills found",     total_votes)
    m2.metric("찬성 (Yes)",      int(vote_counts.get("찬성", 0)))
    m3.metric("반대 (No)",       int(vote_counts.get("반대", 0)))
    m4.metric("기권/불참",       int(vote_counts.get("기권", 0)) + int(vote_counts.get("불참", 0)))

    # Vote distribution chart
    col_v, col_tbl = st.columns([1, 2])
    with col_v:
        fig_vote = px.pie(
            values=vote_counts.values, names=vote_counts.index,
            title="Vote distribution",
            color_discrete_map={
                "찬성": "#2ECC71", "반대": "#E74C3C",
                "기권": "#BDC3C7", "불참": "#ECF0F1",
            },
            hole=0.4,
        )
        fig_vote.update_layout(margin=dict(t=40, b=0, l=0, r=0), height=260)
        st.plotly_chart(fig_vote, use_container_width=True)

    with col_tbl:
        st.dataframe(
            vdf[["BILL_NAME", "PROC_DT", "BILL_RESULT", "MEMBER_VOTE"]].rename(columns={
                "BILL_NAME":   "Bill",
                "PROC_DT":     "Vote Date",
                "BILL_RESULT": "Bill Outcome",
                "MEMBER_VOTE": f"{name}'s Vote",
            }),
            use_container_width=True, height=260,
        )

    st.download_button(
        label=f"⬇ Download vote record (CSV)",
        data=vdf.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"{name}_{age}대_vote_record.csv",
        mime="text/csv",
    )
