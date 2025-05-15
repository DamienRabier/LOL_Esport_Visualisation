from mwrogue.esports_client import EsportsClient
import datetime as dt

date = "2025-03-28"
split_start = dt.datetime.strptime(date, "%Y-%m-%d").date()

site = EsportsClient("lol")
response = site.cargo_client.query(
    tables="ScoreboardGames=SG, ScoreboardPlayers=SP, Tournaments=T",
    join_on="SG.GameId=SP.GameId, SG.OverviewPage=T.OverviewPage",
    fields="T.Name=Tournament, SG.DateTime_UTC, SG.Team1, SG.Team2, SG.Winner, SG.Patch, SP.Link, SP.Team, SP.Champion, SP.SummonerSpells, SP.KeystoneMastery, SP.KeystoneRune, SP.Role, SP.GameId, SP.Side",
    where="SG.DateTime_UTC >= '" + str(split_start) + " 00:00:00' AND SG.DateTime_UTC <= '" + str(split_start+dt.timedelta(1)) + " 00:00:00' AND T..League = 'LoL EMEA Championship'"
)

print(response)