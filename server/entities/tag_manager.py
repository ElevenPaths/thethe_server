import time
import json

from enum import Enum

from server.db import DB

AVAILABLE_COLORS = [
    "blue",
    "cyan",
    "green",
    "orange",
    "pink",
    "purple",
    "red",
    "yellow",
]


class Tag:
    def __init__(self, name, color, icon=False, is_system=False):
        self.name = name
        self.color = color
        self.is_system = is_system
        self.icon = icon


system_tags = [
    {"name": "apk", "color": "green", "icon": "android"},
    {"name": "malware", "color": "red", "icon": "mdi-biohazard"},
    {"name": "phishing", "color": "red", "icon": "mdi-hook"},
    {"name": "spammer", "color": "orange", "icon": "mdi-email-send-outline"},
    {"name": "maldoc", "color": "blue", "icon": "mdi-biohazard"},
    {"name": "crypto-currency", "color": "amber darken-1", "icon": "mdi-bitcoin"},
    {"name": "cert", "color": "amber darken-1", "icon": "mdi-certificate"},
    # Services
    {"name": "dns", "color": "blue", "icon": "mdi-dns"},
    {"name": "www", "color": "blue", "icon": "mdi-web"},
    {"name": "ssh", "color": "blue", "icon": "mdi-console"},
]


class TagErrors(Enum):
    NONE = (0,)
    ALREADY_EXISTS = (1,)
    NAME_NOT_COMPLIANT = (2,)
    COLOR_NOT_COMPLIANT = 3


class TagManager:
    def __init__(self):
        self.db = DB("tags")

    def get_tags(self):
        results = self.db.collection.find({})
        return [
            {"name": result["name"], "color": result["color"]} for result in results
        ]

    def delete(self, name):
        self.db.collection.delete_one({"name": name})

    def new(self, tag):
        tag["name"] = tag["name"].lower()

        if not tag["name"].isalnum():
            return TagErrors.NAME_NOT_COMPLIANT

        if not tag["color"] in AVAILABLE_COLORS:
            return TagErrors.COLOR_NOT_COMPLIANT

        if not self.db.collection.find_one({"name": tag["name"]}):
            self.db.collection.insert_one({"name": tag["name"], "color": tag["color"]})
            return TagErrors.NONE

        else:
            return TagErrors.ALREADY_EXISTS

    def update(self, old_name, new_tag):
        self.db.collection.update_one(
            {"name": old_name}, {"name": new_tag["name"], "color": new_tag["color"]}
        )

    def exists(self, tag):
        return tag in self.get_tags()
