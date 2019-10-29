"""
Slack UI modules.
"""
import Mods.tokens as tokens
import Mods.identity as identity
import slack
import json
import sqlite3
import requests


def sendModal(payload):
    # Get required params
    with open("templates/app_home.json", "r") as h:
        appHome = json.load(h)
        h.close()
    data = {
        "token": tokens.getToken(payload["team_id"]),
        "user_id": payload["event"]["user"],
        "view": json.dumps(appHome)
    }
    # Create new request.
    URL = "https://slack.com/api/views.publish"
    r = requests.post(url=URL, data=data)
    return True

