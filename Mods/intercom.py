"""
Intercom module.
Carlos Saucedo, 2019.
"""

from intercom.client import Client as intercomClient
import sqlite3
import pickle
import codecs
import Mods.tokens as tokens
import requests
import os
import uuid
import json
import Mods.errors as errors


class Client(object):
    def __init__(self, key):
        """An intercom client.
        Arguments:
            key {string} -- Intercom's access key. [More](https://app.intercom.com/a/apps/szdcciir/developer-hub/app-packages/41730/oauth)
        """
        self.client = intercomClient(personal_access_token=key)

    def gotTeamsMessage(self, turn_context):
        """Sends an MS Teams message to Intercom.

        Arguments:
            turn_context {TurnContext} -- MS Teams message metadata.
        """
        # Fetching values
        userId = turn_context.activity.from_property.id
        realName = turn_context.activity.from_property.name
        message = turn_context.activity.text
        # Check to see if the user is in the database.
        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("SELECT * FROM teams WHERE userId='"+userId+"';")
        if(c.fetchone() == None):
            # User does not exist.
            # Add user to Intercom.
            user = self.client.users.create(user_id=userId, name=realName)
            # Set user's source attribute.
            user.custom_attributes["Source"] = "Microsoft Teams"
            self.client.users.save(user)
            # Send the message to intercom.
            newMsg = self.client.messages.create(**{
                "from": {
                    "type": "user",
                    "id": user.id
                },
                "body": message
            })
            # Fetch the conversationID.
            convoId = self.client.conversations.find_all(
                user_id=userId, type="user")[0].id
            context = codecs.encode(pickle.dumps(
                turn_context), "base64").decode()

            # Add user into db
            c.execute('INSERT INTO teams VALUES(?, ?, ?, ?)',
                      (userId, convoId, realName, context))
        else:
            # User already exists.
            # Fetch the conversation ID.
            c.execute("SELECT convoId FROM teams WHERE userId='"+userId+"';")
            convoId = c.fetchone()
            if(convoId != None):
                # If the conversation is active.
                convoId = convoId[0]
                self.client.conversations.reply(
                    id=convoId, type="user", user_id=userId, message_type="comment", body=message)
            else:
                # If the conversation has been archived.
                newMsg = self.client.messages.create(**{
                    "from": {
                        "type": "user",
                        "id": userId
                    },
                    "body": message
                })
                # Fetch the created conversation ID.
                convoId = self.client.conversations.find_all(
                    user_id=userId, type="user")[0].id
                # Update the database with the new conversation ID.
                c.execute("UPDATE teams SET convoId='" + convoId +
                          "' WHERE userId='" + userId + "';")
        conn.commit()
        conn.close()

    def gotMessage(self, userId, teamId, channelId, realName, email, message, fileUrls):
        """Pushes a message's contents and metadata to Intercom.

        Arguments:
            userId {string} -- The user's Slack ID.
            userName {string} -- The user's name.
            email {string} -- The user's email.
            message {string} -- The message itself.
            files {list} -- A list of attachment URLs.
        """

        files = list()
        # Catch to see if there is a link being sent.
        if (message.startswith("<http") and message.endswith(">") and len(message.split()) == 1):
            # Message is a solo link.
            message = "Link: " + message[1:-1]
        # Handling Files.
        if(len(fileUrls) > 0):
            # Check to see if only attachment was sent.
            if(len(message) == 0):
                message = "User sent attachment(s):"
            # There are files in the array.
            # Fetch the token to download files.
            token = tokens.getToken(teamId)
            for fileUrl in fileUrls:
                # For each file in the array,
                # Download the file.
                extension = os.path.splitext(fileUrl)[1]
                r = requests.get(fileUrl, headers={
                                 "Authorization": "Bearer " + token})
                fileName = str(uuid.uuid1()) + extension
                open("static/uploads/" + fileName, "wb").write(r.content)
                files.append(
                    "https://api.hirewells.com/static/uploads/" + fileName)
        # Opening the sqlite3 database.
        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        # Checking to see if there is already that user in the database.
        c.execute("SELECT * FROM users WHERE userId='" + userId + "';")
        user = None
        if(c.fetchall() == None):
            # If the user does not exist
            # Add a new user object to intercom.
            user = self.client.users.create(email=email, name=realName)
            # Set the user's source attribute.
            user.custom_attributes["Source"] = "Slack"
            self.client.users.save(user)
            # Send a message as the user.
            newMsg = self.client.messages.create(**{
                "from": {
                    "type": "user",
                    "id": user.id
                },
                "body": message,
                "attachment_urls": files
            })

            # Fetch the created conversation ID.
            convoId = self.client.conversations.find_all(
                email=email, type="user")[0].id

            # Add a new user to the database.
            print("Adding new user")
            c.execute("INSERT INTO users VALUES('" + userId + "','" + channelId + "','" +
                      teamId + "','" + convoId + "','" + realName + "','" + email + "');")
            conn.commit()
            # TODO: Send auto response back to Intercom.
            # Retrieving message text.
            with open("templates/auto_responses.json") as h:
                msg = json.load(h)["on_join_message"]
            # Creating new request.
            URL = "https://slack.com/api/chat.postMessage"
            # Crafting a data object to send to Slack.
            data = {
                "token": tokens.getToken(teamId),
                "channel": channelId,
                "text": msg
            }
            # Making the request.
            r = requests.post(url=URL, data=data)

            # Checking the status of the response.
            response = json.loads(r.text)
            success = response["ok"]
            if not success:
                raise errors.APIError(response)
            return success
        else:
            # If the user already exists.
            # Fetch the conversation ID.

            # Check if Admins are online.
            if not self.usersOnline():
                # If there are no users online
                # Retrieving message text.
                with open("templates/auto_responses.json") as h:
                    msg = json.load(h)["on_away_response"]
                # Creating new request.
                URL = "https://slack.com/api/chat.postMessage"
                # Crafting a data object to send to Slack.
                data = {
                    "token": tokens.getToken(teamId),
                    "channel": channelId,
                    "text": msg
                }
                # Making the request.
                r = requests.post(url=URL, data=data)

                # Checking the status of the response.
                response = json.loads(r.text)
                success = response["ok"]
                if not success:
                    raise errors.APIError(response)

            c.execute("SELECT convoId FROM users WHERE email='" + email + "';")
            convoId = c.fetchone()
            if(convoId != None):
                # If the conversation is active.
                convoId = convoId[0]
                self.client.conversations.reply(
                    id=convoId, type="user", email=email, message_type="comment", body=message, attachment_urls=files)
            else:
                # If the conversation has been archived.
                newMsg = self.client.messages.create(**{
                    "from": {
                        "type": "user",
                        "id": userId
                    },
                    "body": message,
                    "attachment_urls": files
                })
                # Fetch the created conversation ID.
                convoId = self.client.conversations.find_all(
                    email=email, type="user")[0].id
                # Update the database with the new conversation ID.
                c.execute("UPDATE users SET convoId='" + convoId +
                          "' WHERE email='" + email + "';")
        conn.commit()
        conn.close()

    def usersOnline(self):
        """Checks to see if any Intercom users are online.
        """
        for admin in self.client.admins.all():
            if(admin.email and not admin.email.startswith("operator+") and not admin.away_mode_enabled):
                print(admin.email + " " + str(admin.away_mode_enabled))
                return True
        return False
