import atexit
import datetime
import os
import re

from fastapi import FastAPI, BackgroundTasks, Response, Form
from twilio.twiml.messaging_response import MessagingResponse
import mysql.connector as sql
import uvicorn as uvicorn
from discord.ext import commands
from dotenv import load_dotenv
from twilio.rest import Client
from paramiko import SSHClient
import paramiko

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
    if debug:
        send_text(get_database_value('MYNUMBER')[0], "Bot is now online in debug mode.")
    else:
        send_text(get_database_value('MYNUMBER')[0], f"Bot is now online in live mode using the following numbers: {numbers_used}")


def send_text(number, play_message):
    account_sid = get_database_value('TWILIO_ACCOUNT_SID')[0]
    auth_token = get_database_value("TWILIO_AUTH_TOKEN")[0]
    client = Client(account_sid, auth_token)

    message = client.messages.create(
        body=play_message,
        from_="+1" + get_database_value('TWILIONUMBER')[0],
        to="+1" + str(number)
    )

    print("Sent Text Message to " + str(number))


def play_alarm():
    print("Playing Alarm")
    client = SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    client.connect(get_database_value('DESKTOPIP')[0], port=22, username=get_database_value('SSHUSERNAME')[0],
                   password=get_database_value('SSHPASSWORD')[0], look_for_keys=False)
    stdin, stdout, stderr = client.exec_command('cd ~/Desktop/ && screen -d -m ./playAlarm.py')
    client.close()


@bot.event
async def on_message(message):
    play_maker_id = int(get_database_value("PLAYMAKERID")[0])
    channel_id = int(get_database_value('CHANNELID')[0])

    if not debug:
        if message.author.id != play_maker_id and \
                message.channel.id != channel_id:
            no_play(message.content)
            return

    expression = r"^[A-Za-z]{2,4} [0-9]+\.*[0-9]*[cp] @ [0-9]+\.*[0-9]* @everyone"
    lotto_expression = r"^[A-Za-z]{2,4} [0-9]+\.*[0-9]*[cp] 0dte @ [0-9]+\.*[0-9]* @everyone"
    pattern = re.compile(expression)
    match = pattern.match(message.content)
    if match is not None:
        handle_message(match.string)
    elif pattern.match(message.content) is not None:
        handle_message(match.string, True)
    else:
        no_play(message.content)
        if message.channel.id == channel_id:
            send_text(get_database_value('MYNUMBER')[0], str("Regular message from the channel:\n" + message.content))


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
    print(new_message)

    if not debug:
        send_multiple_texts(new_message)
    else:
        send_text(get_database_value('MYNUMBER')[0], new_message)

    if int(get_database_value('PLAYALARM')[0]) == 1:
        play_alarm()
        send_text(get_database_value('MYNUMBER')[0], "Playing alarm.")


def send_multiple_texts(message):
    # print("Sending to multiple numbers")
    numbers = get_database_value('NUMBERS')
    for number in numbers:
        print("Sending to " + number)
        send_text(number, message)


def no_play(message):
    print("No play found.")
    print("Regular Message: " + message)



def get_database_value(query,table = "envVars"):
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


if __name__ == "__main__":

    load_dotenv()
    atexit.register(send_text, get_database_value('MYNUMBER')[0], "Bot is now offline.")
    debug = int(get_database_value('DEBUG')[0])
    if debug:
        bot.run(os.getenv("TESTDISCORDAUTH"))
    else:
        bot.run(os.getenv("DISCORDAUTH"))
    uvicorn.run(app, host="0.0.0.0", port=8080)


