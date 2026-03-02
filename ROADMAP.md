# Assembly Explorer — Future Improvements

Deployed at: https://national-assembly-kr.streamlit.app/
GitHub: https://github.com/kyusik-yang/assembly-explorer

This file captures design and feature improvements to revisit in future sessions.
Priority levels: 🔴 High / 🟡 Medium / 🟢 Nice-to-have

---

## Design

- 🔴 **Mobile layout**: current sidebar layout collapses poorly on phones — switch to top-filter expander on mobile
- 🟡 **Custom CSS**: add a thin blue header bar with logo/title, improve typography (larger headings, better spacing)
- 🟡 **Color palette consistency**: unify chart colors across all three pages (currently each page uses a different Plotly scheme)
- 🟡 **Loading skeleton**: replace spinner with a skeleton placeholder so the layout doesn't jump when data loads
- 🟢 **Dark mode support**: test and tweak `.streamlit/config.toml` for dark mode users
- 🟢 **Favicon and social preview image** for when the URL is shared on social media or Squarespace

---

## Features — Bills page

- ✅ **Pagination info**: shows "X of N total" with note to increase page size
- ✅ **Filter by date range**: `propose_dt_from` / `propose_dt_to` (YYYYMMDD)
- ✅ **Member votes tab**: per-member vote breakdown (party bar chart + table) inside bill detail section
- ✅ **Assembly 16th/17th**: age selector now includes 16/17
- ✅ **Bulk export**: auto-paginate all results up to 5,000 records with progress; CSV download
- 🔴 **Timeline chart**: bar chart of bills filed by month/year to show legislative activity over time
- 🟡 **Co-sponsor network graph**: visualize the co-sponsorship network using `pyvis` or `networkx` + Plotly
- 🟢 **Export to Excel** (`.xlsx`) in addition to CSV, with auto-formatted columns
- 🟢 **Bookmark/share URL**: encode current filter state in the URL so a search can be shared as a link

---

## Features — Members page

- ✅ **Total count display**: shows "X of N total" with overflow notice
- ✅ **Assembly 16th/17th**: age selector now includes 16/17
- ✅ **Member Profile page** (`5_Member_Profile.py`): bills proposed (auto-paginated + bulk CSV) + recent vote record (parallel fetch, 30 bills)
- 🟡 **Member profile click-through**: click a member name in the roster → redirect to profile page
- 🟡 **Cross-assembly seat comparison**: bar chart comparing party seat counts across 20th/21st/22nd assemblies side by side
- 🟡 **Gender breakdown chart**: currently a column in the table but not visualized
- 🟢 **District map**: if GeoJSON data is available, show a choropleth of seats by region

---

## Features — Votes page

- ✅ **Party-level vote breakdown**: per-member votes grouped by party, rendered as grouped bar chart inside each bill expander
- ✅ **Total count display**: shows "X of N total"
- ✅ **Assembly 16th/17th**: age selector now includes 16/17
- 🟡 **Pass rate over time**: line chart showing monthly/annual bill pass rates for a given assembly
- 🟡 **Controversial bill detector**: highlight bills where yes/no margin was narrow (e.g., < 10 votes)
- 🟢 **Vote comparison across assemblies**: same bill topic searched across multiple assemblies

---

## Features — New pages to add

- ✅ **Committee Explorer** (`4_Committee.py`): browse any committee, see party composition pie/stats and member roster
- 🟡 **Bill Journey**: enter a bill number → see the full timeline from filing → committee review → plenary vote, displayed as a horizontal flowchart
- 🟡 **About / How to Use**: a proper help page explaining each tool, API key setup, and link to the MCP repo and tutorial

---

## Technical

- ✅ **`@st.cache_data` caching**: all API calls wrapped with TTL=1h cache
- ✅ **Tuple return from client**: `_parse()` returns `(rows, total_count)` for pagination metadata
- ✅ **`get_member_votes` in client**: new method for `nojepdqqaweusdfbi` endpoint
- ✅ **Date filter in `search_bills`**: `STR_DT` / `END_DT` params
- 🟡 **Async-native**: Streamlit 1.41+ supports `async` natively — remove `asyncio.run()` wrappers
- 🟡 **Error messages**: improve user-facing error messages (distinguish between "no results", "API key error", "network timeout")
- 🟢 **Unit tests for the client**: add a small test suite that mocks API responses
- 🟢 **GitHub Actions CI**: auto-run tests on push

---

## Integration with other projects

- 🔴 **Chatbot page (Phase 3)**: add a fourth page powered by Claude API with `tool_use`, letting visitors ask free-form questions that trigger the Assembly API tools — the most "wow" feature, needs Anthropic API key + backend
- 🟡 **Link to Quarto tutorial**: once the tutorial site is live (Phase 2), add a banner/link on the Home page
- 🟡 **Link from Squarespace homepage**: embed the Streamlit URL as an iFrame or link button in the personal website

---

## Notes for next session

- Streamlit Cloud auto-redeploys on `git push origin main` — no manual redeploy needed
- API key is stored in Streamlit Cloud secrets (not in the repo)
- Local dev: put the key in `.streamlit/secrets.toml` (gitignored)
- Phase 2 (Quarto tutorial site) not yet started — see task list
