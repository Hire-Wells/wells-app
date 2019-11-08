"""
Intercom module.
Carlos Saucedo, 2019.
"""

from intercom.client import Client as intercomClient
import sqlite3
import pickle


class Client(object):
    def __init__(self, key):
        """An intercom client.
        Arguments:
            key {string} -- Intercom's access key. [More](https://app.intercom.com/a/apps/szdcciir/developer-hub/app-packages/41730/oauth)
        """
        self.client = intercomClient(personal_access_token=key)

    def gotTeamsMessage(self, turn_context):
        """Pushes a message from Teams to intercom.

        Arguments:
            context {TurnContext} -- The MS Teams context metadata.
        """
        # Fetching values
        userId = turn_context.activity.from_property.id
        realName = turn_context.activity.from_property.name
        message = turn_context.activity.text
        # Check to see if the user is in the database.
        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("SELECT * FROM teams WHERE userId='"+userId+"';")
        if(len(c.fetchone()) == 0):
            # User does not exist.
            # Add user to Intercom.
            user = self.client.users.create(id=userId, name=realName)
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
                id=userId, type="user")[0].id
            context = pickle.dump(turn_context)

            # Add user into db
            c.execute("INSERT INTO teams VALUES('"+userId+"','" +
                      convoId+"','"+realName+"','"+context+"');")
        else:
            # Fetch the conversation ID.
            c.execute("SELECT convoId FROM users WHERE userId='"+userId+"';")
            convoId = c.fetchone[0]
            if(convoId != None):
                # If the conversation is active.
                self.client.conversations.reply(
                    id=convoId, type="user", user_id=userId, message_type="comment", body=message)
            else:
                # If the conversation has been archived.
                #TODO: `user.id` doesn't exist in that scope?
                newMsg = self.client.messages.create(**{
                    "from": {
                        "type": "user",
                        "id": user.id
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
            c.execute("INSERT INTO users VALUES('" + userId + "','" + channelId + "','" +
                      teamId + "','" + convoId + "','" + realName + "','" + email + "');")
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
