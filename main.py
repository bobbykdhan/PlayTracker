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
    response = MessagingResponse()
    if get_database_value('MYNUMBER')[0] in From:
        if "/snooze" in Body.lower():
            print("Received a snooze message.")
            time_str = (_ := re.findall(r'\d+', Body.lower())[0] if re.findall(r'\d+', Body.lower()) else 5)
            response.message(f"Snoozed for {time_str} minutes.")
            set_database_value("SNOOZE", str(float(time_str) * 60 + time.time()))
        elif "/cancel" in Body.lower():
            print("Received a cancel message.")
            response.message(f"Canceled snooze")
            set_database_value("SNOOZE", str(000))
        elif "/regular" in Body.lower():
            print("Received a regular message.")
            if bool(float(get_database_value("REGULAR")[0])):
                response.message(f"Disabled regular messages")
                set_database_value("REGULAR", str(0))
            else:
                response.message(f"Enabled regular messages")
                set_database_value("REGULAR", str(1))
        elif "/debug" in Body.lower():
            print("Received a debug message.")
            if bool(float(get_database_value("DEBUG")[0])):
                response.message(f"Disabled Debug Mode. Restart server to take effect.")
                set_database_value("DEBUG", str(0))
            else:
                response.message(f"Enabled Debug Mode. Restart server to take effect.")
                set_database_value("DEBUG", str(1))
        return Response(content=str(response), media_type="application/xml")
    else:
        print(f"Text from: {From} and contains: {Body}")
        return {"message": f"Text from: {From} and contains: {Body}"}

def init():
    load_dotenv()
    global debug
    debug = int(get_database_value('DEBUG')[0])

    config = uvicorn.Config("main:app", host="0.0.0.0", port=8080, log_level="info")
    server = uvicorn.Server(config)
    webserver = server.serve()

    bot_call = bot.start(get_database_value((_ := "TESTDISCORDAUTH" if debug else "DISCORDAUTH"))[0])

    asyncio.ensure_future(bot_call)
    asyncio.ensure_future(webserver)

    loop = asyncio.get_event_loop()
    loop.run_forever()


if __name__ == "__main__":
    init()
