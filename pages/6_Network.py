"""Co-sponsorship network page."""

import asyncio
import networkx as nx
import pandas as pd
import streamlit as st

from client import AGE_OPTIONS, AssemblyClient
from utils import build_cosponsor_graph, network_figure, inject_mobile_css

st.set_page_config(
    page_title="Co-sponsorship Network · Assembly Explorer",
    page_icon="🕸️", layout="wide",
)

API_KEY = st.secrets.get("ASSEMBLY_API_KEY", "") or __import__("os").getenv("ASSEMBLY_API_KEY", "")


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_bills_for_network(api_key, age, bill_name, committee, proposer, page_size):
    async def _run():
        async with AssemblyClient(api_key) as c:
            return await c.search_bills(
                age=age,
                bill_name=bill_name or None,
                committee=committee or None,
                proposer=proposer or None,
                page_size=page_size,
            )
    return asyncio.run(_run())


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_all_proposers(api_key, bill_ids: tuple):
    """Fetch co-sponsors for multiple bills in parallel."""
    async def _run():
        async with AssemblyClient(api_key) as c:
            tasks = [c.get_bill_proposers(bid) for bid in bill_ids]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        out = {}
        for bid, result in zip(bill_ids, results):
            if isinstance(result, Exception) or not result:
                continue
            rows, _ = result
            out[bid] = rows
        return out
    return asyncio.run(_run())


inject_mobile_css()
st.title("🕸️ Co-sponsorship Network")
st.caption(
    "Visualize the co-sponsorship network for a set of bills — "
    "who proposes legislation together, and how coalitions cluster by party."
)

with st.sidebar:
    st.header("Filters")
    age       = st.selectbox("Assembly (대수)", AGE_OPTIONS, index=0)
    bill_name = st.text_input("Bill keyword", placeholder="예: 인공지능, 반도체, 주거")
    committee = st.text_input("Committee", placeholder="예: 과학기술정보방송통신위원회")
    proposer  = st.text_input("Lead proposer (optional)", placeholder="예: 홍길동")
    n_bills   = st.slider(
        "Bills to include in network",
        min_value=10, max_value=100, value=40, step=10,
        help="More bills = denser network but slower to build.",
    )
    search_btn = st.button("Build Network", type="primary", use_container_width=True)
    st.markdown("---")
    st.caption(
        "Node size = number of co-sponsorship links (degree). "
        "Edge thickness = number of bills co-proposed together. "
        "Color = party."
    )

if not API_KEY:
    st.warning("No API key found.")
    st.stop()

if not search_btn:
    st.info("Set filters in the sidebar and click **Build Network**. (On mobile, tap **>>** at the top left to open the sidebar.)")
    st.stop()

# ── Step 1: Fetch bills ────────────────────────────────────────────────────────
with st.spinner("Fetching bills..."):
    try:
        bills, total = fetch_bills_for_network(
            API_KEY, age, bill_name, committee, proposer, n_bills,
        )
    except Exception as e:
        st.error(f"API error: {e}")
        st.stop()

if not bills:
    st.info("No bills found. Try different filters.")
    st.stop()

bill_ids = tuple(b["BILL_ID"] for b in bills if "BILL_ID" in b)
st.markdown(f"**{len(bills)} bills** retrieved (of {total:,} total) — fetching co-sponsors...")

# ── Step 2: Fetch co-sponsors in parallel ─────────────────────────────────────
with st.spinner(f"Loading co-sponsors for {len(bill_ids)} bills in parallel..."):
    try:
        proposers_map = fetch_all_proposers(API_KEY, bill_ids)
    except Exception as e:
        st.error(f"Failed to load co-sponsors: {e}")
        st.stop()

covered = len(proposers_map)
st.caption(f"Co-sponsor data found for {covered} of {len(bill_ids)} bills.")

# ── Step 3: Build graph ────────────────────────────────────────────────────────
G = build_cosponsor_graph(bills, proposers_map)

if len(G.nodes) == 0:
    st.warning("Could not build a network — no co-sponsor data available for this filter.")
    st.stop()

# ── Stats ──────────────────────────────────────────────────────────────────────
m1, m2, m3, m4 = st.columns(4)
m1.metric("Members (nodes)",  len(G.nodes))
m2.metric("Co-sponsor links", len(G.edges))
density = nx.density(G)
m3.metric("Network density",  f"{density:.3f}")
try:
    components = nx.number_connected_components(G)
    m4.metric("Components", components)
except Exception:
    pass

# ── Network figure ─────────────────────────────────────────────────────────────
title_parts = [f"{age}th Assembly"]
if bill_name:
    title_parts.append(f'"{bill_name}"')
if committee:
    title_parts.append(committee)
title = "Co-sponsorship Network — " + " · ".join(title_parts)

fig = network_figure(G, title=title)
st.plotly_chart(fig, use_container_width=True)

# ── Top co-sponsoring pairs ────────────────────────────────────────────────────
st.markdown("#### Top co-sponsoring pairs")
edges_df = pd.DataFrame([
    {
        "Member A": a,
        "Party A":  G.nodes[a].get("party", ""),
        "Member B": b,
        "Party B":  G.nodes[b].get("party", ""),
        "Shared bills": data["weight"],
    }
    for a, b, data in G.edges(data=True)
]).sort_values("Shared bills", ascending=False)

st.dataframe(edges_df.head(30), use_container_width=True, height=300)

# ── Top nodes by degree ────────────────────────────────────────────────────────
st.markdown("#### Most connected members")
degree_df = pd.DataFrame([
    {
        "Member":  n,
        "Party":   G.nodes[n].get("party", ""),
        "Co-sponsor links": G.degree(n),
        "Total bill weight": sum(d["weight"] for _, _, d in G.edges(n, data=True)),
    }
    for n in G.nodes()
]).sort_values("Co-sponsor links", ascending=False)

st.dataframe(degree_df.head(20), use_container_width=True, height=300)

st.download_button(
    "⬇ Download edge list (CSV)",
    data=edges_df.to_csv(index=False).encode("utf-8-sig"),
    file_name=f"cosponsor_network_{age}_{bill_name or 'all'}.csv",
    mime="text/csv",
)
