"""
Hire wells app.
Carlos Saucedo, 2019.
"""
import os
import slack
import json
import requests
import Mods.identity as identity
import Mods.intercom as intercom

# Auth Tokens
with open("config.json", "r") as h:
    config = json.load(h)

# Setting environment variables.
os.environ["SLACK_API_TOKEN"] = config["slack"]["BOT_TOKEN"]

# Intercom client
intercomClient = intercom.Client(config["intercom"]["ACCESS_TOKEN"])

# Runs on the receipt of a message.
@slack.RTMClient.run_on(event='message')
def newMessage(**payload):
    data = payload["data"]
    web_client = payload["web_client"]
    rtm_client = payload["rtm_client"]

    # If the message is an IM,
    # and does not come from a bot.
    if(data["channel"].startswith("D") and "bot_id" not in data):
        userId = data["user"]
        user = identity.getUser(userId)
        realName = user["real_name"]
        email = user["email"]
        channelId = data["channel"]
        intercomClient.gotMessage(
            userId, channelId, realName, email, data["text"])


# Getting the token from the Environment variable.
slack_token = os.environ["SLACK_API_TOKEN"]

# Initiating the bot.
client = slack.RTMClient(token=slack_token)
client.start()
