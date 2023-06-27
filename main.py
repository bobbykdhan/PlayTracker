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
            send_text(get_database_value('MYNUMBER')[0], f"Bot is now online in live mode using the following numbers: {numbers_used}")
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

    expression = r"^[A-Za-z]{2,4} [0-9]+\.*[0-9]*[cp] @ [0-9]+\.*[0-9]* @everyone"
    lotto_expression = r"^[A-Za-z]{2,4} [0-9]+\.*[0-9]*[cp] 0dte @ [0-9]+\.*[0-9]* @everyone"
    regular_pattern = re.compile(expression)
    regular_match = regular_pattern.match(message.content)
    lotto_pattern = re.compile(lotto_expression)
    lotto_match = lotto_pattern.match(message.content)

    if lotto_match is not None:
        handle_message(lotto_match.string, True)
    elif regular_match is not None:
        handle_message(regular_match.string, False)
    else:
        no_play(message.content)
        if message.channel.id == channel_id or debug:
            send_text(get_database_value('MYNUMBER')[0], str("Regular message from the channel:\n" + message.content))
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
        log_date("plays",new_message,"lotto_storage")
    else:
        log_date("plays", new_message, "play_storage")




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

    if  "/snooze" in Body.lower() and get_database_value('MYNUMBER')[0] in From:
        print("Received a snooze message.")
        response = MessagingResponse()
        time_str = (_ := re.findall(r'\d+', Body.lower())[0] if re.findall(r'\d+', Body.lower()) else 5)
        msg = response.message(f"Snoozed for {time_str} minutes.")
        set_database_value("SNOOZE", str(float(time_str) * 60 + time.time()))
        return Response(content=str(response), media_type="application/xml")
    else: 
        print(f"Text from: {From} and contains: {Body}")
        return  {"message": f"Text from: {From} and contains: {Body}"}


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
def set_database_value(query, value, table = "envVars"):
    mysql = sql.connect(
        host=os.environ['DBHOST'],
        user=os.environ['DBUSER'],
        password=os.environ['DBPASSWORD'],
        database=os.environ['DBNAME']
    )
    mycursor = mysql.cursor()

    mycursor.execute(f"UPDATE {table} SET {query} = '{value}' LIMIT 1")

    mysql.commit()
def add_database_value(query, value, table = "envVars"):
    mysql = sql.connect(
        host=os.environ['DBHOST'],
        user=os.environ['DBUSER'],
        password=os.environ['DBPASSWORD'],
        database=os.environ['DBNAME']
    )
    mycursor = mysql.cursor()

    mycursor.execute(f"INSERT INTO {table} ({query}) VALUES ('{value}')")

    mysql.commit()

def log_date(query, value, table = "envVars"):
    mysql = sql.connect(
        host=os.environ['DBHOST'],
        user=os.environ['DBUSER'],
        password=os.environ['DBPASSWORD'],
        database=os.environ['DBNAME']
    )
    mycursor = mysql.cursor()

    mycursor.execute(f"INSERT INTO {table} ({query},date) VALUES ('{value}','{get_current_time()}')")

    mysql.commit()


def remove_database_value(query, value, table = "envVars"):
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
   
    


