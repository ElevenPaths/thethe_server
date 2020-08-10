import time
import json
import bson
import traceback

from server.db import DB
from server.entities.resource_manager import ResourceManager


AVAILABLE_COLORS = [
    "purple",
    "red",
    "pink",
    "orange",
    "indigo",
    "blue",
    "cyan",
    "green",
    "teal",
    "light-blue",
]

AVAILABLE_ICONS = [
    "android",
    "warning",
    "bug_report",
    "build",
    "dns",
    "extension",
    "favorite",
    "fingerprint",
    "help",
    "grade",
    "home",
    "http",
    "https",
    "info",
    "label",
    "language",
    "mediation",
    "lock_open",
    "pan_tool",
    "outlet",
    "payment",
    "query_builder",
    "print",
    "privacy_tip",
    "room",
    "search",
    "support",
    "verified",
    "verified_user",
    "visibility",
    "work",
    "videocam",
    "call",
    "sentiment_satisfied_alt",
    "vpn_key",
]


class TagManager:
    @staticmethod
    def get_tags():
        db = DB("tags")
        return db.collection.find({})

    @staticmethod
    def delete(tag_id):
        db = DB("tags")
        db.collection.delete_one({"_id": bson.ObjectId(tag_id)})
        ResourceManager.remove_tag(bson.ObjectId(tag_id))
        return (True, "Tag delete from system")

    @staticmethod
    def create(tag):
        tag_name = tag.get("name")
        tag_color = tag.get("color")
        tag_icon = tag.get("icon")

        if not tag_name.isalnum():
            return (False, "Tag name should included alphanum characters only")

        if not tag_color in AVAILABLE_COLORS:
            return (False, "Unknown tag color")

        if tag_icon and not tag_icon in AVAILABLE_ICONS:
            return (False, "Unknown tag icon")

        db = DB("tags")
        if db.collection.find_one({"name": tag_name}):
            return (False, "There is already a tag with this name")
        else:
            db.collection.insert_one(
                {"name": tag_name, "color": tag_color, "icon": tag_icon}
            )
            return (True, "Tag saved")

    @staticmethod
    def exists(tag):
        return tag in get_tags()
