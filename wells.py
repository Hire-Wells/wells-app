"""
Wells Web API.
"""

import json
import sqlite3
import requests
import Mods.identity as identity
import Mods.intercom as intercom
import Mods.tokens as tokens
from slackeventsapi import SlackEventAdapter
from flask import Flask, request
from html2text import html2text
import slack

# Auth Tokens
with open("config.json", "r") as h:
    config = json.load(h)
    h.close()
# Slack API Token.
SLACK_SIGNING_SECRET = config["slack"]["SIGNING_SECRET"]

# Flask app
app = Flask(__name__)

# Slack events API object.
slack_events_adapter = SlackEventAdapter(
    SLACK_SIGNING_SECRET, "/slack/events/", app)


# Intercom client
intercomClient = intercom.Client(config["intercom"]["ACCESS_TOKEN"])

"""
Auth Events
"""
@app.route('/auth/', methods=['GET'])
def authWorkspace(**payload):
    """
    Executes when a workspace is going to be authenticated.
    """

    # Parsing the temp authorization code from Slack.
    authCode = request.args.get('code')
    # Exchanging it for a full auth token.
    authParams = {
        "Content-Type": "application/json",
        "client_id": config["slack"]["CLIENT_ID"],
        "client_secret": config["slack"]["CLIENT_SECRET"],
        "code": authCode
    }
    r = requests.post(
        url="https://slack.com/api/oauth.access", data=authParams)
    # Getting back the token information.
    tokenData = r.json()
    teamId = tokenData["team_id"]
    botUserId = tokenData["bot"]["bot_user_id"]
    botAccessToken = tokenData["bot"]["bot_access_token"]

    # Storing it into the token database.
    conn = sqlite3.connect("database.db")
    conn.execute("INSERT INTO tokens VALUES('" + teamId +
                 "','" + botUserId + "','" + botAccessToken + "')")
    conn.commit()
    conn.close()
    return "Authentication succeeded. You may now close this tab."


"""
Slack Events
"""
@slack_events_adapter.on("message")
def newMessage(payload):
    """
    Executes when an IM is sent to Wells.
    """
    # Parsing the received information.
    data = payload["event"]
    if("bot_id" not in data): # If the message isn't from a user.
        # Getting the user's information.
        userId = data["user"]
        token = tokens.getToken(payload["team_id"])
        user = identity.getUser(userId, token)
        realName = user["real_name"]
        email = user["email"]
        channelId = data["channel"]
        teamId = payload["team_id"]
        intercomClient.gotMessage(
            userId, teamId, channelId, realName, email, data["text"])


"""
Intercom Events
"""
@app.route('/intercom/', methods=['POST'])
def onMessageReceive():
    """
    Executes when an intercom message was sent back to the user.
    """
    data = json.loads(request.data) # Loads the response JSON.
    if(data["data"]["item"]["type"] != "conversation"):
        print("Incoming intercom test request!")
        return "OK"
    # Parses the response text and converts it to non-html.
    responseText = html2text(
        data["data"]["item"]["conversation_parts"]["conversation_parts"][0]["body"])

    # Formatting a message.
    message = [
        {
            "type": "section",
            "text": {
                "type": "plain_text",
                "text": responseText
            }
        }
    ]

    # Adding links per attachment.
    attachments = data["data"]["item"]["conversation_parts"]["conversation_parts"][0]["attachments"]
    if(len(attachments) > 0):
        # If there is at least one attachment.

        filesText = "_Attachments:_"
        for file in attachments:
            fileName = file["name"]
            fileUrl = file["url"]
            filesText+= "\n" + "*<" + fileUrl + "|" + fileName + ">*"

        # Adding the divider.
        message.append({
            "type": "divider"
        })
        message.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": filesText
            }
        })

    email = data["data"]["item"]["user"]["email"]

    # Retrieves the channel ID from the database.
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT channelId, teamId FROM users WHERE email='" + email + "'")
    user = c.fetchone()
    channelId = user[0]
    teamId = user[1]

    # Sends the message to the user.
    # Fetching the auth token.
    token = tokens.getToken(teamId)
    slack_client = slack.WebClient(token=token)
    response = slack_client.chat_postMessage(
        channel=channelId,
        blocks=message
    )

    # Returns 200 to Intercom.
    return "OK"


# Start the server on port 3000
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
