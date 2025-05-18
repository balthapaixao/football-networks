from . import processing as process
# import load as load

from statsbombpy import sb
import pandas as pd
import warnings
import os
import json

from multiprocessing import Pool

warnings.simplefilter("ignore")

# read the championship ids

def read_json(file_path: str) -> dict:
    with open(file_path, "r") as file:
        data = json.load(file)
    return data

def etl(championship_dict: dict):
    # championship_ids = read_json(championships)
    # championship_id = championship_ids[championship]
    championship_id = championship_dict["competition_id"]
    championship_name = championship_dict["competition_name"]
    season_id = championship_dict["season_id"]

    df_matches_league = sb.matches(
        competition_id=championship_id, season_id=season_id
    ).sort_values(["match_date"], ascending=True)
    match_ids = df_matches_league["match_id"].to_list()

    cnt = 1
    list_season_metrics = []
    for match_id in match_ids:
        df_metrics = process.process_match(
            match_id=match_id,
            df_matches=df_matches_league,
        )
        list_season_metrics.append(df_metrics)

        print(f"{cnt} of {len(match_ids)}", end="\r")

        cnt += 1
    df_metrics = pd.concat(list_season_metrics)

    print(f"Current directory: {os.getcwd()}")

    try:
        file_name = f"../../data/processed/{championship_name}_15_16.csv"
        df_metrics.to_csv(file_name, index=False)
    except:
        current_dir = os.getcwd()
        file_name = f"{current_dir}/data/processed/{championship_name}_15_16.csv"
        df_metrics.to_csv(file_name, index=False)

    # load.load_postgres(file_path=file_name)


# def main():
#     championship_ids = ...
#     championships = list(championship_ids.keys())
#     for championship in championships:
#         print(f"Processing {championship}")
#         etl(championship=championship)


# if __name__ == "__main__":
#     main()
