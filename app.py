"""LoL Esport debrief & scouting dashboard (Streamlit).

Run from the project root with the venv active:
    streamlit run app.py
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from config import LEAGUEPEDIA
from src.api import LeaguepediaClient
from src.db import get_engine
from src.dashboard import catalog, queries as q
from src.etl.run import ingest_tournament_steps

st.set_page_config(page_title="LoL Esport — Debrief & Scouting", page_icon="🎮", layout="wide")


# --------------------------------------------------------------- resources
@st.cache_resource
def engine():
    return get_engine()


@st.cache_data(ttl=600)
def cached(fn_name: str, *args):
    """Cache any queries.* function call by name + args."""
    return getattr(q, fn_name)(engine(), *args)


@st.cache_data(ttl=3600)
def load_catalog():
    return catalog.load_catalog(engine())


def hbar(df: pd.DataFrame, x: str, y: str, title: str, color: str | None = None):
    if df.empty:
        st.info("No data.")
        return
    fig = px.bar(df, x=x, y=y, orientation="h", title=title, color=color,
                 color_continuous_scale="Tealrose" if color else None)
    fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=max(280, 26 * len(df)),
                      margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig, width="stretch")


# ------------------------------------------------------------------ filters
st.sidebar.title("🎮 Filters")
try:
    tdf = cached("tournaments")
except Exception as exc:  # pragma: no cover - surfaced in UI
    st.error(f"Could not reach the database. Is PostgreSQL running and `.env` set?\n\n{exc}")
    st.stop()

if tdf.empty:
    st.warning("No data yet. Ingest a tournament first, e.g. "
               "`python -m src.etl.run tournament \"MSI 2025\"`.")
    st.stop()

# Show the friendly name, filter internally by overviewpage (the reliable key).
name_to_op = dict(zip(tdf["name"], tdf["overviewpage"]))
tournament = st.sidebar.selectbox("Tournament", list(name_to_op))
overview = name_to_op[tournament]
st.sidebar.caption("Filters apply across all tabs.")

st.title("LoL Esport — Debrief & Scouting")
st.caption(f"Tournament: **{tournament}**")

tab_overview, tab_team, tab_player, tab_draft, tab_add = st.tabs(
    ["📊 Overview", "🛡️ Team scouting", "🧍 Player", "🚫 Draft", "➕ Add data"]
)

# ------------------------------------------------------------------ overview
with tab_overview:
    k = cached("overview_kpis", overview)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Games", int(k["games"]))
    c2.metric("Teams", int(k["teams"]))
    patches = int(k["patches"] or 0)
    if patches == 1:
        c3.metric("Patch", k["patch_list"])
    else:
        c3.metric("Patches", patches, help=k["patch_list"] or None)
    c4.metric("Avg game length (min)", k["avg_len_min"])
    if pd.notna(k["first_game"]):
        st.caption(f"From {pd.to_datetime(k['first_game']).date()} "
                   f"to {pd.to_datetime(k['last_game']).date()}")

    col1, col2 = st.columns(2)
    with col1:
        picks = cached("top_picks", overview).head(15)
        hbar(picks, x="picks", y="champion", title="Most-picked champions", color="winrate_pct")
    with col2:
        bans = cached("top_bans", overview).head(15)
        hbar(bans, x="bans", y="champion", title="Most-banned champions")


# ------------------------------------------------------------- team scouting
with tab_team:
    team_list = cached("teams", overview)
    team = st.selectbox("Team", team_list, key="team_select")
    if team:
        rec = cached("team_record", team, overview)
        obj = cached("team_objectives", team, overview)
        games = int(rec["games"]) or 1

        def wr(w, g):
            return f"{(100 * w / g):.0f}%" if g else "—"

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Record", f"{int(rec['wins'])}-{int(rec['games'] - rec['wins'])}",
                  wr(rec["wins"], rec["games"]))
        c2.metric("Blue side", f"{int(rec['blue_wins'])}/{int(rec['blue_games'])}",
                  wr(rec["blue_wins"], rec["blue_games"]))
        c3.metric("Red side", f"{int(rec['red_wins'])}/{int(rec['red_games'])}",
                  wr(rec["red_wins"], rec["red_games"]))
        c4.metric("Avg kills / game", obj["kills"])

        st.subheader("Objective control (avg / game)")
        o1, o2, o3, o4, o5 = st.columns(5)
        o1.metric("🐉 Dragons", obj["dragons"])
        o2.metric("🟣 Barons", obj["barons"])
        o3.metric("🗼 Towers", obj["towers"])
        o4.metric("👁️ Heralds", obj["heralds"])
        o5.metric("🐛 Grubs", obj["grubs"])

        col1, col2 = st.columns(2)
        with col1:
            pool = cached("team_champion_pool", team, overview)
            hbar(pool.head(15), x="games", y="champion",
                 title="Champion pool (picks)", color="winrate_pct")
        with col2:
            bans = cached("team_bans", team, overview)
            hbar(bans.head(15), x="bans", y="champion", title="Bans by this team")

        st.subheader("Recent games")
        st.dataframe(cached("team_games", team, overview), width="stretch", hide_index=True)


# ------------------------------------------------------------------- player
with tab_player:
    team_list = [""] + cached("teams", overview)
    pteam = st.selectbox("Team (optional)", team_list, key="player_team")
    plist = cached("players", overview, pteam or None)
    player = st.selectbox("Player", plist, key="player_select") if plist else None
    if player:
        s = cached("player_summary", player, overview)
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Games", int(s["games"]))
        c2.metric("KDA", s["kda"], f"{s['k']}/{s['d']}/{s['a']}")
        c3.metric("Win rate", f"{s['winrate_pct']}%")
        c4.metric("Avg CS", int(s["cs"]) if pd.notna(s["cs"]) else "—")
        c5.metric("Avg damage", f"{int(s['dmg']):,}" if pd.notna(s["dmg"]) else "—")

        col1, col2 = st.columns([1, 1])
        with col1:
            champs = cached("player_champions", player, overview)
            hbar(champs.head(15), x="games", y="champion",
                 title="Champion pool", color="winrate_pct")
        with col2:
            st.subheader("Game log")
            st.dataframe(cached("player_games", player, overview),
                         width="stretch", hide_index=True)


# -------------------------------------------------------------------- draft
with tab_draft:
    col1, col2 = st.columns(2)
    with col1:
        picks = cached("top_picks", overview)
        st.subheader("Picks")
        st.dataframe(picks, width="stretch", hide_index=True)
    with col2:
        bans = cached("top_bans", overview)
        st.subheader("Bans")
        st.dataframe(bans, width="stretch", hide_index=True)


# ------------------------------------------------------------------ add data
def run_ingest(tournament_name: str):
    """Run the ingest with live status; refresh caches + rerun on success."""
    try:
        counts: dict[str, int] = {}
        with st.status(f"Ingesting “{tournament_name}”…", expanded=True) as status:
            for label, rows in ingest_tournament_steps(tournament_name):
                counts[label] = rows
                st.write(f"**{label}:** {rows} rows")
                if label == "Tournament metadata" and rows == 0:
                    status.update(label="No match", state="error")
                    st.error(
                        f"No tournament named “{tournament_name}” found. Check the "
                        "exact Leaguepedia spelling (case-sensitive)."
                    )
                    return
            status.update(label=f"Loaded “{tournament_name}”", state="complete")
        st.success(f"Done — games: {counts.get('Games', 0)}, "
                   f"players: {counts.get('Players', 0)}.")
        cached.clear()  # new data should show in the other tabs
        st.rerun()
    except Exception as exc:  # surfaced in the UI instead of crashing the app
        st.error(f"Ingest failed: {exc}")
        st.caption("Leaguepedia may be rate-limiting; the client retries with "
                   "backoff — you can also just try again in a moment.")


with tab_add:
    st.subheader("Ingest a tournament from Leaguepedia")
    cat = load_catalog()

    # Build / refresh the autocomplete catalog from the API.
    with st.expander("🔄 Tournament list (autocomplete source)",
                     expanded=cat.empty):
        st.caption(f"{len(cat):,} tournaments cached." if not cat.empty
                   else "Not built yet — fetch it once to enable search.")
        st.caption("Fetching the full list can take a few minutes "
                   "(Leaguepedia rate-limits large pulls). It's stored, so this "
                   "is rarely needed.")
        if st.button("Refresh list from Leaguepedia"):
            with st.spinner("Fetching every tournament from Leaguepedia… (a few minutes)"):
                n = catalog.refresh_catalog(
                    LeaguepediaClient(LEAGUEPEDIA.username, LEAGUEPEDIA.password),
                    engine(),
                )
            load_catalog.clear()
            st.success(f"Catalog refreshed: {n:,} tournaments.")
            st.rerun()

    if cat.empty:
        st.info("Build the tournament list above to get searchable autocomplete, "
                "or use “Type the name manually” below.")
    else:
        # Region / year filters keep the searchable dropdown small and fast.
        c1, c2 = st.columns(2)
        regions = ["All"] + sorted(r for r in cat["region"].dropna().unique() if r)
        region = c1.selectbox("Region", regions)
        years = ["All"] + sorted((str(y) for y in cat["year"].dropna().unique() if str(y)),
                                 reverse=True)
        year = c2.selectbox("Year", years)

        view = cat
        if region != "All":
            view = view[view["region"] == region]
        if year != "All":
            view = view[view["year"].astype(str) == year]

        choice = st.selectbox(
            f"Tournament  ({len(view):,} match the filters — type to search)",
            options=view["name"].tolist(),
            index=None,
            placeholder="Start typing a tournament name…",
        )
        if st.button("Fetch & load", type="primary", disabled=not choice):
            run_ingest(choice)

    with st.expander("Type the name manually (for very new tournaments)"):
        manual = st.text_input("Exact Leaguepedia name",
                               placeholder="e.g. MSI 2026", key="manual_name")
        if st.button("Fetch & load", key="manual_go", disabled=not manual.strip()):
            run_ingest(manual.strip())
