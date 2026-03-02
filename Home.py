"""Home page — Korean National Assembly Explorer."""

import streamlit as st

st.set_page_config(
    page_title="Assembly Explorer",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🏛️ Korean National Assembly Explorer")
st.subheader("Explore Korean legislative data powered by 열린국회정보 Open API")

st.markdown("---")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### 📜 Bills")
    st.markdown(
        "Search member-sponsored bills by keyword, proposer, committee, or outcome. "
        "Bulk-export full datasets for statistical analysis."
    )
    st.page_link("pages/1_Bills.py", label="Search Bills →", icon="📜")

with col2:
    st.markdown("### 🗳️ Vote Results")
    st.markdown(
        "Query plenary vote tallies for any bill — yes, no, abstain. "
        "Drill down to per-member and party-level breakdowns."
    )
    st.page_link("pages/3_Votes.py", label="View Votes →", icon="🗳️")

with col3:
    st.markdown("### 🏛️ Committees")
    st.markdown(
        "Browse committee rosters and party composition for any standing "
        "or special committee, across all assemblies."
    )
    st.page_link("pages/4_Committee.py", label="Explore Committees →", icon="🏛️")

st.markdown("")
col4, col5, _ = st.columns(3)

with col4:
    st.markdown("### 👤 Members")
    st.markdown(
        "Look up National Assembly members by party, district, or committee. "
        "See party distribution and member rosters."
    )
    st.page_link("pages/2_Members.py", label="Browse Members →", icon="👤")

with col5:
    st.markdown("### 🔍 Member Profile")
    st.markdown(
        "Full legislative activity for a single member — all bills proposed, "
        "recent vote record, and committee affiliation. Bulk-exportable."
    )
    st.page_link("pages/5_Member_Profile.py", label="View Profile →", icon="🔍")

st.markdown("")
col6, col7, _ = st.columns(3)

with col6:
    st.markdown("### 🕸️ Co-sponsorship Network")
    st.markdown(
        "Visualize the co-sponsorship network for a set of bills. "
        "See who legislates together and how coalitions cluster by party."
    )
    st.page_link("pages/6_Network.py", label="View Network →", icon="🕸️")

with col7:
    st.markdown("### 🗺️ Bill Journey")
    st.markdown(
        "Full legislative timeline for a single bill — filing, committee review, "
        "plenary vote, and promulgation with exact dates."
    )
    st.page_link("pages/7_Bill_Journey.py", label="View Journey →", icon="🗺️")

st.markdown("---")

with st.expander("What is this?", expanded=True):
    st.markdown("""
This app provides a live, interactive window into Korean legislative data via the
[열린국회정보 API](https://open.assembly.go.kr). Every query hits the official
National Assembly database in real time — no cached or static data.

It is built as a companion to the
[open-assembly-mcp](https://github.com/kyusik-yang/open-assembly-mcp) project,
an **MCP (Model Context Protocol) server** that lets AI assistants like Claude
call the same API directly within a conversation. If you are a researcher or
developer who wants to integrate Korean legislative data into AI workflows,
check out the MCP server.

**Data coverage**
- 16th–22nd National Assembly (2000–present)
- Bills, members, vote results, committee rosters, co-sponsor networks, per-member votes

**Built with** Python · Streamlit · httpx ·
[open-assembly-mcp](https://github.com/kyusik-yang/open-assembly-mcp)
    """)

st.markdown("---")
st.caption(
    "Data source: [열린국회정보](https://open.assembly.go.kr) — "
    "Korean National Assembly Open API. "
    "Not affiliated with or endorsed by the National Assembly."
)
