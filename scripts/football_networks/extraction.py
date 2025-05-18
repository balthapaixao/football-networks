import warnings
import numpy as np
import pandas as pd

from statsbombpy import sb

pd.set_option("display.max_columns", None)
pd.set_option("display.max_rows", None)
warnings.simplefilter("ignore")


def get_players(match_id: int) -> pd.DataFrame:
    """
    Get the players numbers for a given match

    Parameters
    ----------
    match_id : int
        The match id

    Returns
    -------
    df_players : pd.DataFrame
        A dataframe with the players numbers

    Examples
    --------
    >>> df_players = get_players(match_id=227489)
    >>> df_players.head()

    """
    lineups = sb.lineups(match_id=match_id)
    teams = list(lineups.keys())

    list_players_dfs = []
    list_positions = []
    for team in teams:
        list_players_dfs.append(pd.DataFrame(lineups[team]))
        list_positions.extend(
            pd.json_normalize(pd.json_normalize(lineups[team]["positions"])[0])[
                "position"
            ]
        )

    df_players = pd.concat(list_players_dfs).reset_index(drop=True)
    df_players["position"] = pd.Series(list_positions)

    df_players = df_players[["player_id", "player_name", "jersey_number", "position"]]

    return df_players


def get_match(match_id: int) -> pd.DataFrame:
    """
    Get the match events for a given match

    Parameters
    ----------
    match_id : int
        The match id

    Returns
    -------
    df_match : pd.DataFrame
        A dataframe with the match events

    Examples
    --------
    >>> df_match = get_match(match_id=227489)
    >>> df_match.head()

    """
    df_match = sb.events(match_id=match_id)

    return df_match


def get_starting_XI(df_match: pd.DataFrame) -> pd.DataFrame:
    """
    Get the starting XI for a given match

    Parameters
    ----------
    df_match : pd.DataFrame
        A dataframe with the match events

    Returns
    -------
    df_starting_xi : pd.DataFrame
        A dataframe with the starting XI

    Examples
    --------
    >>> df_match = get_match(match_id=227489)
    >>> df_starting_xi = get_starting_XI(df_match=df_match)
    >>> df_starting_xi.head()
    """
    starting_xi = df_match.loc[df_match["type"] == "Starting XI", "tactics"]

    jersey_numbers = pd.DataFrame(
        pd.json_normalize(starting_xi)["lineup"].explode().to_list()
    )["jersey_number"]
    df_starting_xi = pd.json_normalize(
        pd.DataFrame(pd.json_normalize(starting_xi)["lineup"].explode().to_list())[
            "player"
        ]
    )
    df_starting_xi["jersey_number"] = jersey_numbers.to_list()

    # add team
    df_starting_xi = df_starting_xi.merge(
        df_match[["player_id", "team"]].drop_duplicates(),
        left_on="id",
        right_on="player_id",
        how="left",
    ).drop(columns=["player_id"])

    home = df_starting_xi["team"][0]
    df_starting_xi["home"] = df_starting_xi["team"].apply(
        lambda x: True if x == home else False
    )

    return df_starting_xi


class Player:
    """
    A class used to represent a player

    Attributes
    ----------
    id : int
        The player id
    name : str
        The player name
    x : float
        The average x position
    y : float
        The average y position
    n_passes_completed : int
        The number of passes completed

    Methods
    -------
    average_position(df)
        Get the average position of the player

    Examples
    --------
    >>> df_match = get_match(match_id=227489)
    >>> df_starting_xi = get_starting_XI(df_match=df_match)
    >>> player = Player(player=df_starting_xi.iloc[0], df=df_match)
    >>> player.x, player.y, player.n_passes_completed
    (50.0, 50.0, 0)
    """

    def __init__(self, player: pd.DataFrame, df: pd.DataFrame) -> None:
        """
        Parameters
        ----------
        player : pd.Series
            The player
        df : pd.DataFrame
            A dataframe with the match events
        """
        self.id = player["id"]
        self.name = player["name"]
        self.average_position(df)

    def average_position(self, df: pd.DataFrame) -> None:
        """
        Get the average position of the player

        Parameters
        ----------
        df : pd.DataFrame
            A dataframe with the match events
        """

        player_pass_df = df.query(
            "(type == 'Pass') & (pass_type not in ['Free Kick', 'Corner', 'Throw-in', 'Kick Off']) & \
             (player_id == @self.id) & \
             (pass_outcome not in ['Unknown','Out','Pass Offside','Injury Clearance', 'Incomplete'])"
        )

        try:
            self.x, self.y = np.mean(player_pass_df["location"].tolist(), axis=0)
        except TypeError:
            print(self.id, self.name)
            self.x, self.y = 50, 50

        def minutes_played(self, df: pd.DataFrame) -> None:
            """
            Get the minutes played by the player

            Parameters
            ----------
            df : pd.DataFrame
                A dataframe with the match events
            """
            player_pass_df = df.query(
                "(type == 'Pass') & (pass_type not in ['Free Kick', 'Corner', 'Throw-in', 'Kick Off']) & \
                 (player_id == @self.id) & \
                 (pass_outcome not in ['Unknown','Out','Pass Offside','Injury Clearance', 'Incomplete'])"
            )

        self.n_passes_completed = len(player_pass_df)


def get_starters_list(df_match: pd.DataFrame, df_starting_xi: pd.DataFrame) -> list:
    """
    Get starters list

    Parameters
    ----------
    df_starting_xi : pd.DataFrame
        Starting XI dataframe

    Returns
    -------
    list
        Starters list
    """
    player_objs_dict = {}
    starters = []

    for player in df_starting_xi.to_dict(orient="records"):
        player_obj = Player(player, df_match)
        starters.append(player_obj.name)
        player_objs_dict[player["id"]] = player_obj

    return starters, player_objs_dict


def prepare_passes_df(
    df_match: pd.DataFrame, df_starting_xi: pd.DataFrame
) -> pd.DataFrame:
    """
    Prepare passes dataframe

    Parameters
    ----------
    df_match : pd.DataFrame
        Match dataframe
    df_starting_xi : pd.DataFrame
        Starting XI dataframe

    Returns
    -------
    pd.DataFrame
        Passes dataframe
    """
    starters, player_objs_dict = get_starters_list(df_match, df_starting_xi)
    select_cols = ["player", "pass_recipient", "location", "pass_end_location"]
    df_passes = df_match.loc[
        (
            (df_match["type"] == "Pass")
            & ~(
                df_match["pass_outcome"].isin(
                    ["Unknown", "Out", "Pass Offside", "Injury Clearance", "Incomplete"]
                )
            )
        ),
        select_cols,
    ]

    df_passes = (
        df_passes.groupby(["player", "pass_recipient"]).size().reset_index(name="count")
    )

    df_passes = df_passes.query("player in @starters & pass_recipient in @starters")

    df_passes = df_passes.merge(df_starting_xi, left_on="player", right_on="name").drop(
        columns=["name"]
    )

    df_passes = df_passes.merge(
        df_starting_xi, left_on="pass_recipient", right_on="name"
    ).drop(columns=["name"])

    df_passes.columns = [
        "passer",
        "recipient",
        "passes",
        "passer_id",
        "passer_jersey_number",
        "passer_team",
        "home",
        "recipient_id",
        "recipient_jersey_number",
        "recipient_team",
        "away",
    ]
    df_passes = df_passes[
        [
            "passer",
            "passer_id",
            "passer_jersey_number",
            "passer_team",
            "recipient",
            "recipient_id",
            "recipient_jersey_number",
            "recipient_team",
            "passes",
            "home",
        ]
    ]

    df_passes = df_passes.sort_values(by="passes", ascending=False)

    return df_passes
