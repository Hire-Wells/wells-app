"""
Gets a user's identity information.
Carlos Saucedo, 2019
"""

import requests
import os
import json

# TODO: Catch errors.
# Fetches the entire User data JSON.
def getUser(userId, token):
    """Fetches information about the user.

    Arguments:
        userId {string} -- The user's Slack ID.
    """
    # Create the package of information to send.
    payload = {'token': token, 'user': userId}
    # Make the request to the Slack API.
    r = requests.get("https://slack.com/api/users.info", params=payload)
    data = json.loads(r.content)
    return(data["user"]["profile"])


def getRealName(userId, token):
    """Fetches a user's real name.

    Arguments:
        userId {string} -- The user's Slack ID.
    """
    return(getUser(userId)["real_name"])


def getEmail(userId, token):
    """Fetches a user's email.

    Arguments:
        userId {string} -- The user's Slack ID.
    """
    return(getUser(userId)["email"])
