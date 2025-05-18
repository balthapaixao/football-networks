import pandas as pd

import psycopg2
from sqlalchemy import create_engine
import warnings

warnings.simplefilter("ignore")


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


def df_from_query(query: str) -> pd.DataFrame:
    """
    Get a pandas dataframe from a SQL query
    """
    conn = get_connection()
    df = pd.read_sql(query, conn)
    conn.close()
    return df


def execute_query(query: str):
    """
    Execute a SQL query
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query)
    conn.commit()
    conn.close()
