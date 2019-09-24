from flask import Flask, request
import json
import sqlite3
from html2text import html2text
from slackclient import SlackClient

app = Flask(__name__)

# Auth tokens
with open("config.json", "r") as h:
    config = json.load(h)
slack_bot_token = config["slack"]["BOT_TOKEN"]

# Slack Web API
slack_client = SlackClient(token=slack_bot_token)


@app.route('/', methods=['POST'])
def onMessageReceive():
    data = json.loads(request.data)  # Loads the response JSON.

    # Parses the response text and converts it to non-html.
    responseText = html2text(
        data["data"]["item"]["conversation_parts"]["conversation_parts"][0]["body"])
    email = data["data"]["item"]["user"]["email"]

    # Retrieves the channel ID from the database.
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT channelId FROM users WHERE email='" + email + "'")
    channelId = c.fetchone()[0]
    print("Channel ID: " + channelId + "\nMessage: " + responseText)

    # Sends the message to the user.
    response = slack_client.api_call(
        "chat.postMessage", channel=channelId, text=responseText)

    # Returns 200 to Intercom.
    return "OK"


if __name__ == "__main__":
    app.run()
