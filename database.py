import os
from datetime import datetime

from mysql import connector as sql


def get_current_time():
    return datetime.now().strftime("%m/%d/%Y, %H:%M:%S")


def get_database_value(query, table="envVars"):
    mysql = sql.connect(
        host=os.environ['DBHOST'],
        user=os.environ['DBUSER'],
        password=os.environ['DBPASSWORD'],
        database=os.environ['DBNAME']
    )
    mycursor = mysql.cursor()

    mycursor.execute(f"SELECT {query} FROM {table}")

    result_tuples = mycursor.fetchall()
    results = []
    for tuple in result_tuples:
        if tuple[0] is not None:
            results.append(tuple[0])
    return results


def set_database_value(query, value, table="envVars"):
    mysql = sql.connect(
        host=os.environ['DBHOST'],
        user=os.environ['DBUSER'],
        password=os.environ['DBPASSWORD'],
        database=os.environ['DBNAME']
    )
    mycursor = mysql.cursor()

    mycursor.execute(f"UPDATE {table} SET {query} = '{value}' LIMIT 1")

    mysql.commit()


def add_database_value(query, value, table="envVars"):
    mysql = sql.connect(
        host=os.environ['DBHOST'],
        user=os.environ['DBUSER'],
        password=os.environ['DBPASSWORD'],
        database=os.environ['DBNAME']
    )
    mycursor = mysql.cursor()

    mycursor.execute(f"INSERT INTO {table} ({query}) VALUES ('{value}')")

    mysql.commit()


def log_date(query, value, table="envVars"):
    mysql = sql.connect(
        host=os.environ['DBHOST'],
        user=os.environ['DBUSER'],
        password=os.environ['DBPASSWORD'],
        database=os.environ['DBNAME']
    )
    mycursor = mysql.cursor()

    mycursor.execute(f"INSERT INTO {table} ({query},date) VALUES ('{value}','{get_current_time()}')")

    mysql.commit()


def log_play(play, lotto=False):
    mysql = sql.connect(
        host=os.environ['DBHOST'],
        user=os.environ['DBUSER'],
        password=os.environ['DBPASSWORD'],
        database=os.environ['DBNAME']
    )
    mycursor = mysql.cursor()
    table = (_ := "PLAY_STORAGE" if lotto else "LOTTO_STORAGE")

    ticker, strike_price, contract_direction, contract_price = [line.split(": ")[1].strip() for line in
                                                                play.strip().split("\n")[:4]]

    mycursor.execute(
        f"INSERT INTO {table} (Ticker, Strike Price, Contract Direction, Contract Price,date) VALUES ('{ticker}', '{strike_price}', '{contract_direction}', '{contract_price}','{get_current_time()}')")

    mysql.commit()


def remove_database_value(query, value, table="envVars"):
    mysql = sql.connect(
        host=os.environ['DBHOST'],
        user=os.environ['DBUSER'],
        password=os.environ['DBPASSWORD'],
        database=os.environ['DBNAME']
    )
    mycursor = mysql.cursor()

    mycursor.execute(f"DELETE FROM {table} WHERE {query} = '{value}'")

    mysql.commit()
