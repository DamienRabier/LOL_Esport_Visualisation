"""LoL Esport debrief & scouting dashboard (Streamlit).

Run from the project root with the venv active:
    streamlit run app.py
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
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


WIN_GREEN = "#2ecc71"
LOSS_RED = "#e74c3c"
BAN_BLUE = "#3498db"


def rate_hbar(df: pd.DataFrame, y: str, total_col: str, pos_col: str, title: str,
              *, pos_name: str = "Wins", neg_name: str = "Losses",
              sort_col: str | None = None, show_neg: bool = True,
              pos_color: str = WIN_GREEN):
    """Stacked horizontal bar: green = positive share, red = the rest, per row.

    Each segment is labelled with its percentage. Used for both win rate
    (green = wins out of picks) and ban rate (green = games banned out of games).
    """
    if df.empty:
        st.info("No data.")
        return
    df = df.copy()
    df["_pos"] = df[pos_col].fillna(0).astype(int)
    df["_neg"] = (df[total_col].fillna(0).astype(int) - df["_pos"]).clip(lower=0)
    total = df[total_col].replace(0, pd.NA)
    df["_posrate"] = (100 * df["_pos"] / total).round(0)
    df["_negrate"] = (100 * df["_neg"] / total).round(0)

    # Percentage labels written on each segment (blank when the rate is 0).
    pos_txt = [f"{r:.0f}%" if pd.notna(r) and r > 0 else "" for r in df["_posrate"]]
    neg_txt = [f"{r:.0f}%" if pd.notna(r) and r > 0 else "" for r in df["_negrate"]]

    # Ascending on the chosen metric so the biggest bar sits on top.
    order = list(df[sort_col or total_col].argsort())
    df = df.iloc[order]
    pos_txt = [pos_txt[i] for i in order]
    neg_txt = [neg_txt[i] for i in order]

    fig = go.Figure()
    fig.add_bar(
        y=df[y], x=df["_pos"], orientation="h", name=pos_name, marker_color=pos_color,
        text=pos_txt, textposition="inside", insidetextanchor="middle",
        textfont=dict(color="white"), cliponaxis=False,
        hovertemplate="%{y}<br>" + pos_name + ": %{x} (%{text})<extra></extra>",
    )
    if show_neg:
        fig.add_bar(
            y=df[y], x=df["_neg"], orientation="h", name=neg_name, marker_color=LOSS_RED,
            text=neg_txt, textposition="inside", insidetextanchor="middle",
            textfont=dict(color="white"), cliponaxis=False,
            hovertemplate="%{y}<br>" + neg_name + ": %{x} (%{text})<extra></extra>",
        )
    fig.update_layout(
        barmode="stack", title=title, height=max(280, 26 * len(df)),
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        bargap=0.25,
    )
    st.plotly_chart(fig, width="stretch")


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


def render_add_data():
    st.subheader("Ingest a tournament from Leaguepedia")
    cat = load_catalog()

    # Build / refresh the autocomplete catalog from the API.
    with st.expander("🔄 Tournament list (autocomplete source)",
                     expanded=cat.empty):
        st.caption(f"{len(cat):,} tournaments cached." if not cat.empty
                   else "Not built yet — fetch it once to enable search.")

        from datetime import date
        from mwclient.errors import APIError
        cutoff = date.today().year - 2  # current year + the two before it

        def do_refresh(spinner_msg: str, **kwargs):
            """Refresh the catalog, turning rate-limit errors into a friendly note."""
            try:
                with st.spinner(spinner_msg):
                    n = catalog.refresh_catalog(
                        LeaguepediaClient(LEAGUEPEDIA.username, LEAGUEPEDIA.password),
                        engine(),
                        **kwargs,
                    )
            except APIError as exc:
                if getattr(exc, "code", None) == "ratelimited":
                    st.error("Leaguepedia is rate-limiting this IP. Wait ~15 minutes "
                             "and try again, or add bot credentials to `.env` for a "
                             "higher quota (see README).")
                else:
                    st.error(f"Catalog refresh failed: {exc}")
                return
            load_catalog.clear()
            st.success(f"Catalog built: {n:,} tournaments.")
            st.rerun()

        b1, b2 = st.columns(2)
        if b1.button(f"⚡ Load recent ({cutoff}–now)", type="primary"):
            do_refresh(f"Fetching tournaments since {cutoff}… (a few seconds)",
                       where=f"T.Year >= {cutoff}")
        b1.caption("Fast — one request. Covers everything from the last 3 years.")

        if b2.button("Refresh full history"):
            do_refresh("Fetching every tournament from Leaguepedia… (a few minutes)")
        b2.caption("Slow (minutes, rate-limited). Only for old tournaments.")

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


# ------------------------------------------------------------------ filters
st.sidebar.title("🎮 Filters")
try:
    tdf = cached("tournaments")
except Exception as exc:  # pragma: no cover - surfaced in UI
    st.error(f"Could not reach the database. Is PostgreSQL running and `.env` set?\n\n{exc}")
    st.stop()

# Empty DB: don't dead-end. Show only the "Add data" tab so the first
# tournament can be ingested straight from the UI.
if tdf.empty:
    st.title("LoL Esport — Debrief & Scouting")
    st.warning("No data yet. Ingest your first tournament below to unlock the "
               "Overview, Team, Player and Draft tabs.")
    render_add_data()
    st.stop()

# Show the friendly name, filter internally by overviewpage (the reliable key).
name_to_op = dict(zip(tdf["name"], tdf["overviewpage"]))
tournament = st.sidebar.selectbox("Tournament", list(name_to_op))
overview = name_to_op[tournament]
st.sidebar.caption("Filters apply across all tabs.")

# Sidebar button navigates to a dedicated "Add data" page (not embedded here).
st.session_state.setdefault("page", "dashboard")
st.sidebar.divider()
if st.sidebar.button("➕ Add data", width="stretch"):
    st.session_state.page = "add_data"
    st.rerun()

# Dedicated Add-data page.
if st.session_state.page == "add_data":
    if st.button("← Back to dashboard"):
        st.session_state.page = "dashboard"
        st.rerun()
    st.title("Add data")
    render_add_data()
    st.stop()

st.title("LoL Esport — Debrief & Scouting")
st.caption(f"Tournament: **{tournament}**")

tab_overview, tab_games, tab_team, tab_player, tab_draft = st.tabs(
    ["📊 Overview", "🎮 Games", "🛡️ Team scouting", "🧍 Player", "🚫 Draft"]
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
        rate_hbar(picks, y="champion", total_col="picks", pos_col="wins",
                  title="Most-picked champions (win/loss)")
    with col2:
        bans = cached("top_bans", overview).head(15)
        rate_hbar(bans, y="champion", total_col="games", pos_col="bans",
                  title="Most-banned champions (ban rate)",
                  pos_name="Banned", sort_col="bans", show_neg=False, pos_color=BAN_BLUE)


# -------------------------------------------------------------- game by game
with tab_games:
    gl = cached("games_list", overview)
    if gl.empty:
        st.info("No games for this tournament.")
    else:
        # One readable label per game for the selector.
        def game_label(r):
            d = pd.to_datetime(r["date"]).strftime("%Y-%m-%d") if pd.notna(r["date"]) else "?"
            s1 = "" if pd.isna(r["team1score"]) else int(r["team1score"])
            s2 = "" if pd.isna(r["team2score"]) else int(r["team2score"])
            return f"{d} — {r['team1']} {s1}–{s2} {r['team2']}"

        labels = {game_label(r): r["gameid"] for _, r in gl.iterrows()}
        pick = st.selectbox("Game", list(labels), key="game_select")
        gid = labels[pick]

        g = cached("game_detail", gid)
        players = cached("game_players", gid)

        # Header line: winner, length, patch.
        winner = (g.get("team1") if g.get("winner") == 1
                  else g.get("team2") if g.get("winner") == 2 else "—")
        h1, h2, h3 = st.columns(3)
        h1.metric("Winner", winner)
        h2.metric("Length", g.get("gamelength") or "—")
        h3.metric("Patch", g.get("patch") or "—")

        # Team-level objectives, side by side.
        st.subheader("Team stats")
        t1, t2 = st.columns(2)
        for col, side, label in ((t1, 1, g.get("team1")), (t2, 2, g.get("team2"))):
            p = "team1" if side == 1 else "team2"
            with col:
                st.markdown(f"**{label or ('Team ' + str(side))}**"
                            + ("  🏆" if g.get("winner") == side else ""))
                st.write({
                    "Kills": g.get(f"{p}kills"),
                    "Gold": g.get(f"{p}gold"),
                    "Towers": g.get(f"{p}towers"),
                    "Dragons": g.get(f"{p}dragons"),
                    "Barons": g.get(f"{p}barons"),
                    "Heralds": g.get(f"{p}riftheralds"),
                    "Grubs": g.get(f"{p}voidgrubs"),
                })
                bans = g.get(f"{p}bans")
                if isinstance(bans, (list, tuple)) and len(bans):
                    st.caption("Bans: " + ", ".join(bans))

        # Full per-player scoreboard.
        st.subheader("Player scoreboard")
        if players.empty:
            st.info("No player rows for this game.")
        else:
            st.dataframe(players.drop(columns=["side"], errors="ignore"),
                         width="stretch", hide_index=True)


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
            rate_hbar(pool.head(15), y="champion", total_col="games", pos_col="wins",
                      title="Champion pool (win/loss)")
        with col2:
            bans = cached("team_bans", team, overview)
            rate_hbar(bans.head(15), y="champion", total_col="games", pos_col="bans",
                      title="Bans by this team (ban rate)",
                      pos_name="Banned", sort_col="bans", show_neg=False, pos_color=BAN_BLUE)

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
            rate_hbar(champs.head(15), y="champion", total_col="games", pos_col="wins",
                      title="Champion pool (win/loss)")
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


