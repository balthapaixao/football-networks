import pandas as pd

import psycopg2
from sqlalchemy import create_engine


def get_connection():
    """
    Get the database connection
    """
    conn = psycopg2.connect(
        host="localhost",
        database="football_networks",
        user="balthapaixao",
        password="hard3st_p4ss",
        port=5432,
    )
    return conn


def get_engine():
    """
    Get the database engine
    """
    engine = create_engine(
        "postgresql+psycopg2://balthapaixao:hard3st_p4ss@localhost:5432/football_networks"
    )
    return engine


def load_postgres(file_path: str):
    df_metrics = pd.read_csv(file_path)
    champ_name = file_path.split("/")[-1].split(".")[0]
    table_name = f"fame_{champ_name}_15_16"
    conn = get_connection()
    engine = get_engine()

    df_metrics.to_sql(
        table_name,
        engine,
        if_exists="replace",
        index=False,
        schema="metrics",
    )

    engine.dispose()
    conn.close()
