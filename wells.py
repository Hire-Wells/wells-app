"""
Wells Web API.
Carlos Saucedo, 2019
"""

import json
import os
import sqlite3
import requests
import Mods.identity as identity
import Mods.intercom as intercom
import Mods.tokens as tokens
import Mods.slackui as slackui
import Mods.errors as errors
from Mods.teams_bot import TeamsBot
from slackeventsapi import SlackEventAdapter
from flask import Flask, request
import html2text
import slack

# Bot framework module
import asyncio
from datetime import datetime
from types import MethodType
import sys
import pickle
import codecs

from flask import Flask, request, Response
from botbuilder.core import BotFrameworkAdapterSettings, TurnContext, BotFrameworkAdapter, ShowTypingMiddleware
from botbuilder.schema import Activity, ActivityTypes
import uuid

# Auth Tokens
with open("config.json", "r") as h:
    config = json.load(h)
    h.close()
# Slack API Token.
SLACK_SIGNING_SECRET = config["slack"]["SIGNING_SECRET"]

# Flask app
app = Flask(__name__, instance_relative_config=True)
app.config.from_object("config.DefaultConfig")

# Teams loop
LOOP = asyncio.get_event_loop()
# Create adapter.
# See https://aka.ms/about-bot-adapter to learn more about how bots work.
SETTINGS = BotFrameworkAdapterSettings(
    app.config["APP_ID"], app.config["APP_PASSWORD"])
ADAPTER = BotFrameworkAdapter(SETTINGS)
ADAPTER.use(ShowTypingMiddleware(delay=0.5, period=2.0))

# Create the Bot
BOT = TeamsBot(config["intercom"]["ACCESS_TOKEN"])

# Slack events API object.
slack_events_adapter = SlackEventAdapter(
    SLACK_SIGNING_SECRET, "/slack/events/", app)


# Intercom client
intercomClient = intercom.Client(config["intercom"]["ACCESS_TOKEN"])

"""
Microsoft Teams Events
"""
# Listen for incoming requests on /teams/messages
@app.route("/teams/messages", methods=["POST"])
def messages():
    # Main bot message handler.
    if "application/json" in request.headers["Content-Type"]:
        body = request.json
    else:
        return Response(status=415)

    activity = Activity().deserialize(body)
    auth_header = (
        request.headers["Authorization"] if "Authorization" in request.headers else ""
    )

    try:
        task = LOOP.create_task(
            ADAPTER.process_activity(activity, auth_header, BOT.on_turn)
        )
        LOOP.run_until_complete(task)
        return Response(status=201)
    except Exception as exception:
        raise exception


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
    print(tokenData)
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
    files = list()  # Creating the files list.
    if("bot_id" not in data):  # If the message isn't from a bot.
        # If it is a solo link being sent.
        # Managing attachments.
        if "files" in data:
            # Message contains attachments.
            for file in data["files"]:
                files.append(file["url_private_download"])

        # Getting the user's information.
        userId = data["user"]
        token = tokens.getToken(payload["team_id"])
        user = identity.getUser(userId, token)
        realName = user["real_name"]
        email = user["email"]
        channelId = data["channel"]
        teamId = payload["team_id"]
        message = data["text"]

        intercomClient.gotMessage(
            userId, teamId, channelId, realName, email, message, files)


@slack_events_adapter.on("app_home_opened")
def appHome(payload):
    """
    Executes when a user opens his app home.
    """
    slackui.sendHomeScreen(payload)

    # Opening the sqlite3 database.
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    # Checking to see if there is already that user in the database.
    userId = payload["event"]["user"]
    c.execute("SELECT * FROM users WHERE userId='" +
              userId + "';")

    if(payload["event"]["tab"] == "messages" and c.fetchone() == None):

        teamId = payload["team_id"]
        channelId = payload["event"]["channel"]
        with open("templates/auto_responses.json") as h:
            message = json.load(h)["on_join_message"]

        # Getting name and email from Slack.
        URL = "https://slack.com/api/users.info"
        data = {
            "token": tokens.getToken(teamId),
            "user": userId
        }
        r = requests.get(url=URL, params=data)
        data = r.json()
        success = data["ok"]
        if(not success):
            raise errors.APIError(data)
        else:
            email = data["user"]["profile"]["email"]
            realName = data["user"]["real_name"]
            intercomClient.gotAdminMessage(
                userId, teamId, channelId, realName, email, message)

        # Creating new request.
        URL = "https://slack.com/api/chat.postMessage"
        # Crafting a data object to send to Slack.
        data = {
            "token": tokens.getToken(payload["team_id"]),
            "channel": payload["event"]["channel"],
            "text": message
        }
        # Making the request.
        r = requests.post(url=URL, data=data)

        # Checking the status of the response.
        response = json.loads(r.text)
        success = response["ok"]
        if not success:
            raise errors.APIError(response)


"""
Slack Actions
"""
@app.route("/slack/actions/", methods=["POST"])
def onAction():
    # Loads the request information as JSON.
    payload = json.loads(request.form.to_dict()["payload"])
    if payload["type"] == "block_actions":
        # A button was pressed.
        actionId = payload["actions"][0]["action_id"]
        if(actionId == "button_newReq"):
            slackui.sendModal(payload, modalName="new_req_modal")
        # else:
        #     print(payload)
    elif(payload["type"] == "view_submission"):
        # A modal submission went through.
        print(payload["view"]["state"]["values"])
    else:
        print(payload)
    return Response(status=200)


"""
Intercom Events
"""
@app.route('/intercom/', methods=['POST'])
def onMessageReceive():
    """
    Executes when an intercom message was sent back to the user.
    """
    data = json.loads(request.data)  # Loads the response JSON.
    if(data["data"]["item"]["type"] != "conversation"):
        return Response(status=200)
    # Parses the response text and converts it to non-html.
    h = html2text.HTML2Text()
    h.ignore_links = True
    responseText = h.handle(
        data["data"]["item"]["conversation_parts"]["conversation_parts"][0]["body"])
    # Check to see if User is from Teams or Slack.
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    userId = data["data"]["item"]["user"]["user_id"]
    if userId != None:
        # User is a Teams user.
        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute('SELECT reference FROM teams WHERE userId=?;', (userId,))
        referenceEncoded = c.fetchone()[0]
        reference = pickle.loads(referenceEncoded)
        # Send the message to the Teams user.
        LOOP.run_until_complete(
            ADAPTER.continue_conversation(
                reference,
                lambda turn_context: turn_context.send_activity(responseText),
                SETTINGS.app_id if SETTINGS.app_id else uuid.uuid4(),
            )
        )
    else:
        # User is a slack user.
        # Formatting a message block.
        # Info: https://api.slack.com/reference/block-kit/block-elements
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
                filesText += "\n" + "*<" + fileUrl + "|" + fileName + ">*"

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
    return Response(status=200)


# Start the server on port 3000
if __name__ == "__main__":
    try:
        app.run(host="0.0.0.0", port=3978)
    except Exception as exception:
        raise exception
