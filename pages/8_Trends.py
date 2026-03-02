"""Bill trends page — keyword volume by assembly and year."""

import asyncio
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from client import AGE_OPTIONS, AssemblyClient
from utils import inject_mobile_css

st.set_page_config(page_title="Trends · Assembly Explorer", page_icon="📈", layout="wide")

API_KEY = st.secrets.get("ASSEMBLY_API_KEY", "") or __import__("os").getenv("ASSEMBLY_API_KEY", "")


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_bill_count(api_key: str, age: str, keyword: str) -> int:
    """Return total bill count for (age, keyword) without fetching rows."""
    async def _run():
        async with AssemblyClient(api_key) as c:
            _, total = await c.search_bills(
                age=age, bill_name=keyword or None, page_size=1,
            )
            return total
    return asyncio.run(_run())


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_bills_sample(api_key: str, age: str, keyword: str, page_size: int = 100):
    """Fetch up to page_size bills for date-distribution analysis."""
    async def _run():
        async with AssemblyClient(api_key) as c:
            rows, total = await c.search_bills(
                age=age, bill_name=keyword or None, page_size=page_size,
            )
            return rows, total
    return asyncio.run(_run())


# ── Sidebar ───────────────────────────────────────────────────────────────────

inject_mobile_css()
st.title("📈 Bill Trends")
st.caption("Compare bill volumes across assemblies and trace how policy topics rise and fall over time.")

with st.sidebar:
    st.header("Settings")
    keywords_raw = st.text_input(
        "Keywords (comma-separated)",
        value="인공지능, 주거, 반도체",
        help="Up to 5 keywords. Leave blank for total bill count.",
    )
    ages_selected = st.multiselect(
        "Assemblies to compare",
        options=AGE_OPTIONS,
        default=["22", "21", "20", "19"],
        help="Select two or more assemblies.",
    )
    show_pct = st.toggle("Show as % of total bills", value=False)
    run_btn = st.button("Run", type="primary", use_container_width=True)

if not API_KEY:
    st.warning("No API key found.")
    st.stop()

if not run_btn:
    st.info("Set keywords and assemblies in the sidebar, then click **Run**.")
    st.stop()

if len(ages_selected) < 1:
    st.warning("Select at least one assembly.")
    st.stop()

keywords = [k.strip() for k in keywords_raw.split(",") if k.strip()][:5]
if not keywords:
    keywords = [""]   # empty string = all bills

# ── Fetch counts ──────────────────────────────────────────────────────────────

records = []
progress = st.progress(0.0, text="Fetching data...")
total_calls = len(keywords) * len(ages_selected)
done = 0

for kw in keywords:
    for age in ages_selected:
        label = kw if kw else "(all bills)"
        count = fetch_bill_count(API_KEY, age, kw)
        records.append({"Keyword": label, "Assembly": f"{age}대", "age_num": int(age), "count": count})
        done += 1
        progress.progress(done / total_calls, text=f"Fetching: {label} — {age}대 ({count:,})")

progress.empty()

df = pd.DataFrame(records).sort_values("age_num")

# ── Denominator for % mode ────────────────────────────────────────────────────

if show_pct:
    totals = {}
    for age in ages_selected:
        totals[age] = fetch_bill_count(API_KEY, age, "")
    df["total"] = df["age_num"].astype(str).map(totals)
    df["value"] = (df["count"] / df["total"] * 100).round(2)
    y_label = "% of all bills"
    hover_fmt = "%{y:.2f}%"
else:
    df["value"] = df["count"]
    y_label = "Number of bills"
    hover_fmt = "%{y:,}"

# ── Chart 1: grouped bar — keywords × assemblies ──────────────────────────────

st.markdown("### Bill volume by assembly")

fig_bar = px.bar(
    df, x="Assembly", y="value", color="Keyword",
    barmode="group",
    title="Keyword volume per assembly" + (" (% of total)" if show_pct else ""),
    labels={"value": y_label, "Assembly": ""},
    text="value",
    height=420,
)
fig_bar.update_traces(
    texttemplate=("%{text:.1f}%" if show_pct else "%{text:,}"),
    textposition="outside",
)
fig_bar.update_layout(legend=dict(orientation="h", y=1.1), margin=dict(t=60, b=40))
st.plotly_chart(fig_bar, use_container_width=True)

# ── Chart 2: line chart trend across assemblies ───────────────────────────────

if len(ages_selected) >= 3 and len(keywords) > 1:
    st.markdown("### Trend across assemblies")
    fig_line = px.line(
        df, x="Assembly", y="value", color="Keyword",
        markers=True,
        title="Keyword trend (16대 = 2000, 22대 = 2024–present)" + (" (% of total)" if show_pct else ""),
        labels={"value": y_label, "Assembly": "Assembly"},
        height=380,
    )
    fig_line.update_layout(legend=dict(orientation="h", y=1.1))
    st.plotly_chart(fig_line, use_container_width=True)

# ── Chart 3: within-assembly date distribution ────────────────────────────────

if len(keywords) == 1 and keywords[0]:
    st.markdown(f"### Monthly filing pattern — '{keywords[0]}'")
    st.caption("Based on up to 100 bills per assembly.")

    all_dated = []
    for age in ages_selected:
        rows, _ = fetch_bills_sample(API_KEY, age, keywords[0], page_size=100)
        for r in rows:
            dt = r.get("PROPOSE_DT", "")
            if dt and len(dt) >= 7:
                all_dated.append({
                    "Assembly": f"{age}대",
                    "YearMonth": dt[:7],
                    "age_num": int(age),
                })

    if all_dated:
        df_dated = pd.DataFrame(all_dated)
        monthly = (
            df_dated.groupby(["Assembly", "YearMonth"])
            .size().reset_index(name="count")
            .sort_values("YearMonth")
        )
        fig_time = px.line(
            monthly, x="YearMonth", y="count", color="Assembly",
            title=f"Monthly bill filings — '{keywords[0]}'",
            labels={"YearMonth": "Month", "count": "Bills filed"},
            markers=False,
            height=380,
        )
        fig_time.update_xaxes(tickangle=-45)
        st.plotly_chart(fig_time, use_container_width=True)

# ── Table ─────────────────────────────────────────────────────────────────────

st.markdown("### Data table")

pivot = df.pivot_table(index="Keyword", columns="Assembly", values="value", aggfunc="first")
pivot.columns.name = None
pivot.index.name = "Keyword"
st.dataframe(
    pivot.style.format(("{:.2f}" if show_pct else "{:,.0f}")),
    use_container_width=True,
)

st.download_button(
    "Download CSV",
    df[["Keyword", "Assembly", "count"]].to_csv(index=False).encode("utf-8-sig"),
    "bill_trends.csv",
    "text/csv",
)
