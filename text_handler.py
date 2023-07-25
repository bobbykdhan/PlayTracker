import time

from twilio.rest import Client

from database import get_database_value, log_play


def send_text(number, message_content, override_snooze=False):
    if time.time() > float(get_database_value("SNOOZE")[0]) or override_snooze:
        account_sid = get_database_value('TWILIO_ACCOUNT_SID')[0]
        auth_token = get_database_value("TWILIO_AUTH_TOKEN")[0]
        client = Client(account_sid, auth_token)

        message = client.messages.create(
            body=message_content,
            from_="+1" + get_database_value('TWILIONUMBER')[0],
            to="+1" + str(number)
        )

        print("Sent Text Message to " + str(number))
    else:
        print("Snoozed. Not sending text message.")


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
