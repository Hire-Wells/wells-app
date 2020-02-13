"""
Microsoft Teams integration module.
Carlos Saucedo, 2019
"""
from botbuilder.core import ActivityHandler, MessageFactory, TurnContext
from botbuilder.schema import ChannelAccount
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
        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                await turn_context.send_activity("Hello and welcome! Please let me know what I can help you with and a team of highly-experienced sourcers will contact you back as soon as possible.")

    async def on_message_activity(self, turn_context: TurnContext):
        userId = turn_context.activity.from_property.id
        realName = turn_context.activity.from_property.name
        self.intercom.gotTeamsMessage(turn_context)

    async def send_message(self, turn_context, msg):
        """Sends a message from Intercom to the Teams DM.

        Arguments:
            turn_context {TurnContext} -- The context to send the message to.
            msg {string} -- Message to send.
        """
        await turn_context.send_activity(msg)
