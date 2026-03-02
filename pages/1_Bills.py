"""Bills search page."""

import asyncio
import pandas as pd
import plotly.express as px
import streamlit as st

from client import AGE_OPTIONS, AssemblyClient

st.set_page_config(page_title="Bills · Assembly Explorer", page_icon="📜", layout="wide")

API_KEY = st.secrets.get("ASSEMBLY_API_KEY", "") or __import__("os").getenv("ASSEMBLY_API_KEY", "")


# ── Cached fetchers ────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_bills(api_key, age, bill_name, proposer, committee, proc_result,
                dt_from, dt_to, page, page_size):
    async def _run():
        async with AssemblyClient(api_key) as c:
            return await c.search_bills(
                age=age, bill_name=bill_name or None, proposer=proposer or None,
                committee=committee or None,
                proc_result=None if proc_result == "(all)" else proc_result,
                propose_dt_from=dt_from or None, propose_dt_to=dt_to or None,
                page=page, page_size=page_size,
            )
    return asyncio.run(_run())


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_bills_bulk(api_key, age, bill_name, proposer, committee, proc_result,
                     dt_from, dt_to, max_records):
    """Auto-paginate all results up to max_records."""
    async def _run():
        all_rows = []
        page = 1
        PAGE_SIZE = 100
        total = None
        async with AssemblyClient(api_key) as c:
            while len(all_rows) < max_records:
                rows, total = await c.search_bills(
                    age=age, bill_name=bill_name or None, proposer=proposer or None,
                    committee=committee or None,
                    proc_result=None if proc_result == "(all)" else proc_result,
                    propose_dt_from=dt_from or None, propose_dt_to=dt_to or None,
                    page=page, page_size=PAGE_SIZE,
                )
                all_rows.extend(rows)
                if len(all_rows) >= total or not rows:
                    break
                page += 1
        return all_rows[:max_records], total
    return asyncio.run(_run())


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_proposers(api_key, bill_id):
    async def _run():
        async with AssemblyClient(api_key) as c:
            return await c.get_bill_proposers(bill_id)
    return asyncio.run(_run())


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_member_votes(api_key, bill_id, age):
    async def _run():
        async with AssemblyClient(api_key) as c:
            return await c.get_member_votes(bill_id=bill_id, age=age)
    return asyncio.run(_run())


# ── Page ──────────────────────────────────────────────────────────────────────

st.title("📜 Bill Search")
st.caption("Search member-sponsored bills from the 열린국회정보 API in real time.")

with st.sidebar:
    st.header("Filters")
    age         = st.selectbox("Assembly (대수)", AGE_OPTIONS, index=0)
    bill_name   = st.text_input("Bill keyword (법률안명)", placeholder="예: 인공지능, 반도체")
    proposer    = st.text_input("Lead proposer (대표발의자)", placeholder="예: 홍길동")
    committee   = st.text_input("Committee (소관위원회)", placeholder="예: 법제사법위원회")
    proc_result = st.selectbox(
        "Processing result (처리결과)",
        ["(all)", "원안가결", "수정가결", "부결", "폐기", "철회"],
    )
    st.markdown("**Date range (발의일)**")
    dt_from   = st.text_input("From (YYYYMMDD)", placeholder="20240101")
    dt_to     = st.text_input("To (YYYYMMDD)", placeholder="20241231")
    page_size = st.slider("Preview size", 10, 100, 20, 10)
    search_btn = st.button("Search", type="primary", use_container_width=True)

if not API_KEY:
    st.warning(
        "No API key found. Set `ASSEMBLY_API_KEY` in `.streamlit/secrets.toml` "
        "or as an environment variable."
    )
    st.stop()

# Reset bulk cache on new search
if search_btn:
    st.session_state.pop("bulk_bills_df", None)

if search_btn:
    with st.spinner("Querying 열린국회정보 API..."):
        try:
            rows, total = fetch_bills(
                API_KEY, age, bill_name, proposer, committee, proc_result,
                dt_from, dt_to, 1, page_size,
            )
        except Exception as e:
            st.error(f"API error: {e}")
            st.stop()

    if not rows:
        st.info("No bills found. Try different filters.")
        st.stop()

    df = pd.DataFrame(rows)

    # ── Summary metrics ───────────────────────────────────────────────────────
    has_more = total > page_size
    st.markdown(f"### Showing {len(df)} of **{total:,}** total bills — {age}th Assembly")

    m1, m2, m3, m4 = st.columns(4)
    result_counts = df["PROC_RESULT"].value_counts() if "PROC_RESULT" in df.columns else pd.Series()
    m1.metric("In this preview", len(df))
    m2.metric("Passed (원안가결)",  int(result_counts.get("원안가결", 0)))
    m3.metric("Amended (수정가결)", int(result_counts.get("수정가결", 0)))
    m4.metric("Scrapped (폐기)",    int(result_counts.get("폐기", 0)))

    # ── Result distribution chart ─────────────────────────────────────────────
    if not result_counts.empty:
        col_chart, col_table = st.columns([1, 2])
        with col_chart:
            fig = px.pie(
                values=result_counts.values, names=result_counts.index,
                title="Processing outcomes",
                color_discrete_sequence=px.colors.qualitative.Set2,
                hole=0.35,
            )
            fig.update_layout(margin=dict(t=40, b=0, l=0, r=0), height=320)
            st.plotly_chart(fig, use_container_width=True)
    else:
        col_table = st.container()

    # ── Preview table ─────────────────────────────────────────────────────────
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
            use_container_width=True, height=320,
        )

    # ── Bulk export ───────────────────────────────────────────────────────────
    st.markdown("---")
    with st.expander(
        f"📥 Export full dataset  ·  **{total:,}** records available",
        expanded=has_more,
    ):
        col_opt, col_btn = st.columns([2, 1])
        with col_opt:
            max_dl = st.select_slider(
                "Max records to collect",
                options=[100, 300, 500, 1000, 3000, 5000],
                value=min(500, total),
            )
            if total > max_dl:
                st.caption(f"Will collect the first {max_dl:,} of {total:,} results.")
            else:
                st.caption(f"Will collect all {total:,} results.")
        with col_btn:
            st.markdown("&nbsp;")
            collect_btn = st.button(
                f"Collect {min(total, max_dl):,} records",
                type="primary",
                use_container_width=True,
            )

        if collect_btn:
            with st.spinner(f"Paginating through API... collecting up to {max_dl:,} records"):
                try:
                    all_rows, all_total = fetch_bills_bulk(
                        API_KEY, age, bill_name, proposer, committee, proc_result,
                        dt_from, dt_to, max_dl,
                    )
                    st.session_state["bulk_bills_df"] = pd.DataFrame(all_rows)
                    st.session_state["bulk_bills_label"] = (
                        f"assembly_{age}_bills_full_{len(all_rows)}records.csv"
                    )
                    st.success(f"Collected {len(all_rows):,} records (of {all_total:,} total).")
                except Exception as e:
                    st.error(f"Bulk fetch error: {e}")

        if "bulk_bills_df" in st.session_state:
            bulk_df = st.session_state["bulk_bills_df"]
            label   = st.session_state.get("bulk_bills_label", "bills_bulk.csv")

            # Result breakdown of full dataset
            if "PROC_RESULT" in bulk_df.columns:
                full_counts = bulk_df["PROC_RESULT"].value_counts()
                st.markdown(f"**Full dataset breakdown** ({len(bulk_df):,} records):")
                cols = st.columns(len(full_counts))
                for i, (k, v) in enumerate(full_counts.items()):
                    cols[i].metric(k or "(pending)", v)

            st.download_button(
                label=f"⬇ Download CSV ({len(bulk_df):,} rows)",
                data=bulk_df.to_csv(index=False).encode("utf-8-sig"),
                file_name=label,
                mime="text/csv",
                type="primary",
            )
            st.caption(
                "CSV includes all raw API columns. "
                "Encoding: UTF-8 with BOM (Excel-compatible)."
            )

    # ── Bill detail + co-sponsors + member votes ──────────────────────────────
    if "BILL_NAME" in df.columns and "BILL_ID" in df.columns:
        st.markdown("---")
        st.markdown("#### Bill details")
        selected = st.selectbox("Select a bill", df["BILL_NAME"].tolist())
        row = df[df["BILL_NAME"] == selected].iloc[0]
        bill_id = row.get("BILL_ID", "")

        cols = st.columns(2)
        with cols[0]:
            for k, label in [
                ("BILL_NO", "Bill No."), ("RST_PROPOSER", "Lead proposer"),
                ("COMMITTEE", "Committee"), ("PROPOSE_DT", "Filed"),
                ("PROC_RESULT", "Result"),
            ]:
                if k in row and pd.notna(row[k]):
                    st.markdown(f"**{label}**: {row[k]}")
        with cols[1]:
            if "DETAIL_LINK" in row and row["DETAIL_LINK"]:
                st.link_button("Open in Assembly system", row["DETAIL_LINK"])

        if bill_id:
            tab_proposers, tab_votes = st.tabs(["Co-sponsors", "Member votes (개인별 표결)"])

            with tab_proposers:
                with st.spinner("Loading co-sponsors..."):
                    try:
                        proposers, _ = fetch_proposers(API_KEY, bill_id)
                        if proposers:
                            pdf = pd.DataFrame(proposers)
                            show_cols = [c for c in ["PPSR_NM", "PPSR_POLY_NM", "REP_DIV"]
                                         if c in pdf.columns]
                            st.dataframe(
                                pdf[show_cols].rename(columns={
                                    "PPSR_NM": "Name", "PPSR_POLY_NM": "Party", "REP_DIV": "Role",
                                }),
                                use_container_width=True,
                            )
                        else:
                            st.info("No co-sponsor data available.")
                    except Exception as e:
                        st.error(str(e))

            with tab_votes:
                with st.spinner("Loading individual vote records..."):
                    try:
                        votes, vote_total = fetch_member_votes(API_KEY, bill_id, age)
                        if votes:
                            vdf = pd.DataFrame(votes)
                            st.caption(f"{vote_total} member votes")
                            if "POLY_NM" in vdf.columns and "RESULT_VOTE_MOD" in vdf.columns:
                                breakdown = (
                                    vdf.groupby(["POLY_NM", "RESULT_VOTE_MOD"])
                                    .size().reset_index(name="count")
                                )
                                fig_v = px.bar(
                                    breakdown, x="POLY_NM", y="count",
                                    color="RESULT_VOTE_MOD",
                                    title="Vote breakdown by party",
                                    labels={"POLY_NM": "Party", "count": "Members",
                                            "RESULT_VOTE_MOD": "Vote"},
                                    color_discrete_map={
                                        "찬성": "#2ECC71", "반대": "#E74C3C",
                                        "기권": "#BDC3C7", "불참": "#ECF0F1",
                                    },
                                    barmode="group", height=320,
                                )
                                fig_v.update_layout(margin=dict(t=50, b=80))
                                fig_v.update_xaxes(tickangle=-30)
                                st.plotly_chart(fig_v, use_container_width=True)

                            show_cols = [c for c in ["HG_NM", "POLY_NM", "ORIG_NM", "RESULT_VOTE_MOD"]
                                         if c in vdf.columns]
                            st.dataframe(
                                vdf[show_cols].rename(columns={
                                    "HG_NM": "Name", "POLY_NM": "Party",
                                    "ORIG_NM": "District", "RESULT_VOTE_MOD": "Vote",
                                }),
                                use_container_width=True, height=300,
                            )
                        else:
                            st.info("No individual vote records for this bill.")
                    except Exception as e:
                        st.error(str(e))
else:
    st.info("Set filters in the sidebar and click **Search**.")
