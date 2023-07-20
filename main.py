import atexit
import time
import os
import re
from datetime import datetime

from fastapi import FastAPI, BackgroundTasks, Response, Request, Form
from twilio.twiml.messaging_response import MessagingResponse
import mysql.connector as sql
import uvicorn as uvicorn
from discord.ext import commands
from dotenv import load_dotenv
from twilio.rest import Client
from paramiko import SSHClient
import paramiko
import asyncio

bot = commands.Bot(os.getenv("BOTOVERRIDE"), self_bot=True)
app = FastAPI()


@bot.event
async def on_ready():
    print("Enabling Bot v1.0")
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')

    numbers = get_database_value('NUMBERS')
    numbers_used = ""
    for number in numbers:
        numbers_used += number + ", "
    if time.time() - float(get_database_value('LASTRUN')[0]) > 3000:
        if debug:
            send_text(get_database_value('MYNUMBER')[0], "Bot is now online in debug mode.")
        else:
            send_text(get_database_value('MYNUMBER')[0],
                      f"Bot is now online in live mode using the following numbers: {numbers_used}")
    else:
        print("Bot ran less then 30 minutes ago. Not sending text message.")

    set_database_value('LASTRUN', str(time.time()))


def send_text(number, play_message):
    if time.time() > float(get_database_value("SNOOZE")[0]):
        account_sid = get_database_value('TWILIO_ACCOUNT_SID')[0]
        auth_token = get_database_value("TWILIO_AUTH_TOKEN")[0]
        client = Client(account_sid, auth_token)

        message = client.messages.create(
            body=play_message,
            from_="+1" + get_database_value('TWILIONUMBER')[0],
            to="+1" + str(number)
        )

        print("Sent Text Message to " + str(number))
    else:
        print("Snoozed. Not sending text message.")


@bot.event
async def on_message(message):
    play_maker_id = int(get_database_value("PLAYMAKERID")[0])
    channel_id = int(get_database_value('CHANNELID')[0])

    if not debug:
        if message.author.id != play_maker_id and \
                message.channel.id != channel_id:
            no_play(message.content)
            return

    play_expression = r"^[A-Za-z]{2,5} [0-9]+\.*[0-9]*[cp]\s(?:0dte\s)?@\s(?:0dte )?[0-9]+\.*[0-9]*\s(?:0dte )?@everyone\s*(?:0dte)?\s*"
    play_pattern = re.compile(play_expression)
    play_match = play_pattern.match(message.content)

    if play_match is not None:
        if "0dte" in play_match.string:
            play = play_match.string.replace("0dte ", "")
            handle_message(play, True)
        else:
            handle_message(play_match.string, False)
    else:
        no_play(message.content)
        if message.channel.id == channel_id or debug:
            if bool(float(get_database_value("REGULAR")[0])):
                send_text(get_database_value('MYNUMBER')[0],
                          str("Regular message from the channel:\n" + message.content))
            else:
                print("Regular messages disabled")
            log_date("messages", message.content, "message_storage")


def handle_message(message, lotto=False):
    ticker, strike_price, _, price, _ = message.split()

    if (strike_price[::-1])[0] == "c":
        direction = "Call"
    else:
        direction = "Put"

    strike_price = strike_price.replace("c", "")
    strike_price = strike_price.replace("p", "")

    print("Found a play:")
    new_message = "Ticker: " + ticker + " \n" + "Strike Price: " + strike_price + " \n" \
                  + "Contract direction: " + direction \
                  + " \n" + "Contract Price: " + price
    if lotto and int(get_database_value('LOTTO')[0]) == 1:
        new_message += " \n 0 DAYS TO EXPIRATION \n Lotto Play so be cautious."

    if lotto:
        log_play(new_message, True)
    else:
        log_play(new_message)
    print(new_message)

    if not debug:
        send_multiple_texts(new_message)
    else:
        send_text(get_database_value('MYNUMBER')[0], new_message)


def send_multiple_texts(message):
    # print("Sending to multiple numbers")
    numbers = get_database_value('NUMBERS')
    for number in numbers:
        print("Sending to " + number)
        send_text(number, message)


def get_current_time():
    return datetime.now().strftime("%m/%d/%Y, %H:%M:%S")


def no_play(message):
    print("No play found.")
    print("Regular Message: " + message)


@app.get('/')
async def request(request: Request):
    print(f"Request recieved: {str(request)}")
    return Response(content=f"Request recieved: {str(request)}", media_type="application/xml")


@app.get('/sms')
@app.post('/sms')
async def chat(From: str = Form(...), Body: str = Form(...)):
    if "/snooze" in Body.lower() and get_database_value('MYNUMBER')[0] in From:
        print("Received a snooze message.")
        response = MessagingResponse()
        time_str = (_ := re.findall(r'\d+', Body.lower())[0] if re.findall(r'\d+', Body.lower()) else 5)
        msg = response.message(f"Snoozed for {time_str} minutes.")
        set_database_value("SNOOZE", str(float(time_str) * 60 + time.time()))
        return Response(content=str(response), media_type="application/xml")
    elif "/cancel" in Body.lower() and get_database_value('MYNUMBER')[0] in From:
        print("Received a cancel message.")
        response = MessagingResponse()
        msg = response.message(f"Canceled snooze")
        set_database_value("SNOOZE", str(000))
        return Response(content=str(response), media_type="application/xml")
    elif "/regular" in Body.lower() and get_database_value('MYNUMBER')[0] in From:
        print("Received a regular message.")
        response = MessagingResponse()
        enabled = bool(float(get_database_value("REGULAR")[0]))
        if enabled:
            msg = response.message(f"Disabled regular messages")
            set_database_value("REGULAR", str(0))
        else:
            msg = response.message(f"Enabled regular messages")
            set_database_value("REGULAR", str(1))
        return Response(content=str(response), media_type="application/xml")
    elif "/debug" in Body.lower() and get_database_value('MYNUMBER')[0] in From:
        print("Received a debug message.")
        response = MessagingResponse()
        enabled = bool(float(get_database_value("DEBUG")[0]))
        if enabled:
            msg = response.message(f"Disabled Debug Mode. Restart server to take effect.")
            set_database_value("DEBUG", str(0))
        else:
            msg = response.message(f"Disabled Debug Mode. Restart server to take effect.")
            set_database_value("DEBUG", str(1))
        return Response(content=str(response), media_type="application/xml")
    else:
        print(f"Text from: {From} and contains: {Body}")
        return {"message": f"Text from: {From} and contains: {Body}"}


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
    table = (_ := "PLAY_STORAGE" if debug else "LOTTO_STORAGE")

    ticker, strike_price, contract_direction, contract_price = [line.split(": ")[1] for line in
                                                                play.strip().split("\n")[:3]]


    mycursor.execute(f"INSERT INTO {table} (Ticker, Strike Price, Contract Direction, Contract Price,date) VALUES ('{ticker}', '{strike_price}', '{contract_direction}', '{contract_price}','{get_current_time()}')")

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


if __name__ == "__main__":
    load_dotenv()
    debug = int(get_database_value('DEBUG')[0])

    config = uvicorn.Config("main:app", host="0.0.0.0", port=8080, log_level="info")
    server = uvicorn.Server(config)
    webserver = server.serve()

    bot_call = bot.start(get_database_value((_ := "TESTDISCORDAUTH" if debug else "DISCORDAUTH"))[0])

    bot_task = asyncio.ensure_future(bot_call)
    server_task = asyncio.ensure_future(webserver)

    loop = asyncio.get_event_loop()
    loop.run_forever()
