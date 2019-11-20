
#!/usr/bin/env python3
import os
import json

""" Bot Configuration """

with open("config.json", "r") as h:
    config = json.load(h)
    h.close()

class DefaultConfig:
    """ Bot Configuration """

    config = config["teams"]

    PORT = config["PORT"]
    APP_ID = config["APP_ID"]
    APP_PASSWORD = config["APP_PASSWORD"]
