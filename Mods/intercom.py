"""
Intercom module.
Carlos Saucedo, 2019.
"""

from intercom.client import Client as intercomClient
import sqlite3


class Client(object):
    def __init__(self, key):
        """An intercom client.
        Arguments:
            key {string} -- Intercom's access key. [More](https://app.intercom.com/a/apps/szdcciir/developer-hub/app-packages/41730/oauth)
        """
        self.client = intercomClient(personal_access_token=key)

    def gotMessage(self, userId, teamId, channelId, realName, email, message):
        """Pushes a message's contents and metadata to Intercom.

        Arguments:
            userId {string} -- The user's Slack ID.
            userName {string} -- The user's name.
            email {string} -- The user's email.
            message {string} -- The message itself.
        """
        # Catch to see if there is a link being sent.
        if (message.startswith("<http") and message.endswith(">") and len(message.split()) == 1):
            # Message is a solo link.
            message = "Link: " + message[1:-1]
        # Opening the sqlite3 database.
        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        # Checking to see if there is already that user in the database.
        c.execute("SELECT * FROM users WHERE userId='" + userId + "';")
        user = None
        if(len(c.fetchall()) == 0):
            # If the user does not exist

            # Add a new user object to intercom.
            # Send a message as the user.
            user = self.client.users.create(email=email, name=realName)
            newMsg = self.client.messages.create(**{
                "from": {
                    "type": "user",
                    "id": user.id
                },
                "body": message
            })

            # Fetch the created conversation ID.
            convoId = self.client.conversations.find_all(
                email=email, type="user")[0].id

            # Add a new user to the database.
            c.execute("INSERT INTO users VALUES('" + userId + "','" + channelId + "','" + teamId + "','" + convoId + "','" + realName + "','" + email + "');")
            conn.commit()
        else:
            # If the user already exists.
            # Fetch the conversation ID.
            c.execute("SELECT convoId FROM users WHERE email='" + email + "';")
            convoId = c.fetchone()[0]
            if(convoId != None):
                # If the conversation is active.
                self.client.conversations.reply(
                    id=convoId, type="user", email=email, message_type="comment", body=message)
            else:
                # If the conversation has been archived.
                newMsg = self.client.messages.create(**{
                    "from": {
                        "type": "user",
                        "id": user.id
                    },
                    "body": message
                })
                # Fetch the created conversation ID.
                convoId = self.client.conversations.find_all(
                    email=email, type="user")[0].id
                # Update the database with the new conversation ID.
                c.execute("UPDATE users SET convoId='" + convoId +
                          "' WHERE email='" + email + "';")
                conn.commit()
        conn.close()
