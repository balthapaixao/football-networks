# Functions to get Metrics

# from shapely.geometry import Polygon
# from scipy.spatial import Voronoi
import networkx as nx

import pandas as pd
import numpy as np

from . import extraction as extract


def get_passes_digraph(df_passes: pd.DataFrame) -> nx.DiGraph:
    team_a, team_b = df_passes["passer_team"].unique()
    df_passes_a = df_passes.loc[df_passes["passer_team"] == team_a]
    df_passes_b = df_passes.loc[df_passes["passer_team"] == team_b]

    G_a = nx.DiGraph()
    G_b = nx.DiGraph()
    G_a.add_nodes_from(df_passes_a["passer_id"].unique())
    G_b.add_nodes_from(df_passes_b["passer_id"].unique())

    for i, row in df_passes_a.iterrows():
        G_a.add_edge(row["passer_id"], row["recipient_id"], weight=row["passes"])

    for i, row in df_passes_b.iterrows():
        G_b.add_edge(row["passer_id"], row["recipient_id"], weight=row["passes"])

    return G_a, G_b


def get_graph_metrics(G: nx.DiGraph) -> pd.DataFrame:
    """
    Generates a dataframe of the centrality metrics
    """
    df_metrics = pd.DataFrame()
    df_metrics["total_passes"] = pd.Series(dict(G.degree(weight="weight")))
    df_metrics["degrees_in"] = pd.Series(dict(G.in_degree()))
    df_metrics["degrees_out"] = pd.Series(dict(G.out_degree()))
    df_metrics["average_neighbor_degree"] = pd.Series(nx.average_neighbor_degree(G))
    df_metrics["degree_centrality"] = pd.Series(nx.degree_centrality(G))
    df_metrics["in_degree_centrality"] = pd.Series(nx.in_degree_centrality(G))
    df_metrics["out_degree_centrality"] = pd.Series(nx.out_degree_centrality(G))
    df_metrics["closeness_centrality"] = pd.Series(nx.closeness_centrality(G))
    df_metrics["betweenness_centrality"] = pd.Series(nx.betweenness_centrality(G))
    df_metrics["pagerank_centrality"] = pd.Series(nx.pagerank(G))

    total_auth_degrees = sum(dict(G.in_degree()).values())
    auth = {node: val / total_auth_degrees for node, val in dict(G.in_degree()).items()}

    total_hub_degrees = sum(dict(G.out_degree()).values())
    hub = {node: val / total_hub_degrees for node, val in dict(G.out_degree()).items()}
    df_metrics["hubs"] = pd.Series(hub)
    df_metrics["authorities"] = pd.Series(auth)

    try:
        df_metrics["eccentricity"] = pd.Series(nx.eccentricity(G))
    except nx.NetworkXError:
        # NetworkXError: Found infinite path length because the digraph is not strongly connected
        df_metrics["eccentricity"] = np.nan

    df_metrics = df_metrics.reset_index(names="player_id")
    return df_metrics


# def voronoi_area(df_metrics: pd.DataFrame) -> pd.DataFrame:
#    voronoi_areas = []
#    coords = df_metrics[["avg_x", "avg_y"]].to_numpy()
#    vor = Voronoi(coords)
#    for region in vor.regions:
#        if len(region) > 0 and region[0] != -1:
#            vertices = np.array([vor.vertices[i] for i in region])
#            polygon = Polygon(vertices)
#            area = polygon.area
#            voronoi_areas.append(area)

#    df_metrics["voronoi_area"] = voronoi_areas

#    return df_metrics


def average_location(
    df_metrics: pd.DataFrame, player_objs_dict: object
) -> pd.DataFrame:
    for i, row in df_metrics.iterrows():
        df_metrics.loc[i, "avg_x"] = player_objs_dict[row["player_id"]].x
        df_metrics.loc[i, "avg_y"] = player_objs_dict[row["player_id"]].y
    return df_metrics


def process_match(
    match_id: int, df_matches: pd.DataFrame, slice_minutes: int = None
) -> pd.DataFrame:
    """
    Process the match
    """

    df_match = extract.get_match(match_id)
    df_match.to_csv(f"../../data/raw/match_{match_id}.csv", index=False)

    df_starting_xi = extract.get_starting_XI(df_match)

    df_players = extract.get_players(match_id=match_id)

    if slice_minutes:
        ...

    else:

        df_passes = extract.prepare_passes_df(
            df_match=df_match, df_starting_xi=df_starting_xi
        )

        starters, player_objs_dict = extract.get_starters_list(df_match, df_starting_xi)

        passes_graph_a, passes_graph_b = get_passes_digraph(df_passes=df_passes)

        df_metrics_a = get_graph_metrics(passes_graph_a)
        df_metrics_b = get_graph_metrics(passes_graph_b)

        df_metrics_a = df_metrics_a.merge(
            df_starting_xi[["id", "jersey_number", "name", "team"]],
            left_on=["player_id"],
            right_on=["id"],
            how="left",
        )

        df_metrics_b = df_metrics_b.merge(
            df_starting_xi[["id", "jersey_number", "name", "team"]],
            left_on=["player_id"],
            right_on=["id"],
            how="left",
        )
        # add location and voronoi area
        df_metrics_a = average_location(df_metrics_a, player_objs_dict)
        # df_metrics_a = voronoi_area(df_metrics_a)
        df_metrics_b = average_location(df_metrics_b, player_objs_dict)
        # df_metrics_b = voronoi_area(df_metrics_b)

        df_metrics = pd.concat([df_metrics_a, df_metrics_b])
        df_metrics["match_id"] = match_id

        df_metrics = df_metrics.merge(
            df_matches[
                [
                    "match_id",
                    "home_score",
                    "away_score",
                    "match_week",
                    "home_managers",
                    "away_managers",
                    "home_team",
                    "away_team",
                ]
            ],
            left_on="match_id",
            right_on="match_id",
            how="left",
        ).drop(columns=["id"])

        df_metrics["home"] = df_metrics.apply(
            lambda row: True if row["team"] == row["home_team"] else False, axis=1
        )
        df_metrics["manager"] = df_metrics.apply(
            lambda row: row["home_managers"] if row["home"] else row["away_managers"],
            axis=1,
        )
        df_metrics = df_metrics.drop(
            columns=["home_managers", "away_managers", "home_team", "away_team"]
        )

        # add player position
        df_metrics = df_metrics.merge(
            df_players[["player_id", "position"]], left_on="player_id", right_on="player_id"
        )

    return df_metrics
