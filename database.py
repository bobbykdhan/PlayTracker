import os
from datetime import datetime

from mysql import connector as sql
import re

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

def remove_emojis(data):
    emoj = re.compile("["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
        u"\U00002500-\U00002BEF"  # chinese char
        u"\U00002702-\U000027B0"
        u"\U00002702-\U000027B0"
        u"\U000024C2-\U0001F251"
        u"\U0001f926-\U0001f937"
        u"\U00010000-\U0010ffff"
        u"\u2640-\u2642" 
        u"\u2600-\u2B55"
        u"\u200d"
        u"\u23cf"
        u"\u23e9"
        u"\u231a"
        u"\ufe0f"  # dingbats
        u"\u3030"
                      "]+", re.UNICODE)
    return re.sub(emoj, '', data)

def log_spam(channel,author,value):
    mysql = sql.connect(
        host=os.environ['DBHOST'],
        user=os.environ['DBUSER'],
        password=os.environ['DBPASSWORD'],
        database=os.environ['DBNAME']
    )
    mycursor = mysql.cursor()
    channel = remove_emojis(channel)
    author = remove_emojis(author)
    value = remove_emojis(value)

    mycursor.execute(f"INSERT INTO spam_storage (channel,author,messages,date) VALUES ('{channel}','{author}','{value}','{get_current_time()}')")
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
