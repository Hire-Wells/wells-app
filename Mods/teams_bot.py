"""
Microsoft Teams integration module.
Carlos Saucedo, 2019
"""
from botbuilder.core import ActivityHandler, MessageFactory, TurnContext
from botbuilder.schema import ChannelAccount, Activity
import Mods.intercom
import json
import pickle
import sqlite3


class TeamsBot(ActivityHandler):
    def __init__(self, intercomToken):
        # Creating intercom client.
        self.intercom = Mods.intercom.Client(intercomToken)

    async def on_members_added_activity(
        self, members_added: [ChannelAccount], turn_context: TurnContext
    ):
        # Sending a welcome message.
        # Reading in the message text.
        with open("templates/auto_responses.json") as h:
            msg = json.load(h)["on_join_message"]
        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                await turn_context.send_activity(msg)

    async def on_message_activity(self, turn_context: TurnContext):
        """Runs when a message is sent from Teams to intercom.

        Args:
            turn_context (TurnContext): The message context.
        """
        # Send help information.
        if("help" in turn_context.activity.text.lower()):
            with open("templates/auto_responses.json") as h:
                msg = json.load(h)["on_help_response"]
            await turn_context.send_activity(msg)
        elif(not self.intercom.usersOnline()):
            with open("templates/auto_responses.json") as h:
                msg = json.load(h)["on_away_response"]
            await turn_context.send_activity(msg)
        else:
            with open("templates/auto_responses.json") as h:
                msg = json.load(h)["on_teams_response"]
            await turn_context.send_activity(msg)
        self.intercom.gotTeamsMessage(
            turn_context.activity, turn_context.get_conversation_reference(turn_context.activity))
