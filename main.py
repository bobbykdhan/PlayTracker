import atexit
import datetime
import os
import re
from discord.ext import commands
from dotenv import load_dotenv
from twilio.rest import Client
from paramiko import SSHClient
import paramiko

bot = commands.Bot(os.getenv("BOTOVERRIDE"), self_bot=True)


@bot.event
async def on_ready():
    print("Enabling Bot v1.0")
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    if debug:
        send_text(os.environ['MYNUMBER'], "Bot is now online in debug mode.")
    else:
        send_text(os.environ['MYNUMBER'], "Bot is now online in live mode.")


def send_text(number, play_message):
    account_sid = os.environ['TWILIO_ACCOUNT_SID']
    auth_token = os.environ["TWILIO_AUTH_TOKEN"]
    client = Client(account_sid, auth_token)

    message = client.messages.create(
        body=play_message,
        from_="+1" + os.environ['TWILIONUMBER'],
        to="+1" + str(number)
    )

    print("Sent Text Message to " + str(number))


def play_alarm():
    print("Playing Alarm")
    client = SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    client.connect(os.environ['DESKTOPIP'], port=22, username=os.environ['SSHUSERNAME'],
                   password=os.environ['SSHPASSWORD'], look_for_keys=False)
    stdin, stdout, stderr = client.exec_command('cd ~/Desktop/ && screen -d -m ./playAlarm.py')
    client.close()


@bot.event
async def on_message(message):
    play_maker_id = int(os.environ["PLAYMAKERID"])
    channel_id = int(os.environ['CHANNELID'])

    if not debug:
        if message.author.id != play_maker_id and \
                message.channel.id != channel_id:
            no_play(message.content)
            return

    expression = r"^[A-Za-z]{2,4} [0-9]+\.*[0-9]*[cp] @ [0-9]+\.*[0-9]* @everyone"
    pattern = re.compile(expression)
    match = pattern.match(message.content)
    if match is None:
        no_play(message.content)
        if message.channel.id == channel_id:
            send_text(os.environ['MYNUMBER'], str("Regular message from the channel:\n" + message.content))
    else:
        handle_message(match.string)


def handle_message(message):
    ticker, strike_price, at, price, channel = message.split()

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
    if "lotto" in message or "Lotto" in message or "LOTTO" in message:
        new_message += " \n" + "Lotto Play so be cautious."
    print(new_message)

    if not debug:
        send_multiple_texts(new_message)
    else:
        send_text(os.environ['MYNUMBER'], new_message)

    # if datetime.datetime.now().time() < datetime.time(12, 30):
    play_alarm()
    send_text(os.environ['MYNUMBER'], "Playing alarm.")


def send_multiple_texts(message):
    # print("Sending to multiple numbers")
    numbers = os.getenv("NUMBERS").split(",")
    for number in numbers:
        print("Sending to " + number)
        send_text(number, message)


def no_play(message):
    print("No play found.")
    print("Regular Message: " + message)




if __name__ == "__main__":
    load_dotenv()
    atexit.register(send_text, os.environ['MYNUMBER'], "Bot is now offline.")
    debug = int(os.getenv("DEBUG"))
    if debug:
        bot.run(os.getenv("TESTDISCORDAUTH"))
    else:
     bot.run(os.getenv("DISCORDAUTH"))
