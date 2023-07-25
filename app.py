import time
import re
import urllib

from fastapi import FastAPI, Response, Request, Form
from twilio.twiml.messaging_response import MessagingResponse
import uvicorn as uvicorn
from discord.ext import commands
from dotenv import load_dotenv
import asyncio

from database import *
from text_handler import send_text, handle_message

bot = commands.Bot(os.getenv("BOTOVERRIDE"), self_bot=True)
app = FastAPI()

global debug


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


def no_play(message):
    print("No play found.")
    print("Regular Message: " + message)


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

    external_ip = urllib.request.urlopen('https://ident.me').read().decode('utf8')

    if external_ip != get_database_value('SERVERIP')[0]:
        send_text(get_database_value('MYNUMBER')[0],"WARNING: Not running on server therefore text commands will not work!!", True)
    config = uvicorn.Config("app:app", host="0.0.0.0", port=8080, log_level="info")
    server = uvicorn.Server(config)
    webserver = server.serve()

    bot_call = bot.start(get_database_value((_ := "TESTDISCORDAUTH" if debug else "DISCORDAUTH"))[0])

    asyncio.ensure_future(bot_call)
    asyncio.ensure_future(webserver)

    loop = asyncio.get_event_loop()
    loop.run_forever()


if __name__ == "__main__":
    init()
