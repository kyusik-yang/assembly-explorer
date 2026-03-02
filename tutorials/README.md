# Tutorials — Korean National Assembly Data

Interactive Jupyter notebooks for collecting and analyzing Korean legislative data
via the [열린국회정보 API](https://open.assembly.go.kr).
Each notebook runs end-to-end on **Google Colab** (free) with no local setup.

---

## Before you start: get a free API key

1. Go to [open.assembly.go.kr](https://open.assembly.go.kr)
2. Sign up (무료 회원가입) — it takes about 2 minutes
3. 마이페이지 → API 키 발급 → copy your key (looks like `d74b52f3...`)

**In Colab:** left sidebar → Secrets (lock icon) → add `ASSEMBLY_API_KEY` with your key.
This keeps your key out of the notebook and persists across sessions.

---

## Tutorials

| # | Notebook | Topic | Open in Colab |
|---|---|---|---|
| 01 | [Getting Started](./01_getting_started.ipynb) | API basics, bills, members, vote tallies, bulk export | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/kyusik-yang/assembly-explorer/blob/main/tutorials/01_getting_started.ipynb) |
| 02 | [Voting Analysis](./02_voting_analysis.ipynb) | Party discipline (Rice index), defection, roll-call panels | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/kyusik-yang/assembly-explorer/blob/main/tutorials/02_voting_analysis.ipynb) |
| 03 | [Network Analysis](./03_network_analysis.ipynb) | Co-sponsorship graph, centrality, community detection, cross-party links | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/kyusik-yang/assembly-explorer/blob/main/tutorials/03_network_analysis.ipynb) |

---

## What data is available?

| Method | Endpoint | Description |
|---|---|---|
| `search_bills` | `nzmimeepazxkubdpn` | Member-sponsored bills — keyword, proposer, committee, date, outcome |
| `get_members` | `nwvrqwxyaytdsfvhu` | Member rosters — party, district, committee, election type |
| `get_vote_results` | `ncocpgfiaoituanbr` | Plenary vote tallies per bill (yes/no/abstain totals) |
| `get_member_votes` | `nojepdqqaweusdfbi` | Individual roll-call votes per bill |
| `get_bill_proposers` | `BILLINFOPPSR` | Full proposer list (lead + co-sponsors) for a bill |
| `get_bill_review` | `nwbpacrgavhjryiph` | Legislative timeline — dates for each stage |

**Coverage:** 16th–22nd National Assembly (2000–present). Member-sponsored bills only.

---

## Tips

- **Rate limits:** The API allows roughly 2 requests/second. The notebooks add short
  `time.sleep()` pauses automatically when bulk-fetching.
- **Korean text in Stata/Excel:** All CSV exports use UTF-8 with BOM (`utf-8-sig`).
  In Stata: `import delimited ..., encoding(utf8)`. In Excel: open directly.
- **Increasing data volume:** Each notebook has a `MAX_BILLS` or `N_BILLS` variable
  you can increase. Start small (20-50) to verify your API key works, then scale up.
- **Interactive app:** The same data is available through a live Streamlit app at
  [national-assembly-kr.streamlit.app](https://national-assembly-kr.streamlit.app) —
  useful for exploration before writing code.
