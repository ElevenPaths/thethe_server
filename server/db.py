import traceback
import time
import bson

from pymongo import MongoClient
from server.entities.plugin_result_types import PluginResultStatus

DATABASE_SCHEME_VERSION = 0.6


class DB:
    def __init__(self, collection):
        self.client = MongoClient("mongodb://root:root@mongo:27017/")
        self.db = self.client.get_database("thethe")
        self.collection = self.db.get_collection(collection)

    def __del__(self):
        self.client.close()


def check_database_version():
    """
        Check if database needs a migration
    """
    db = DB("version")
    version = db.collection.find_one({})
    if not version:
        db.collection.insert_one({"version": DATABASE_SCHEME_VERSION})
        return True

    elif version["version"] < DATABASE_SCHEME_VERSION:
        return True

    else:
        return False


def _move_plugin_results_outside(db_name):
    print(
        f"[db._move_plugin_results_outside]: Migrating {db_name} resources plugin results"
    )
    try:
        db = DB(db_name)
        for doc in db.collection.find({}):
            if "plugins" in doc:
                for plugin in doc["plugins"]:
                    plugin_db = DB(plugin["name"])

                    try:
                        plugin_db.collection.insert_one(
                            {
                                "resource_id": bson.ObjectId(doc["_id"]),
                                "result_status": PluginResultStatus.COMPLETED.value,
                                "results": plugin["results"],
                                "timestamp": plugin["update_time"]
                                if "update_time" in plugin
                                else time.time(),
                            }
                        )
                    except Exception as e:
                        print(f"[db._move_plugin_results_outside::for] {e}")
                        tb1 = traceback.TracebackException.from_exception(e)
                        print("".join(tb1.format()))
                        continue

        # Delete all "plugins" arrays
        db.collection.update_many({}, {"$unset": {"plugins": ""}})

    except Exception as e:
        print(f"[db._move_plugin_results_outside] {e}")
        tb1 = traceback.TracebackException.from_exception(e)
        print("".join(tb1.format()))


def _move_resources_into_resources_collection(db_name):
    try:
        db = DB(db_name)
        docs = db.collection.find({})

        db = DB("resources")
        for doc in docs:
            try:
                db.collection.insert_one(doc)
            except Exception as e:
                print(f"[db._move_resources_into_resources_collection] {e}")
                tb1 = traceback.TracebackException.from_exception(e)
                print("".join(tb1.format()))
                continue

        # Delete all "plugins" arrays
        db.collection.update_many({}, {"$unset": {"plugins": ""}})

    except Exception as e:
        print(f"[db._move_resources_into_resources_collection] {e}")
        tb1 = traceback.TracebackException.from_exception(e)
        print("".join(tb1.format()))


def _remove_unneeded_collection(resource):
    try:
        db = DB(resource)
        db.collection.drop()
    except Exception as e:
        print(f"[db._remove_unneeded_collection] {e}")
        tb1 = traceback.TracebackException.from_exception(e)
        print("".join(tb1.format()))


def migrate_database():
    # First look into the resources collection to move the plugins outside
    _move_plugin_results_outside("resources")

    # Put resources in "resource" collection
    OLD_RESOURCES = ["ip", "domain", "url", "username", "hash", "email"]

    for resource in OLD_RESOURCES:
        _move_plugin_results_outside(resource)
        _move_resources_into_resources_collection(resource)
        _remove_unneeded_collection(resource)

    # Push version number
    db = DB("version")
    version = db.collection.update_one(
        {}, {"$set": {"version": DATABASE_SCHEME_VERSION}}, upsert=True
    )
