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
        "Search member-sponsored bills by keyword, proposer, committee, "
        "or processing outcome. Filter across the 18th–22nd assemblies."
    )
    st.page_link("pages/1_Bills.py", label="Search Bills →", icon="📜")

with col2:
    st.markdown("### 👤 Members")
    st.markdown(
        "Look up National Assembly members by party, district, or committee. "
        "See party distribution and member rosters."
    )
    st.page_link("pages/2_Members.py", label="Browse Members →", icon="👤")

with col3:
    st.markdown("### 🗳️ Vote Results")
    st.markdown(
        "Query plenary vote tallies for any bill — yes, no, abstain, absent. "
        "Visualize vote breakdowns at a glance."
    )
    st.page_link("pages/3_Votes.py", label="View Votes →", icon="🗳️")

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
- 18th–22nd National Assembly (2008–present)
- Bills, members, vote results, committee rosters, co-sponsor networks

**Built with** Python · Streamlit · httpx ·
[open-assembly-mcp](https://github.com/kyusik-yang/open-assembly-mcp)
    """)

st.markdown("---")
st.caption(
    "Data source: [열린국회정보](https://open.assembly.go.kr) — "
    "Korean National Assembly Open API. "
    "Not affiliated with or endorsed by the National Assembly."
)
