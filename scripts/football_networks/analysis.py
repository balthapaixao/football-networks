import db_utils as db
import os
from scipy.stats import spearmanr
import seaborn as sns
import matplotlib.pyplot as plt


def get_competition_positions():
    premier_league = {
        "Leicester City": 1,
        "Arsenal": 2,
        "Tottenham Hotspur": 3,
        "Manchester City": 4,
        "Manchester United": 5,
        "Southampton": 6,
        "West Ham United": 7,
        "Liverpool": 8,
        "Stoke City": 9,
        "Chelsea": 10,
        "Everton": 11,
        "Swansea City": 12,
        "Watford": 13,
        "West Bromwich Albion": 14,
        "Crystal Palace": 15,
        "AFC Bournemouth": 16,
        "Sunderland": 17,
        "Newcastle United": 18,
        "Norwich City": 19,
        "Aston Villa": 20,
    }
    la_liga = {
        "Barcelona": 1,
        "Real Madrid": 2,
        "Atlético Madrid": 3,
        "Villarreal": 4,
        "Athletic Club": 5,
        "Celta Vigo": 6,
        "Sevilla": 7,
        "Málaga": 8,
        "Real Sociedad": 9,
        "Real Betis": 10,
        "Las Palmas": 11,
        "Valencia": 12,
        "Espanyol": 13,
        "Eibar": 14,
        "RC Deportivo La Coruña": 15,
        "Granada": 16,
        "Sporting Gijón": 17,
        "Rayo Vallecano": 18,
        "Getafe": 19,
        "Levante UD": 20,
    }
    bundesliga = {
        "Bayern Munich": 1,
        "Borussia Dortmund": 2,
        "Bayer Leverkusen": 3,
        "Borussia Mönchengladbach": 4,
        "Schalke 04": 5,
        "FSV Mainz 05": 6,
        "Hertha Berlin": 7,
        "Wolfsburg": 8,
        "FC Köln": 9,
        "Hamburger SV": 10,
        "Ingolstadt": 11,
        "Augsburg": 12,
        "Werder Bremen": 13,
        "Darmstadt 98": 14,
        "Hoffenheim": 15,
        "Eintracht Frankfurt": 16,
        "VfB Stuttgart": 17,
        "Hannover 96": 18,
    }
    serie_a = {
        "Juventus": 1,
        "Napoli": 2,
        "AS Roma": 3,
        "Inter Milan": 4,
        "Fiorentina": 5,
        "Sassuolo": 6,
        "AC Milan": 7,
        "Lazio": 8,
        "Chievo": 9,
        "Empoli": 10,
        "Genoa": 11,
        "Torino": 12,
        "Atalanta": 13,
        "Bologna": 14,
        "Sampdoria": 15,
        "Palermo": 16,
        "Udinese": 17,
        "Carpi": 18,
        "Frosinone": 19,
        "Hellas Verona": 20,
    }
    ligue_1 = {
        "Paris Saint-Germain": 1,
        "Lyon": 2,
        "AS Monaco": 3,
        "OGC Nice": 4,
        "Lille": 5,
        "Saint-Étienne": 6,
        "Caen": 7,
        "Rennes": 8,
        "Angers": 9,
        "Bastia": 10,
        "Bordeaux": 11,
        "Montpellier": 12,
        "Marseille": 13,
        "Nantes": 14,
        "Lorient": 15,
        "Guingamp": 16,
        "Toulouse": 17,
        "Stade de Reims": 18,
        "Gazélec Ajaccio": 19,
        "Troyes": 20,
    }

    return {
        "premier_league": premier_league,
        "la_liga": la_liga,
        "bundesliga": bundesliga,
        "serie_a": serie_a,
        "ligue_1": ligue_1,
    }


# falta criar as views


def create_views():
    competitions = list(get_competition_positions().keys())
    for competition in competitions:
        drop_query = (
            f"""DROP MATERIALIZED VIEW IF EXISTS METRICS.fame_{competition}_CLEANED;"""
        )
        db.execute_query(drop_query)
        query = f"""

        CREATE MATERIALIZED VIEW METRICS.fame_{competition}_CLEANED AS
(
SELECT MATCH_ID,
       PLAYER_ID,
       NAME,
       JERSEY_NUMBER,
       POSITION,
       TEAM,
       MATCH_WEEK,
       MANAGER,
       HOME,
       CASE
           WHEN (HOME_SCORE = AWAY_SCORE) THEN 'Draw'
           WHEN ((HOME_SCORE < AWAY_SCORE) AND (HOME = TRUE)) THEN 'Loser'
           WHEN ((HOME_SCORE > AWAY_SCORE) AND (HOME = TRUE)) THEN 'Winner'
           WHEN ((HOME_SCORE > AWAY_SCORE) AND (HOME <> TRUE)) THEN 'Loser'
           WHEN ((HOME_SCORE < AWAY_SCORE) AND (HOME <> TRUE)) THEN 'Winner'
           END AS OUTCOME,
       TOTAL_PASSES,
       DEGREES_IN,
       DEGREES_OUT,
       DEGREE_CENTRALITY,
       IN_DEGREE_CENTRALITY,
       OUT_DEGREE_CENTRALITY,
       AVERAGE_NEIGHBOR_DEGREE,
       CLOSENESS_CENTRALITY,
       BETWEENNESS_CENTRALITY,
       PAGERANK_CENTRALITY,
       hubs,
       authorities,
       ECCENTRICITY,
       AVG_X,
       AVG_Y
FROM METRICS.fame_{competition}_15_16_15_16);
        """
        db.execute_query(query)


def get_df_iq_range_mean(league: str):
    try:
        create_views()
    except:
        raise

    query = f"""select * from metrics.fame_{league}_cleaned;"""
    df = db.df_from_query(query)

    df_iqrange = (
        df.groupby(by=["match_id", "team", "outcome"])[
            ["hubs", "authorities"]
        ].quantile(0.75)
        - df.groupby(by=["match_id", "team", "outcome"])[
            ["hubs", "authorities"]
        ].quantile(0.25)
    ).reset_index()

    df_iqrange.columns = [
        "match_id",
        "team",
        "outcome",
        "iqrange_hub",
        "iqrange_authority",
    ]
    positions = get_competition_positions()[league]
    df_iq_mean = (
        df_iqrange.groupby(by=["team"])[["iqrange_hub", "iqrange_authority"]]
        .mean()
        .reset_index()
    )
    df_iq_mean["pos"] = df_iq_mean["team"].map(positions)

    return df_iq_mean


import numpy as np


def statistical_analysis(league: str):
    print()
    sns.set()
    print(league)
    df_iq_range_mean = get_df_iq_range_mean(league=league)
    # print(df_iq_range_mean)
    print("HUB")
    corr_matrix_hub = df_iq_range_mean.loc[:, ["pos", "iqrange_hub"]].corr(
        method="spearman"
    )
    print(corr_matrix_hub)
    spearman_results = spearmanr(
        df_iq_range_mean["pos"], df_iq_range_mean["iqrange_hub"]
    )
    print(spearman_results)
    # Save plot
    fig, ax = plt.subplots(1, 1, figsize=(15, 5))

    sns.scatterplot(
        data=df_iq_range_mean,
        x="pos",
        y="iqrange_hub",
        ax=ax,
        s=50,
        color="black",
        alpha=0.7,
    )
    ax.set_title(f"{league} - HUB")
    ax.set_xlabel("Position")
    ax.set_ylabel("IQ Range")
    current_path = os.getcwd()

    plt.savefig(
        f"{current_path}/../data/imgs/{league}_hub.png",
        dpi=300,
        bbox_inches="tight",
        transparent=True,
    )

    print("AUTHORITY")

    corr_matrix_authority = df_iq_range_mean.loc[:, ["pos", "iqrange_authority"]].corr(
        method="spearman"
    )
    print(corr_matrix_authority)
    spearman_results = spearmanr(
        df_iq_range_mean["pos"], df_iq_range_mean["iqrange_authority"]
    )
    print(spearman_results)
    # Save plot
    fig, ax = plt.subplots(1, 1, figsize=(15, 5))

    sns.scatterplot(
        data=df_iq_range_mean,
        x="pos",
        y="iqrange_authority",
        ax=ax,
        s=50,
        color="orange",
        alpha=0.7,
    )
    ax.set_title(f"{league} - AUTHORITY")
    ax.set_xlabel("Position")
    ax.set_ylabel("IQ Range")
    ## save in high quality
    plt.savefig(
        f"{current_path}/../data/imgs/{league}_authority.png",
        dpi=300,
        bbox_inches="tight",
        transparent=True,
    )

    fig, ax = plt.subplots(1, 1, figsize=(15, 5))

    sns.scatterplot(
        data=df_iq_range_mean,
        x="pos",
        y="iqrange_hub",
        ax=ax,
        s=50,
        color="black",
        alpha=0.7,
    )
    sns.scatterplot(
        data=df_iq_range_mean,
        x="pos",
        y="iqrange_authority",
        ax=ax,
        s=50,
        color="orange",
        alpha=0.7,
    )
    x = df_iq_range_mean["pos"]
    y = df_iq_range_mean["iqrange_hub"]
    fit = np.polyfit(x, y, deg=1)
    sns.lineplot(
        x=x, y=fit[0] * x + fit[1], color="black", linestyle="dashed", linewidth=1
    )

    x = df_iq_range_mean["pos"]
    y = df_iq_range_mean["iqrange_authority"]
    fit = np.polyfit(x, y, deg=1)
    sns.lineplot(
        x=x, y=fit[0] * x + fit[1], color="orange", linestyle="dashed", linewidth=1
    )

    sns.despine()

    sns.set_style(rc={"axes.facecolor": "white", "figure.facecolor": "grey"})

    plt.xlabel("Team position")
    plt.xticks(np.arange(1, 21, 1))
    plt.ylabel("Interquartile range")
    plt.legend(["Hub", "Authority"])
    plt.savefig(
        f"{current_path}/../data/imgs/{league}_hub_authority.png",
        dpi=300,
        bbox_inches="tight",
        #        transparent=True,
    )


def run_analysis():
    leagues = list(get_competition_positions().keys())
    for league in leagues:
        statistical_analysis(league=league)


if __name__ == "__main__":
    run_analysis()
