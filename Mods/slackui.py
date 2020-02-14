"""
Slack UI modules.
"""
import Mods.tokens as tokens
import Mods.identity as identity
import Mods.errors as errors
import slack
import json
import sqlite3
import requests


def sendHomeScreen(payload):
    """Sends the home app screen to the user.

    Args:
        payload (JSON): The payload of the trigger.

    Returns:
        bool: Whether the operation was successful or not.
    """
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

    # Checking the status of the response.
    response = json.loads(r.text)
    success = response["ok"]
    if not success:
        raise errors.APIError("Slack denied request.")
        print(response)
    return success


def sendModal(payload, modalName):
    """Sends a modal to a user.

    Args:
        payload (JSON): The payload received from the slack trigger.
        modalName (string): Name of the modal to push to the user.

    Returns:
        bool: Whether the request was created successfully.
    """
    # Getting required params.
    triggerId = payload["trigger_id"]
    with open("templates/"+modalName+".json") as h:
        modal = json.load(h)
        h.close()

    # Crafting a data object to send to Slack.
    data = {
        "token": tokens.getToken(payload["team"]["id"]),
        "trigger_id": payload["trigger_id"],
        "view": json.dumps(modal)
    }

    # Creating new request.
    URL = "https://slack.com/api/views.open"
    r = requests.post(url=URL, data=data)

    # Checking the status of the response.
    response = json.loads(r.text)
    success = response["ok"]
    if not success:
        raise errors.APIError(response)
    return success
