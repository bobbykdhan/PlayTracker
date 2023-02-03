import os
import re
import discord
import time
from discord.ext import commands
from dotenv import load_dotenv
from twilio.rest import Client
import subprocess
from paramiko import SSHClient
import paramiko

description = '''Don't worry about it.'''

bot = commands.Bot(os.getenv("BOTOVERRIDE"), self_bot=True)


@bot.event
async def on_ready():
    print("Enabling Bot v1.0")
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')



def sendText(number, playMessage):
    account_sid = os.environ['TWILIO_ACCOUNT_SID']
    auth_token = os.environ["TWILIO_AUTH_TOKEN"]
    client = Client(account_sid, auth_token)

    message = client.messages.create(
        body=playMessage,
        from_="+1" + os.environ['TWILIONUMBER'],
        to="+1" + str(number)
    )

    print("Sent Text Message to " + str(number))

# https://www.devdungeon.com/content/python-ssh-tutorial
# https://www.geeksforgeeks.org/convert-text-speech-python/

def playAlarm():
    client = SSHClient()
    # client.load_system_host_keys()
    # client.load_host_keys('~/.ssh/known_hosts')
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    client.connect(os.environ['DESKTOPIP'], port=22, username=os.environ['SSHUSERNAME'], password=os.environ['SSHPASSWORD'],look_for_keys=False )
    stdin, stdout, stderr = client.exec_command('cd ~/Desktop/ && screen -d -m ./playAlarm.py')
    client.close()


@bot.event
async def on_message(message):

    playMakerId = load_dotenv("PLAYMAKERID")
    channelId = load_dotenv("CHANNELID")
    if not debug:
        if message.author.id != playMakerId or message.channel.id != channelId or message.author == bot.user:
            #     if the user is not the guy who makes plays ignore it
            noPlay(message.content)
            return

    expression = (r"^[A-Za-z0-9]{2,4} [0-9]+\.*[0-9]+[cp] @ [0-9]*\.[0-9]+ @everyone")
    pattern = re.compile(expression)
    match = pattern.match(message.content)
    if match is None:
        noPlay(message.content)
    else:
        handleMessage(match.string)


def handleMessage(message):
    ticker, strikePrice, at, price, channel = message.split()

    if (strikePrice[::-1])[0] == "c":
        direction = "Call"
    else:
        direction = "Put"

    strikePrice = strikePrice.replace("c", "")
    strikePrice = strikePrice.replace("p", "")

    print("Found a play:")
    newMessage = "Ticker: " + ticker + " \n" + "Strike Price: " + strikePrice + " \n" \
                 + "Contract direction: " + direction \
                 + " \n" + "Contract Price: " + price
    print(newMessage)


    # sendText(os.getenv("MYNUMBER"), newMessage)
    # sendMultipleTexts(newMessage)
    # os.system("chmod +x test.sh")
    playAlarm()
    # os.system("./test.sh")

def sendMultipleTexts(message):
    print("Sending to multiple numbers")
    numbers = os.getenv("NUMBERS").split(",")
    for number in numbers:
        sendText(number, message)
def noPlay(message):
    print("No play found.")
    print("Regular Message: " + message)


load_dotenv()
debug = int(os.getenv("DEBUG"))



if debug:
    bot.run(os.getenv("TESTDISCORDAUTH"))
else:
    bot.run(os.getenv("DISCORDAUTH"))


