import traceback
import os
import json


import tasks.deps.sherlock.sherlock.sherlock as _sherlock
from tasks.deps.sherlock.sherlock.notify import QueryNotifyPrint

from server.entities.resource_types import ResourceType
from tasks.tasks import celery_app
from server.entities.plugin_manager import PluginManager
from server.entities.plugin_result_types import PluginResultStatus


# Which resources are this plugin able to work with
RESOURCE_TARGET = [ResourceType.USERNAME]

# Plugin Metadata {a description, if target is actively reached and name}
PLUGIN_DESCRIPTION = "Use Sherlock to find usernames across many social networks"
PLUGIN_NEEDS_API_KEY = False
PLUGIN_IS_ACTIVE = False
PLUGIN_NAME = "sherlock"
PLUGIN_AUTOSTART = False
PLUGIN_DISABLE = False

API_KEY = False
API_KEY_IN_DDBB = False
API_KEY_DOC = ""
API_KEY_NAMES = []


class Plugin:
    description = PLUGIN_DESCRIPTION
    is_active = PLUGIN_IS_ACTIVE
    name = PLUGIN_NAME
    api_key = PLUGIN_NEEDS_API_KEY
    api_doc = ""
    autostart = PLUGIN_AUTOSTART
    apikey_in_ddbb = bool(API_KEY)

    def __init__(self, resource, project_id):
        self.project_id = project_id
        self.resource = resource

    def do(self):
        resource_type = self.resource.get_type()

        try:
            to_task = {
                "username": self.resource.get_data()["canonical_name"],
                "resource_id": self.resource.get_id_as_string(),
                "project_id": self.project_id,
                "resource_type": resource_type.value,
                "plugin_name": PLUGIN_NAME,
            }
            sherlock.delay(**to_task)

        except Exception as e:
            tb1 = traceback.TracebackException.from_exception(e)
            print("".join(tb1.format()))


@celery_app.task
def sherlock(username, plugin_name, project_id, resource_id, resource_type):

    response = []
    result_status = PluginResultStatus.STARTED

    try:
        site_data_all = None
        data_file_path = os.path.join(
            os.getcwd(),
            "tasks",
            "deps",
            "sherlock",
            "sherlock",
            "resources",
            "data.json",
        )

        if site_data_all is None:
            # Check if the file exists otherwise exit.
            if not os.path.exists(data_file_path):
                print("JSON file at doesn't exist.")
                print(
                    "If this is not a file but a website, make sure you have appended http:// or https://."
                )
                return None
            else:
                raw = open(data_file_path, "r", encoding="utf-8")
                try:
                    site_data_all = json.load(raw)
                except:
                    print("Invalid JSON loaded from file.")

        result = _sherlock.sherlock(username, site_data_all, QueryNotifyPrint(),)

        for site, result in result.items():

            temp_result = {}

            temp_result["sitename"] = site
            temp_result["url_user"] = result.get("url_user")
            temp_result["exists"] = (
                "yes" if str(result["status"]) == "Claimed" else "no"
            )

            response.append(temp_result)

        if response:
            result_status = PluginResultStatus.COMPLETED
        else:
            result_status = PluginResultStatus.RETURN_NONE

        PluginManager.set_plugin_results(
            resource_id, plugin_name, project_id, response, result_status
        )

    except Exception as e:
        tb1 = traceback.TracebackException.from_exception(e)
        print("".join(tb1.format()))
        return None
