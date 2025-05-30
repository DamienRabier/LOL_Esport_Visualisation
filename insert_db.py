from mwrogue.esports_client import EsportsClient
import pandas as pd

def get_scoreboard_games():
    site = EsportsClient("lol")
    response = site.cargo_client.query(
        tables="ScoreboardGames=SG",
        fields="SG.OverviewPage, SG.Tournament, SG.Team1, SG.Team2, SG.WinTeam, SG.LossTeam, " +
        "SG.DateTime_UTC, SG.DST, SG.Team1Score, SG.Team2Score, " +
        "SG.Winner, SG.Gamelength, SG.Gamelength_Number, " +
        "SG.Team1Bans, SG.Team2Bans, " +
        "SG.Team1Picks, SG.Team2Picks, " +
        "SG.Team1Players, SG.Team2Players, " +
        "SG.Team1Dragons, SG.Team2Dragons, " +
        "SG.Team1Barons, SG.Team2Barons, " +
        "SG.Team1Towers, SG.Team2Towers, " +
        "SG.Team1Gold, SG.Team2Gold, " +
        "SG.Team1Kills, SG.Team2Kills, " +
        "SG.Team1RiftHeralds, SG.Team2RiftHeralds, " +
        "SG.Team1VoidGrubs, SG.Team2VoidGrubs, " +
        "SG.Team1Atakhans, SG.Team2Atakhans, " +
        "SG.Team1Inhibitors, SG.Team2Inhibitors, " +
        "SG.Patch, SG.LegacyPatch, SG.PatchSort," +
        "SG.MatchHistory, " +
        "SG.VOD, " +
        "SG.N_Page, " +
        "SG.N_MatchInTab, " +
        "SG.N_MatchInPage, " +
        "SG.N_GameInMatch, " +
        "SG.Gamename, " +
        "SG.UniqueLine, " +
        "SG.GameId, " +
        "SG.MatchId, " +
        "SG.RiotPlatformGameId, " +
        "SG.RiotPlatformId, " +
        "SG.RiotGameId, " +
        "SG.RiotHash, " +
        "SG.RiotVersion",
    )
    return pd.DataFrame(response)

def get_scoreboard_players():
    site = EsportsClient("lol")
    response1 = site.cargo_client.query(
        tables="ScoreboardGames=SG, ScoreboardPlayers=SP, Tournaments=T",
        join_on="SG.GameId=SP.GameId, SG.OverviewPage=T.OverviewPage",
        fields = "SP.OverviewPage, SP.Name, SP.Link, SP.Champion, " +
        "SP.Kills, SP.Deaths, SP.Assists, SP.SummonerSpells, " +
        "SP.Gold, SP.CS, SP.DamageToChampions, SP.VisionScore, " +
        "SP.Items, SP.Trinket, SP.KeystoneMastery, SP.KeystoneRune, " +
        "SP.PrimaryTree, SP.SecondaryTree, SP.Runes, " +
        "SP.TeamKills, SP.TeamGold, " +
        "SP.Team, SP.TeamVs, SP.Time, SP.PlayerWin, " +
        "SP.DateTime_UTC, SP.DST, SP.Tournament, " +
        "SP.Role, SP.Role_Number, SP.IngameRole, SP.Side, " +
        "SP.UniqueLine, SP.UniqueLineVs, SP.UniqueRole, SP.UniqueRoleVs, " +
        "SP.GameId, SP.MatchId, SP.GameTeamId, " +
        "SP.GameRoleId, SP.GameRoleIdVs, SP.StatsPage",
        where="T.Name = 'LEC 2025 Spring'"
    )
    df1 = pd.DataFrame(response1)

    response2 = site.cargo_client.query(
        tables="ScoreboardGames=SG, ScoreboardPlayers=SP, Tournaments=T",
        join_on="SG.GameId=SP.GameId, SG.OverviewPage=T.OverviewPage",
        fields = "SP.OverviewPage, SP.Name, SP.Link, SP.Champion, " +
        "SP.Kills, SP.Deaths, SP.Assists, SP.SummonerSpells, " +
        "SP.Gold, SP.CS, SP.DamageToChampions, SP.VisionScore, " +
        "SP.Items, SP.Trinket, SP.KeystoneMastery, SP.KeystoneRune, " +
        "SP.PrimaryTree, SP.SecondaryTree, SP.Runes, " +
        "SP.TeamKills, SP.TeamGold, " +
        "SP.Team, SP.TeamVs, SP.Time, SP.PlayerWin, " +
        "SP.DateTime_UTC, SP.DST, SP.Tournament, " +
        "SP.Role, SP.Role_Number, SP.IngameRole, SP.Side, " +
        "SP.UniqueLine, SP.UniqueLineVs, SP.UniqueRole, SP.UniqueRoleVs, " +
        "SP.GameId, SP.MatchId, SP.GameTeamId, " +
        "SP.GameRoleId, SP.GameRoleIdVs, SP.StatsPage",
        where="T.Name = 'LEC 2025 Spring Playoffs'"
    )
    df2 = pd.DataFrame(response2)

    # ajoute les lignes de df2 à df1
    df = pd.concat([df1, df2], ignore_index=True)
    return df

def get_players_images():
    site = EsportsClient("lol")
    response = site.cargo_client.query(
        tables="PlayerImages=PI",
        fields="PI.FileName, PI.Link, PI.Team, PI.Tournament, ImageType, PI.Caption, PI.IsProfileImage, PI.SortDate"
    )
    return pd.DataFrame(response)

df_sg = get_scoreboard_games()
df_sp = get_scoreboard_players()
df_pi = get_players_images()