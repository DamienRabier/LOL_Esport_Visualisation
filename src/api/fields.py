"""Cargo field definitions, declared once and reused across queries.

Keeping these in one place avoids the copy-pasted field strings that made the
old queries hard to maintain. Each constant is the list of columns we request
for a given Cargo table; the client joins them with ", ".
"""

# ScoreboardGames: one row per game, team-level stats.
SCOREBOARD_GAMES = [
    "OverviewPage", "Tournament", "Team1", "Team2", "WinTeam", "LossTeam",
    "DateTime_UTC", "DST", "Team1Score", "Team2Score", "Winner",
    "Gamelength", "Gamelength_Number",
    "Team1Bans", "Team2Bans", "Team1Picks", "Team2Picks",
    "Team1Players", "Team2Players",
    "Team1Dragons", "Team2Dragons", "Team1Barons", "Team2Barons",
    "Team1Towers", "Team2Towers", "Team1Gold", "Team2Gold",
    "Team1Kills", "Team2Kills", "Team1RiftHeralds", "Team2RiftHeralds",
    "Team1VoidGrubs", "Team2VoidGrubs", "Team1Atakhans", "Team2Atakhans",
    "Team1Inhibitors", "Team2Inhibitors",
    "Patch", "LegacyPatch", "PatchSort", "MatchHistory", "VOD",
    "N_Page", "N_MatchInTab", "N_MatchInPage", "N_GameInMatch",
    "Gamename", "UniqueLine", "GameId", "MatchId",
    "RiotPlatformGameId", "RiotPlatformId", "RiotGameId", "RiotHash", "RiotVersion",
]

# ScoreboardPlayers: one row per player per game.
SCOREBOARD_PLAYERS = [
    "OverviewPage", "Name", "Link", "Champion",
    "Kills", "Deaths", "Assists", "SummonerSpells",
    "Gold", "CS", "DamageToChampions", "VisionScore",
    "Items", "Trinket", "KeystoneMastery", "KeystoneRune",
    "PrimaryTree", "SecondaryTree", "Runes",
    "TeamKills", "TeamGold", "Team", "TeamVs", "Time", "PlayerWin",
    "DateTime_UTC", "DST", "Tournament",
    "Role", "Role_Number", "IngameRole", "Side",
    "UniqueLine", "UniqueLineVs", "UniqueRole", "UniqueRoleVs",
    "GameId", "MatchId", "GameTeamId", "GameRoleId", "GameRoleIdVs", "StatsPage",
]

TOURNAMENTS = [
    "Name", "OverviewPage", "DateStart", "Date", "DateStartFuzzy",
    "League", "Region", "Prizepool", "Currency", "Country", "ClosestTimezone",
    "Rulebook", "EventType", "Links", "Sponsors", "Organizer", "Organizers",
    "StandardName", "StandardName_Redirect", "BasePage",
    "Split", "SplitNumber", "SplitMainPage", "TournamentLevel",
    "IsQualifier", "IsPlayoffs", "IsOfficial", "Year",
    "LeagueIconKey", "AlternativeNames", "ScrapeLink", "Tags", "SuppressTopSchedule",
]

LEAGUES = ["League", "League_Short", "Region", "Level", "IsOfficial"]

CURRENT_LEAGUES = ["Event", "OverviewPage", "Priority"]

TOURNAMENT_PLAYERS = [
    "ID", "Player", "Team", "TeamLast", "Role", "Role_Number",
    "Country", "Residency", "OverviewPage", "Tournament", "IsSubstitute", "IsLowercase",
]

# Columns that Cargo returns as comma-joined lists and that map to TEXT[] in
# Postgres. The client splits these into Python lists on the way out.
LIST_FIELDS = {
    "Team1Bans", "Team2Bans", "Team1Picks", "Team2Picks",
    "Team1Players", "Team2Players", "SummonerSpells", "Items",
    "AlternativeNames", "Tags",
}
