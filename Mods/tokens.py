"""
Token fetching module for Wells.
Carlos Saucedo, 2019
"""

import sqlite3

def getToken(teamId):
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT botAccessToken FROM tokens WHERE teamId='" + teamId + "';")
    token = c.fetchall()[0][0]
    conn.close()
    return token