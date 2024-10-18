import json
from typing import Any, Dict, List
import os

import polars as pl
from polars.exceptions import ComputeError

from pydantic import BaseModel

LOCAL_DIR_PREFIX = "data/raw"

# (game-changers, vct-international, vct-challengers)
LEAGUE = "game-changers"

class GameMapping(BaseModel):
    platform_game_id: str  # e.g. "val:13d729bb-073f-4a26-ab3a-d36fec4ff421"
    esports_game_id: int  # e.g. 111890538382884654
    tournament_id: int  # e.g. 111890485752679867
    team_mapping: Dict[int, int]  # e.g. 17: 105720640249797517
    participant_mapping: Dict[int, int]  # e.g. 1: 111901586897234547


class GameEvent(BaseModel):
    seq_num: int  # sequence number
    metadata: Dict[Any, Any]  # event metadata
    name: str  # event name (e.g. "damageEvent")
    payload: Dict[Any, Any]  # event payload (e.g. victimId, damage, etc.)



def get_game_mappings(mapping_file: str) -> List[GameMapping]:
    """
    Reads game mappings from a JSON file and returns a list of GameMapping objects.

    Parameters:
    mapping_file (str): Path to the JSON file containing game mappings.

    Returns:
    List[GameMapping]: A list of GameMapping objects.
    """
    with open(mapping_file, "r") as mf:
        maps = json.load(mf)
    
    game_mappings = []
    for m in maps:
        try:
            game_mapping = GameMapping(
                platform_game_id=m["platformGameId"],
                esports_game_id=int(m["esportsGameId"]),
                tournament_id=int(m["tournamentId"]),
                team_mapping={int(k): int(v) for k, v in m["teamMapping"].items()},
                participant_mapping={int(k): int(v) for k, v in m["participantMapping"].items()},
            )
            game_mappings.append(game_mapping)
        except ValueError as e:
            print(f"Invalid mapping record: {m}\n{e}\nSkipping...")
    
    return game_mappings



"""
EVENT TYPES
[
  "abilityUsed",
  "configuration",
  "damageEvent",
  "gameDecided",
  "gamePhase",
  "inventoryTransaction",
  "metadata",
  "observerTarget",
  "platformGameId",
  "playerDied",
  "playerSpawn",
  "roundCeremony",
  "roundDecided",
  "roundEnded",
  "roundStarted",
  "snapshot",
  "spikeDefuseCheckpointReached",
  "spikeDefuseStarted",
  "spikeDefuseStopped",
  "spikePlantCompleted",
  "spikePlantStarted",
  "spikePlantStopped",
  "spikeStatus"
]
"""


def get_game_events(game_file: str) -> List[GameEvent]:
    """
    Reads game events from a JSON file and returns a list of GameEvent objects.

    Parameters:
    game_file (str): The path to the JSON file containing game events.

    Returns:
    List[GameEvent]: A list of GameEvent objects.
    """

    ignore_events = {
        "snapshot", "observerTarget","spikePlantStopped","spikePlantStarted", "playerSpawn",
  "roundCeremony", "gamePhase", 
    }

    with open(game_file, "r") as gf:
        game_data = json.load(gf)
    
    game_events = []
    for e in game_data:
        event_name = next(x for x in e if x not in {"metadata", "platformGameId"})
        
        if event_name not in ignore_events:
            game_events.append(
                GameEvent(
                    seq_num=e["metadata"]["sequenceNumber"],
                    metadata=e["metadata"],
                    name=event_name,
                    payload=e[event_name],
                )
            )
    return game_events


def get_game_stats(events: List[GameEvent], mapping: GameMapping) -> pl.DataFrame:
    # mapping data
    tournament_id, game_id = mapping.tournament_id, mapping.esports_game_id
    # temp dict for rounds configuration
    rounds_config = {"round_num": [], "team_id": [], "team_mode": [], "player_id": []}
    # temp dict for damage events
    damage_stats = {
        "tournament_id": [],
        "esports_game_id": [],
        "player_id": [],
        "round_num": [],
        "damage_dealt": [],
        "damage_taken": [],
        "players_killed": [],
        "assists": [],
        "head_shots":[],
        # Add ablility used
    }

    for e in events:
        match e.name:
            case "configuration":
                round_num = e.payload["spikeMode"]["currentRound"]
                if round_num not in rounds_config["round_num"]:
                    # add configuration event once per round
                    attacking_team = e.payload["spikeMode"]["attackingTeam"]["value"]
                    for team in e.payload["teams"]:
                        team_num = team["teamId"]["value"]
                        team_mode = "A" if team_num == attacking_team else "D"
                        team_players = [player["value"] for player in team["playersInTeam"]]
                        for player in team_players:
                            rounds_config["round_num"].append(round_num)
                            rounds_config["team_id"].append(int(mapping.team_mapping[team_num]))
                            rounds_config["team_mode"].append(team_mode)
                            rounds_config["player_id"].append(int(mapping.participant_mapping[player]))
            case "damageEvent":
                round_num = e.metadata["currentGamePhase"]["roundNumber"]
                causer = e.payload.get("causerId", {}).get("value", 0)  #Sometimes players get fall damage or something else
                victim = e.payload["victimId"]["value"]
                damage = round(e.payload["damageDealt"])
                is_killed = 1 if e.payload["killEvent"] else 0
                is_head = 1 if e.payload["location"]=="HEAD" else 0 
                # add causer
                try :
                    damage_stats["tournament_id"].append(tournament_id)
                    damage_stats["esports_game_id"].append(game_id)
                    damage_stats["round_num"].append(round_num)
                    damage_stats["damage_dealt"].append(damage)
                    damage_stats["damage_taken"].append(0)
                    damage_stats["players_killed"].append(is_killed)
                    damage_stats["assists"].append(0)
                    damage_stats["head_shots"].append(is_head)
                    damage_stats["player_id"].append(int(mapping.participant_mapping[causer]))
                except Exception as e:
                    if KeyError:
                        damage_stats["player_id"].append(causer)
                        print("Unkown Damage Event")
                    
                # then victim
                damage_stats["tournament_id"].append(tournament_id)
                damage_stats["esports_game_id"].append(game_id)
                damage_stats["round_num"].append(round_num)
                damage_stats["player_id"].append(int(mapping.participant_mapping[victim]))
                damage_stats["damage_dealt"].append(0)
                damage_stats["damage_taken"].append(damage)
                damage_stats["players_killed"].append(0)
                damage_stats["assists"].append(0)
                damage_stats["head_shots"].append(0)


            #assits
            case "playerDied":
                assistants = e.payload["assistants"]
                for a in assistants:
                    assistant_id = a["assistantId"]["value"]
                    damage_stats["tournament_id"].append(tournament_id)
                    damage_stats["esports_game_id"].append(game_id)
                    damage_stats["round_num"].append(round_num)
                    damage_stats["player_id"].append(int(mapping.participant_mapping[assistant_id]))
                    damage_stats["damage_dealt"].append(0)
                    damage_stats["damage_taken"].append(damage)
                    damage_stats["players_killed"].append(0)
                    damage_stats["assists"].append(1)
                    damage_stats["head_shots"].append(0)

    rounds_df = pl.DataFrame(data=rounds_config, schema_overrides={"team_id": pl.UInt64, "player_id": pl.UInt64})
            
    tournaments = get_tournaments(f"{LOCAL_DIR_PREFIX}/{LEAGUE}")#Get tournaments Names

    teams = get_teams(f"{LOCAL_DIR_PREFIX}/{LEAGUE}") #Get Team Names

    players = get_players(f"{LOCAL_DIR_PREFIX}/{LEAGUE}") #Get player names


    damage_df = pl.DataFrame(
        data=damage_stats,
        schema_overrides={"tournament_id": pl.UInt64, "esports_game_id": pl.UInt64, "player_id": pl.UInt64},
    )

    
    try:

        res = rounds_df.join(damage_df, on=["round_num", "player_id"], how="inner")
        
        # Calculate damage per round
        average_damage_per_round = get_average_dpr(res)

        res = res.join(average_damage_per_round, on=["player_id","tournament_id","esports_game_id","team_mode"], how="inner")\
            .join(tournaments, on=["tournament_id"], how="left")\
            .join(teams, on=["team_id"], how="left")\
            .join(players,on=["player_id"],how="left")
    except ComputeError as ce:
        print(rounds_df)
        print(damage_df)
        # raise ValueError("Bad game data. Could not join dataframes.") from ce
        return
    return res

def process_game_file(games_folder: str, mapping: GameMapping) -> pl.DataFrame:
    platform_game_id = mapping.platform_game_id.replace(":", "_")
    game_file = f"{games_folder}/{platform_game_id}.json"

    if not os.path.exists(game_file):
        print(f" No such file or directory: {game_file}")
        exit()

    print(f"{game_file}")
    events = get_game_events(game_file)
    game_stats = get_game_stats(events, mapping)
    
    if game_stats is None:
        return


    q = (
        game_stats.lazy()
        .group_by("player_name", "team_mode","average_drp","damage_std_dev")
        .agg([
            pl.sum("damage_dealt"),
            pl.sum("damage_taken"),
            pl.sum("players_killed"),
            pl.sum("assists"),
            pl.sum("head_shots"),
        ])
        .sort(["damage_dealt"])
    )
    game_summary = q.collect()
    print(
        f"Extracted events: {len(events)}, game stats rows: {len(game_stats)}, game summary rows: {len(game_summary)}"
    )
    if len(game_summary) == 0:
        print(game_summary)
        # raise ValueError(f"Bad game data. Expected summary len = 20, but got {len(game_summary)}")

    return game_summary

def get_average_dpr(damage_df: pl.DataFrame) -> pl.DataFrame:
    damage_per_round_individual = (
        damage_df.lazy()
        .group_by(["tournament_id", "esports_game_id", "round_num", "player_id", "team_mode"])
        .agg(pl.sum("damage_dealt").alias("damage_per_round"))
        .collect()
    )

    average_damage_per_round = (
        damage_per_round_individual.lazy()
        .group_by(["tournament_id", "esports_game_id", "player_id", "team_mode"])
        .agg(
            pl.mean("damage_per_round").round().cast(pl.Int32).alias("average_drp"),
            pl.std("damage_per_round").round().cast(pl.Float32).alias("damage_std_dev")  # Standard deviation
        )
        .collect()
    )

    return average_damage_per_round

def get_tournaments(data_dir: str) -> pl.DataFrame:#
    # Read JSON file containing tournament data into a Polars DataFrame
    tournaments = pl.read_json(f"{data_dir}/esports-data/tournaments.json")
    
    # Select and rename relevant columns, casting types as necessary
    tournaments = tournaments.select(
        pl.col("id").cast(pl.UInt64).alias("tournament_id"),  # Cast 'id' to UInt64 and rename to 'tournament_id'
        pl.col("league_id").cast(pl.UInt64),  # Cast 'league_id' to UInt64
        pl.col("name").alias("tournament_name"),  # Rename 'name' to 'tournament_name'
        # pl.col("status").alias("tournament_status"),  # Commented out column
        # pl.col("time_zone").alias("tournament_tz"),  # Commented out column
    )
    
    return tournaments

def get_teams(data_dir: str)->pl.DataFrame:
    teams = pl.read_json(f"{data_dir}/esports-data/teams.json")
    teams = (
        teams.select(
            pl.col("id").cast(pl.UInt64).alias("team_id"),
            pl.col("home_league_id").cast(pl.UInt64).alias("league_id"),
            pl.col("name").alias("team_name"),
        )
        .group_by(["league_id", "team_id"])
        .agg(pl.col("team_name").first())
    )
    return teams

def get_leagues(data_dir: str)->pl.DataFrame:
    leagues = pl.read_json(f"{data_dir}/esports-data/leagues.json")
    leagues = leagues.select(
        pl.col("league_id").cast(pl.UInt64),
        pl.col("name").alias("league_name"),
        pl.col("region").alias("league_region"),
    )    
    return leagues

def get_players(data_dir: str)->pl.DataFrame:
    players = pl.read_json(f"{data_dir}/esports-data/players.json")
    players = (
        players.select(
            pl.col("id").cast(pl.UInt64).alias("player_id"),
            pl.col("home_team_id").cast(pl.UInt64).alias("team_id"),
            pl.col("handle").alias("player_handle"),
            (pl.col("first_name") + " " + pl.col("last_name")).alias("player_name"),
            pl.when(pl.col("status") == "active").then(pl.lit(True)).otherwise(pl.lit(False)).alias("player_is_active"),
            # pl.col("created_at").str.to_datetime().alias("player_created"),
            # pl.col("updated_at").str.to_datetime().alias("player_updated"),
        )
        .group_by(["player_id", "team_id", "player_handle", "player_name", "player_is_active"])
        .agg(pl.all())
    )
    return players

def get_fixture_data(data_dir: str) -> pl.DataFrame:
    """
    This function reads json file and joins the tables accordingly.
    
    Parameters:
    data_dir (str): path to data/raw/league
    
    Returns:
    pl.DataFrame: Tables joined togther
    """

    # leagues
    leagues = get_leagues(data_dir)
    # tournaments
    tournaments = get_tournaments(data_dir)

    # teams
    teams = get_teams(data_dir)

    # players
    players = get_players(data_dir)

    fixture_data = (
        leagues.join(tournaments, on="league_id", how="inner")
        .join(teams, on="league_id", how="inner")
        .join(players, on="team_id", how="inner")
    )
    return fixture_data


def process_games(data_dir: str) -> pl.DataFrame:
    """
    This function reads events type and creates a statstical measure for performance
    
    Parameters:
    data_dir (str): path to data/raw/league
    
    Returns:
    pl.DataFrame: Tables joined togther
    """


    # leagues
    leagues = pl.read_json(f"{data_dir}/esports-data/leagues.json")
    leagues = leagues.select(
        pl.col("league_id").cast(pl.UInt64),
        pl.col("name").alias("league_name"),
        pl.col("region").alias("league_region"),
    )
    # tournaments
    tournaments = pl.read_json(f"{data_dir}/esports-data/tournaments.json")
    tournaments = tournaments.select(
        pl.col("id").cast(pl.UInt64).alias("tournament_id"),
        pl.col("league_id").cast(pl.UInt64),
        pl.col("name").alias("tournament_name"),
        # pl.col("status").alias("tournament_status"),
        # pl.col("time_zone").alias("tournament_tz"),
    )
    # teams
    teams = pl.read_json(f"{data_dir}/esports-data/teams.json")
    teams = (
        teams.select(
            pl.col("id").cast(pl.UInt64).alias("team_id"),
            pl.col("home_league_id").cast(pl.UInt64).alias("league_id"),
            pl.col("name").alias("team_name"),
        )
        .group_by(["league_id", "team_id"])
        .agg(pl.col("team_name").first())
    )
    # players
    players = pl.read_json(f"{data_dir}/esports-data/players.json")
    players = (
        players.select(
            pl.col("id").cast(pl.UInt64).alias("player_id"),
            pl.col("home_team_id").cast(pl.UInt64).alias("team_id"),
            pl.col("handle").alias("player_handle"),
            (pl.col("first_name") + " " + pl.col("last_name")).alias("player_name"),
            pl.when(pl.col("status") == "active").then(pl.lit(True)).otherwise(pl.lit(False)).alias("player_is_active"),
            # pl.col("created_at").str.to_datetime().alias("player_created"),
            # pl.col("updated_at").str.to_datetime().alias("player_updated"),
        )
        .group_by(["player_id", "team_id", "player_handle", "player_name", "player_is_active"])
        .agg(pl.all())
    )
    fixture_data = (
        leagues.join(tournaments, on="league_id", how="left")
        .join(teams, on="league_id", how="inner")
        .join(players, on="team_id", how="inner")
    )
    return fixture_data