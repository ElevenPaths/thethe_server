import traceback
import json
import time
import requests
import base64
from urllib.parse import urlparse


from server.entities.resource_types import ResourceType
from tasks.tasks import celery_app
from tasks.api_keys import KeyRing
from server.entities.plugin_manager import PluginManager
from server.entities.plugin_result_types import PluginResultStatus


# Which resources are this plugin able to work with
RESOURCE_TARGET = [ResourceType.URL]

# Plugin Metadata {a description, if target is actively reached and name}
PLUGIN_AUTOSTART = False
PLUGIN_DESCRIPTION = "Scan and analyse URLs"
PLUGIN_IS_ACTIVE = False
PLUGIN_DISABLE = False
PLUGIN_NAME = "urlscan"
PLUGIN_NEEDS_API_KEY = True

API_KEY = KeyRing().get("urlscan")
API_KEY_IN_DDBB = bool(API_KEY)
API_KEY_DOC = "https://urlscan.io/about-api/"
API_KEY_NAMES = ["urlscan"]

SUBMISSION_URL = "https://urlscan.io/api/v1/scan/"
RESULT_URL = "https://urlscan.io/api/v1/result/{uuid}/"

SCREENSHOTS_STORAGE_PATH = "/temp/urlscan/"
SCREENSHOTS_SERVER_PATH = "static/urlscan/"


class Plugin:
    def __init__(self, resource, project_id):
        self.project_id = project_id
        self.resource = resource

    def do(self):
        resource_type = self.resource.get_type()

        try:
            to_task = {
                "url": self.resource.get_data()["canonical_name"],
                "resource_id": self.resource.get_id_as_string(),
                "project_id": self.project_id,
                "resource_type": resource_type.value,
                "plugin_name": PLUGIN_NAME,
            }
            urlscan.delay(**to_task)

        except Exception as e:
            tb1 = traceback.TracebackException.from_exception(e)
            print("".join(tb1.format()))


def result(uuid):
    url_result_response = requests.get(RESULT_URL.format(**{"uuid": uuid}))
    if not url_result_response.status_code == 200:
        print("URL Result API error for uuid {}".format(uuid))
        return None
    return json.loads(url_result_response.content)


def urlscan_screenshot(url):
    try:
        screenshot_name = urlparse(url).path.split("/")[-1]
        r = requests.get(url, allow_redirects=True)
        with open(f"{SCREENSHOTS_STORAGE_PATH}{screenshot_name}", "wb") as f:
            f.write(r.content)
        return f"{SCREENSHOTS_SERVER_PATH}{screenshot_name}"

    except Exception as e:
        tb1 = traceback.TracebackException.from_exception(e)
        print("".join(tb1.format()))
        return None


@celery_app.task
def urlscan(plugin_name, project_id, resource_id, resource_type, url):
    result_status = PluginResultStatus.STARTED
    response = {}

    try:
        API_KEY = KeyRing().get("urlscan")
        if not API_KEY:
            print("No API key...!")
            result_status = PluginResultStatus.NO_API_KEY

        else:
            headers = {
                "Content-Type": "application/json",
                "API-Key": API_KEY,
            }
            data = {"url": url, "visibility": "public"}
            url_submission_response = requests.post(
                SUBMISSION_URL, headers=headers, json=data
            )
            if not url_submission_response.status_code == 200:
                print(
                    f"[urlscan.plugin] Request Error: {url_submission_response.content}"
                )
                result_status = PluginResultStatus.RETURN_NONE

            else:
                uuid = json.loads(url_submission_response.content)["uuid"]

                SLEEP_LIMIT = 300
                SLEEP_DELTA_INCREMENT = 2.5
                SLEEP_FRAME = 2
                # Número de reintentos cada 2 segundos
                while SLEEP_FRAME < SLEEP_LIMIT:
                    response = result(uuid)
                    if response is not None:
                        break
                    SLEEP_FRAME = round(SLEEP_FRAME * SLEEP_DELTA_INCREMENT)
                    time.sleep(SLEEP_FRAME)

                if response:
                    if response.get("message"):
                        # message means problems
                        result_status = PluginResultStatus.FAILED
                        print(f"[urlscan.plugin] {response}")
                    else:
                        result_status = PluginResultStatus.COMPLETED
                        task = response.get("task")
                        if task:
                            screenshot_url = task.get("screenshotURL")
                            if screenshot_url:
                                screenshot_name = urlscan_screenshot(screenshot_url)
                                if screenshot_name:
                                    response["screenshot"] = screenshot_name
                        response = base64.b64encode(
                            json.dumps(response).encode("ascii")
                        )

                else:
                    result_status = PluginResultStatus.RETURN_NONE

            PluginManager.set_plugin_results(
                resource_id, plugin_name, project_id, response, result_status
            )

    except Exception as e:
        tb1 = traceback.TracebackException.from_exception(e)
        print("".join(tb1.format()))
        return None
