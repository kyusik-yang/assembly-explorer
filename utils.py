"""Shared utilities for Assembly Explorer pages."""

import pandas as pd
import networkx as nx
import plotly.graph_objects as go


# ── Rice index ─────────────────────────────────────────────────────────────────

PARTY_COLORS = {
    "더불어민주당":   "#004EA2",
    "국민의힘":       "#E61E2B",
    "개혁신당":       "#FF7210",
    "조국혁신당":     "#0095DA",
    "진보당":         "#D6001C",
    "새로운미래":     "#00B050",
    "무소속":         "#888888",
}

VOTE_COLORS = {
    "찬성": "#2ECC71",
    "반대": "#E74C3C",
    "기권": "#BDC3C7",
    "불참": "#ECF0F1",
}


def compute_rice_index(vdf: pd.DataFrame) -> pd.DataFrame:
    """
    Compute Rice index per party from a member-vote DataFrame.
    vdf must have columns: POLY_NM, RESULT_VOTE_MOD

    Rice index = |Yea - Nay| / (Yea + Nay) * 100
    Range: 0 (perfectly split) to 100 (unanimous).
    """
    summary = []
    for party, grp in vdf.groupby("POLY_NM"):
        vc    = grp["RESULT_VOTE_MOD"].value_counts()
        yea   = int(vc.get("찬성", 0))
        nay   = int(vc.get("반대", 0))
        abst  = int(vc.get("기권", 0))
        absent = int(vc.get("불참", 0))
        denom = yea + nay
        rice  = round(abs(yea - nay) / denom * 100, 1) if denom > 0 else None
        summary.append({
            "Party":      party,
            "Yea (찬성)": yea,
            "Nay (반대)": nay,
            "Abstain":    abst,
            "Absent":     absent,
            "Rice Index": rice,
        })
    return (
        pd.DataFrame(summary)
        .sort_values("Rice Index", ascending=False, na_position="last")
        .fillna({"Rice Index": "—"})
    )


# ── Co-sponsorship network ─────────────────────────────────────────────────────

def build_cosponsor_graph(
    bills: list[dict],
    proposers_map: dict[str, list[dict]],
) -> nx.Graph:
    """
    Build undirected co-sponsorship graph.

    bills: list of bill dicts (must have BILL_ID, BILL_NAME)
    proposers_map: {BILL_ID: list of proposer dicts (PPSR_NM, PPSR_POLY_NM, REP_DIV)}

    Nodes: member names (attr: party)
    Edges: two members who co-sponsored the same bill (weight = # shared bills)
    """
    G = nx.Graph()

    for bill in bills:
        bill_id = bill.get("BILL_ID", "")
        proposers = proposers_map.get(bill_id, [])
        if not proposers:
            continue

        members = [
            (p.get("PPSR_NM", ""), p.get("PPSR_POLY_NM", "기타"))
            for p in proposers
            if p.get("PPSR_NM")
        ]

        for name, party in members:
            if name not in G:
                G.add_node(name, party=party)

        # Add edges between all pairs (lead + co-sponsors)
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                a, _ = members[i]
                b, _ = members[j]
                if G.has_edge(a, b):
                    G[a][b]["weight"] += 1
                else:
                    G.add_edge(a, b, weight=1)

    return G


def network_figure(G: nx.Graph, title: str = "Co-sponsorship Network") -> go.Figure:
    """Render a networkx Graph as a Plotly figure."""
    if len(G.nodes) == 0:
        return go.Figure()

    k = 2.0 / max(len(G.nodes) ** 0.5, 1)
    pos = nx.spring_layout(G, k=k, iterations=60, seed=42)

    # Edge traces (width ~ weight)
    edge_traces = []
    for a, b, data in G.edges(data=True):
        x0, y0 = pos[a]
        x1, y1 = pos[b]
        w = data.get("weight", 1)
        edge_traces.append(go.Scatter(
            x=[x0, x1, None], y=[y0, y1, None],
            mode="lines",
            line=dict(width=min(w * 0.6 + 0.3, 4), color="rgba(150,150,150,0.5)"),
            hoverinfo="none",
            showlegend=False,
        ))

    # Node traces grouped by party
    party_groups: dict[str, dict] = {}
    for node in G.nodes():
        party = G.nodes[node].get("party", "기타")
        deg   = G.degree(node)
        x, y  = pos[node]
        if party not in party_groups:
            party_groups[party] = {"x": [], "y": [], "text": [], "size": []}
        party_groups[party]["x"].append(x)
        party_groups[party]["y"].append(y)
        party_groups[party]["text"].append(
            f"<b>{node}</b><br>Party: {party}<br>Co-sponsors: {deg}"
        )
        party_groups[party]["size"].append(max(8, deg * 3))

    node_traces = [
        go.Scatter(
            x=data["x"], y=data["y"],
            mode="markers",
            name=party,
            hoverinfo="text",
            text=data["text"],
            marker=dict(
                color=PARTY_COLORS.get(party, "#888888"),
                size=data["size"],
                line=dict(width=1, color="white"),
            ),
        )
        for party, data in party_groups.items()
    ]

    fig = go.Figure(
        data=edge_traces + node_traces,
        layout=go.Layout(
            title=title,
            showlegend=True,
            hovermode="closest",
            margin=dict(b=20, l=5, r=5, t=50),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            height=600,
            paper_bgcolor="white",
        ),
    )
    return fig


# ── Bill journey timeline ──────────────────────────────────────────────────────

JOURNEY_STAGES = [
    ("PROPOSE_DT",          "📄 발의",         "Filed"),
    ("COMMITTEE_PRESENT_DT","🏛 소관위 회부",   "Referred to committee"),
    ("COMMITTEE_PROC_DT",   "✅ 소관위 의결",   "Committee decision"),
    ("LAW_SUBMIT_DT",       "📋 법사위 회부",   "Law committee referred"),
    ("LAW_PRESENT_DT",      "📋 법사위 심사",   "Law committee review"),
    ("LAW_PROC_DT",         "🗳 본회의 의결",    "Plenary vote"),
    ("RGS_PRESENT_DT",      "📨 정부 이송",     "Sent to government"),
    ("RGS_PROC_DT",         "📰 공포",          "Promulgated"),
    ("ANNOUNCE_DT",         "📢 시행",          "Enacted"),
]


def journey_figure(row: dict) -> go.Figure:
    """Build a vertical timeline figure from a bill_review row."""
    stages = []
    for field, label_kr, label_en in JOURNEY_STAGES:
        dt = row.get(field)
        if dt:
            stages.append((label_kr, str(dt)))

    if not stages:
        return go.Figure()

    n = len(stages)
    y_vals = list(range(n, 0, -1))

    # Node markers
    node_trace = go.Scatter(
        x=[0.5] * n,
        y=y_vals,
        mode="markers+text",
        marker=dict(size=16, color="#1f77b4", symbol="circle"),
        text=[s[0] for s in stages],
        textposition="middle right",
        textfont=dict(size=13),
        hovertext=[f"{s[0]}<br>{s[1]}" for s in stages],
        hoverinfo="text",
        showlegend=False,
    )

    # Date labels on the left
    date_trace = go.Scatter(
        x=[0.0] * n,
        y=y_vals,
        mode="text",
        text=[s[1] for s in stages],
        textposition="middle left",
        textfont=dict(size=11, color="#555"),
        hoverinfo="none",
        showlegend=False,
    )

    # Vertical connector line
    line_x = [0.5, 0.5]
    line_y = [y_vals[-1] - 0.3, y_vals[0] + 0.3]
    line_trace = go.Scatter(
        x=line_x, y=line_y,
        mode="lines",
        line=dict(color="#aaa", width=2, dash="dot"),
        hoverinfo="none",
        showlegend=False,
    )

    fig = go.Figure(
        data=[line_trace, node_trace, date_trace],
        layout=go.Layout(
            margin=dict(l=80, r=40, t=30, b=20),
            height=max(250, n * 55),
            xaxis=dict(
                showgrid=False, zeroline=False, showticklabels=False,
                range=[-0.3, 1.5],
            ),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            paper_bgcolor="white",
            plot_bgcolor="white",
        ),
    )
    return fig
