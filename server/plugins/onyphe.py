import json
import traceback
import json
import requests

from tasks.api_keys import KeyRing
from server.entities.plugin_manager import PluginManager
from server.entities.resource_types import ResourceType
from tasks.tasks import celery_app
from server.entities.plugin_result_types import PluginResultStatus


# Which resources are this plugin able to work with
RESOURCE_TARGET = [ResourceType.IPv4, ResourceType.DOMAIN]

# Plugin Metadata {a description, if target is actively reached and name}
PLUGIN_AUTOSTART = False
PLUGIN_DESCRIPTION = (
    "Lookup onyphe.io wether this IP or Domain is included in threatlists"
)
PLUGIN_IS_ACTIVE = False
PLUGIN_DISABLE = False
PLUGIN_NAME = "onyphe"
PLUGIN_NEEDS_API_KEY = True

API_KEY = KeyRing().get("onyphe")
API_KEY_IN_DDBB = bool(API_KEY)
API_KEY_DOC = "https://www.onyphe.io/documentation/api"
API_KEY_NAMES = ["onyphe"]


class Plugin:
    def __init__(self, resource, project_id):
        self.project_id = project_id
        self.resource = resource

    def do(self):
        resource_type = self.resource.get_type()

        try:
            to_task = {
                "resource": self.resource.get_data()["canonical_name"],
                "resource_id": self.resource.get_id_as_string(),
                "project_id": self.project_id,
                "resource_type": resource_type.value,
                "plugin_name": PLUGIN_NAME,
            }
            onyphe.delay(**to_task)

        except Exception as e:
            tb1 = traceback.TracebackException.from_exception(e)
            print("".join(tb1.format()))


@celery_app.task
def onyphe(plugin_name, project_id, resource_id, resource_type, resource):
    result_status = PluginResultStatus.STARTED
    query_result = None

    try:
        API_KEY = KeyRing().get("onyphe")
        if not API_KEY:
            print("No API key...!")
            result_status = PluginResultStatus.NO_API_KEY

        else:
            url = ""
            headers = {
                "Authorization": f"apikey {API_KEY}",
                "Content-Type": "application/json",
            }

            if resource_type == "domain":
                url = f"https://www.onyphe.io/api/v2/summary/domain/{resource}"
            elif resource_type == "ip":
                url = f"https://www.onyphe.io/api/v2/summary/ip/{resource}"

            query_result = requests.get(url, headers=headers)

            if query_result.status_code == 200:
                json_results = query_result.json()

                if json_results["results"] == []:
                    result_status = PluginResultStatus.RETURN_NONE
                else:
                    query_result = json_results["results"]
                    result_status = PluginResultStatus.COMPLETED

            else:
                result_status = PluginResultStatus.FAILED

        PluginManager.set_plugin_results(
            resource_id, plugin_name, project_id, query_result, result_status
        )

    except Exception as e:
        tb1 = traceback.TracebackException.from_exception(e)
        print("".join(tb1.format()))
