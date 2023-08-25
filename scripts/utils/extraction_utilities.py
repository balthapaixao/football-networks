import pandas as pd
from mplsoccer import Sbopen


def parse_event(match_id: int) -> pd.DataFrame:
    """
    Extract match data
    """
    sb = Sbopen()
    events, related, freeze, players = sb.event(match_id)

    return events, related, freeze, players


def parse_360(match_id: int) -> pd.DataFrame:
    """
    Extract match data
    """
    sb = Sbopen()
    frames, visible = sb.frame(match_id)

    return frames, visible


def extract_data() -> pd.DataFrame:
    """
    Extract data
    """
    df = ...
    return df
