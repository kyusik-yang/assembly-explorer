# Assembly Explorer

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://national-assembly-kr.streamlit.app)

Interactive web app for exploring Korean National Assembly legislative data,
powered by the [열린국회정보 API](https://open.assembly.go.kr).

**Live app:** [national-assembly-kr.streamlit.app](https://national-assembly-kr.streamlit.app)

---

## Features

| Page | What you can do |
|---|---|
| 📜 Bills | Search member-sponsored bills by keyword, proposer, committee, date, or outcome. Bulk-export up to 5,000 records as CSV. |
| 👤 Members | Browse member rosters by party, district, or committee. View seat distribution charts. |
| 🗳️ Votes | Query plenary vote tallies. Drill down to per-member roll calls and party cohesion (Rice index). |
| 🏛️ Committees | Browse committee rosters and party composition for any standing or special committee. |
| 🔍 Member Profile | Full activity view for a single legislator: all bills proposed and recent vote record. |
| 🕸️ Network | Co-sponsorship network for a bill set: force-directed graph, centrality, community detection. |
| 🗺️ Bill Journey | Step-by-step legislative timeline for a bill: filing date through promulgation. |
| 📈 Trends | Compare bill volumes for keywords across multiple assemblies. |

**Data coverage:** 16th–22nd National Assembly (2000–present). Member-sponsored bills only.

---

## Tutorials

Jupyter notebooks for researchers — runnable on Google Colab with no local setup:

| Notebook | Topic |
|---|---|
| [01 Getting Started](tutorials/01_getting_started.ipynb) | API basics, bill/member/vote collection, bulk export |
| [02 Voting Analysis](tutorials/02_voting_analysis.ipynb) | Rice index, defection labeling, roll-call panel dataset |
| [03 Network Analysis](tutorials/03_network_analysis.ipynb) | Co-sponsorship graph, centrality, community detection |

See [tutorials/README.md](tutorials/README.md) for API key setup and usage tips.

---

## Run locally

```bash
git clone https://github.com/kyusik-yang/assembly-explorer.git
cd assembly-explorer
pip install -r requirements.txt

export ASSEMBLY_API_KEY="your-key-here"
streamlit run Home.py
```

Get a free API key at [open.assembly.go.kr](https://open.assembly.go.kr) (마이페이지 → API 키 발급).

---

## Related

- [open-assembly-mcp](https://github.com/kyusik-yang/open-assembly-mcp) — MCP server that exposes the same data to AI assistants (Claude, etc.)

---

*Data source: [열린국회정보](https://open.assembly.go.kr). Not affiliated with or endorsed by the Korean National Assembly.*
