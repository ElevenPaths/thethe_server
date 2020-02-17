import os
import importlib
import traceback
import pymongo
import time
import bson
import hashlib
import json
import difflib
import pprint

from server.db import DB
from server.entities.resource_types import ResourceType
from server.entities.plugin_result_types import PluginResultStatus
from server.entities.update_central import UpdateCentral


PLUGIN_DIRECTORY = "server/plugins/"
PLUGIN_HIERARCHY = "server.plugins"
EXCLUDE_SET = ["__init__.py", "TEMPLATE.py"]


def _get_module_names():
    """
        Get all the plugins names to load on
    """
    plugins = []
    for root, dirs, files in os.walk("server/plugins"):
        for file in files:
            if ".py" in file[-3:] and not file in EXCLUDE_SET:
                plugins.append("server.plugins.{}".format(os.path.splitext(file)[0]))
    return plugins


def register_plugins():
    """
        This function register metadata from enabled plugins upon container startup
    """
    db = DB("plugins")
    db.collection.delete_many({})

    for module in _get_module_names():
        module = importlib.import_module(module)
        if not module.PLUGIN_DISABLE:
            print(f"registering {module.PLUGIN_NAME}")
            db.collection.insert_one(
                {
                    "name": module.PLUGIN_NAME,
                    "is_active": module.PLUGIN_IS_ACTIVE,
                    "description": module.PLUGIN_DESCRIPTION,
                    "autostart": module.PLUGIN_AUTOSTART,
                    "target": [resource.value for resource in module.RESOURCE_TARGET],
                    "needs_apikey": module.PLUGIN_NEEDS_API_KEY,
                    "apikey_in_ddbb": module.API_KEY_IN_DDBB,
                    "apikey_doc": module.API_KEY_DOC,
                    "apikey_names": module.API_KEY_NAMES,
                }
            )


def _load_module(plugin_name):
    try:
        module = importlib.import_module(f"{PLUGIN_HIERARCHY}.{plugin_name}")
        return module

    except Exception as e:
        print(f"[_load_module] {e}")
        tb1 = traceback.TracebackException.from_exception(e)
        print("".join(tb1.format()))


class PluginManager:
    @staticmethod
    def get_plugin_names():
        try:
            db = DB("plugins")
            plugins = db.collection.find({"needs_apikey": True})

            non_apikeys_fields = []
            for plugin in plugins:
                non_apikeys_fields.extend(plugin["apikey_names"])

            db = DB("apikeys")
            apikeys = [apikey["name"] for apikey in db.collection.find({})]

            non_apikeys_fields = set(non_apikeys_fields) - set(apikeys)

            return list(non_apikeys_fields)

        except Exception as e:
            print(f"[PluginManager.get_plugin_names] {e}")
            tb1 = traceback.TracebackException.from_exception(e)
            print("".join(tb1.format()))

    @staticmethod
    def get_autostart_plugins_for_resource(resource_type_as_string):
        try:
            db = DB("plugins")
            plugins = db.collection.find(
                {"autostart": True, "target": resource_type_as_string}
            )
            return [plugin["name"] for plugin in plugins]

        except Exception as e:
            print(f"[PluginManager.get_autostart_plugins_for_resource] {e}")
            tb1 = traceback.TracebackException.from_exception(e)
            print("".join(tb1.format()))

    @staticmethod
    def get_plugins_for_resource(resource_type_as_string):
        db = DB("plugins")
        plugins = db.collection.find({"target": resource_type_as_string}).sort(
            [("name", pymongo.ASCENDING)]
        )
        results = []
        for entry in plugins:
            results.append(
                {
                    "name": entry["name"],
                    "description": entry["description"],
                    "api_key": entry["needs_apikey"],
                    "api_docs": entry["apikey_doc"],
                    "is_active": entry["is_active"],
                    "apikey_in_ddbb": entry["apikey_in_ddbb"],
                }
            )
        return results

    @staticmethod
    def get_plugins_names_for_resource(resource_type_as_string):
        db = DB("plugins")
        plugins = db.collection.find({"target": resource_type_as_string}).sort(
            [("name", pymongo.ASCENDING)]
        )
        results = []
        for entry in plugins:
            results.append(entry["name"])
        return results

    def __init__(self, resource, project_id):
        self.resource = resource
        self.project_id = project_id

    # TODO: Profiles are not implemented yet (11/02/2020)
    def launch_all(self, profile="pasive"):
        """
            Launch all the loaded plugins based on a profile (by default non active or noisy modules)
        """
        try:
            plugins = PluginManager.get_autostart_plugins_for_resource(
                self.resource.get_type_value()
            )
            name_list = " ".join(plugins)
            print(
                f"[PluginManager.launch_all]: Launching autostart plugins...{name_list}"
            )

            for plugin in plugins:
                module = _load_module(plugin)
                module.Plugin(self.resource, self.project_id).do()

        except Exception as e:
            print(f"[PluginManager.launch_all] {e}")
            tb1 = traceback.TracebackException.from_exception(e)
            print("".join(tb1.format()))

    def launch(self, plugin_name):
        try:
            module = _load_module(plugin_name)
            print(f"Launching {module.PLUGIN_NAME}")
            return module.Plugin(self.resource, self.project_id).do()

        except Exception as e:
            print(f"[PluginManager.launch] {e}")
            tb1 = traceback.TracebackException.from_exception(e)
            print("".join(tb1.format()))

    @staticmethod
    def set_plugin_results(
        resource_id,
        plugin_name,
        project_id,
        query_result,
        result_status=PluginResultStatus.COMPLETED,
    ):

        db = DB(plugin_name)

        # By default, we are inserting a new plugin result
        insert_new_one = True

        # Get the lastest document in the plugin collection for this resource
        last_document = (
            db.collection.find({"resource_id": bson.ObjectId(resource_id)})
            .sort([("_id", -1)])
            .limit(1)
        )

        # HACK: There is no "count" or "length" method in pymongo Cursor
        # Let's see if the new one is just the same as the last stored result
        last_document = list(last_document)
        if not len(last_document) == 0:
            last_document = last_document[0]

            md5_left = hashlib.md5()
            md5_left.update(str(last_document["results"]).encode("utf-8"))
            last_document_hexdigest = md5_left.hexdigest()
            print(last_document_hexdigest)

            md5_right = hashlib.md5()
            md5_right.update(str(query_result).encode("utf-8"))
            query_result_hexdigest = md5_right.hexdigest()
            print(query_result_hexdigest)

            # Result still the same, just update timestamp
            if last_document_hexdigest == query_result_hexdigest:
                db.collection.update_one(
                    {"_id": bson.ObjectId(last_document["_id"])},
                    {"$set": {"timestamp": time.time()}},
                )
                insert_new_one = False
                result_status = PluginResultStatus.JUST_UPDATED

            # This is a new result
            else:
                insert_new_one = True

        # In any case, a new result must be stored
        if insert_new_one:
            db.collection.insert_one(
                {
                    "results": query_result,
                    "timestamp": time.time(),
                    "resource_id": bson.ObjectId(resource_id),
                    "result_status": result_status.value,
                }
            )

        UpdateCentral().set_pending_update(
            project_id, resource_id, plugin_name, result_status,
        )

    @staticmethod
    def get_diff(plugin_name, resource_id, index):
        try:
            db = DB(plugin_name)
            if db:
                result_set = db.collection.find(
                    {"resource_id": bson.ObjectId(resource_id)}
                ).sort([("timestamp", pymongo.DESCENDING)])

                result_set = list(result_set)

                left = json.dumps(
                    result_set[0]["results"], indent=4, sort_keys=True
                ).split("\n")

                right = json.dumps(
                    result_set[index]["results"], indent=4, sort_keys=True
                ).split("\n")

            if left and right:
                diff = difflib.unified_diff(left, right)
                return "\n".join(diff)

            return None

        except Exception as e:
            print(f"[PluginManager.get_diff] {e}")
            tb1 = traceback.TracebackException.from_exception(e)
            print("".join(tb1.format()))
            return None
