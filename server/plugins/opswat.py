# Put your Python standard libraries here, for instance:
# import sys
import json
import traceback

# Put your external dependencies here, for instance:
import requests

from tasks.tasks import celery_app
from server.entities.resource_types import ResourceType
from server.entities.plugin_result_types import PluginResultStatus
from server.entities.plugin_manager import PluginManager

url_details="https://api.metadefender.com/v4/hash/{}"

# Does your plugin need APIKEYS ?
# <------ APIKEYS -------->
from tasks.api_keys import KeyRing

# replace "YOUR_PLUGIN_NAME" with the name of your plugin
API_KEY = KeyRing().get("opswat")
API_KEY_IN_DDBB = bool(API_KEY)
# Put here the url of "how to get an apikey" instructions
API_KEY_DOC = "https://onlinehelp.opswat.com/mdcloud/"
# Put here the key part of the tuple: "key:value". Some sites required you to have one or two kinds of secret and apikeys. Most of all just need the "apikey:value" tuple
# API_KEY_NAMES = ["name_of_the_apikey", "name_of_the_secret"]
# In case of single values, just:
API_KEY_NAMES = ["opswat"]
#
# <------ /APIKEYS -------->
# If your plugin does not need APIKEYS just remove the last paragraph


# <------ RESOURCE_TARGET ------->

# What kind of resource can this plugin handle on?

# Choices are:

#     Resource.Type.DOMAIN
#     Resource.Type.HASH
#     Resource.Type.IPv4
#     Resource.Type.URL
#     Resource.Type.USERNAME
#     Resource.Type.EMAIL
#     Resource.Type.FILE

# Example, we are going to process information for DOMAINs and EMAILs:

RESOURCE_TARGET = [ResourceType.HASH]
# <------ /RESOURCE_TARGET ------->

# <------ PLUGIN IDENTIFICATION ------>

PLUGIN_NAME = "opswat"
PLUGIN_DESCRIPTION = "Opswat plugin "
# <------ /PLUGIN IDENTIFICATION ------>


# <------- PLUGIN CONFIGURATION ------->
# PLUGIN_IS_ACTIVE = True
#     Active as in launching probes. This is, your target will know you are knoing at their gates.
#  PLUGIN_AUTOSTART = False
#     If True, the plugin will be automatically ran when a new resource is added. Be careful with this if your API have a limited rate.
#  PLUGIN_DISABLE = False
#     If True, the plugin neither will be loaded nor will be shown in thethe.
#  PLUGIN_NEEDS_API_KEY = True
#     If True, the plugin needs an APIKEY to work, False otherwise
PLUGIN_IS_ACTIVE = False
PLUGIN_AUTOSTART = False
PLUGIN_DISABLE = False
PLUGIN_NEEDS_API_KEY = True

# <------- /PLUGIN CONFIGURATION ------->


class Plugin:
    def __init__(self, resource, project_id):
        self.project_id = project_id
        self.resource = resource

    def do(self):
        resource_type = self.resource.get_type()

        try:
            to_task = {
                "target": self.resource.get_data()["hash"],
                "resource_id": self.resource.get_id_as_string(),
                "project_id": self.project_id,
                "resource_type": resource_type.value,
                "plugin_name": PLUGIN_NAME,
            }
            hashdd.delay(**to_task)

        except Exception as e:
            tb1 = traceback.TracebackException.from_exception(e)
            print("".join(tb1.format()))


"""
    Main function.

        This is the function where all magic have to happen.

        If your plugin works in a different way for each resource type it
        handle do it like the snippet below.
hash

"""


@celery_app.task
def hashdd(plugin_name, project_id, resource_id, resource_type, target):
    try:
        if PLUGIN_NEEDS_API_KEY:
            result_status = PluginResultStatus.STARTED
            API_KEY = KeyRing().get("opswat")
            response = {}
            if not API_KEY:
                print("[opswat]No API key...!")
                result_status = PluginResultStatus.NO_API_KEY
            else:
                headers = {"apikey": API_KEY}
                print(target)
                query_result = requests.get(url_details.format(target),headers=headers)
                if not query_result.status_code == 200:
                    # if query_result.status_code == 404003:
                    #     response = json.loads(query_result.content)
                    #     result_status = PluginResultStatus.COMPLETED
                    #     PluginManager.set_plugin_results(resource_id, plugin_name, project_id, response, result_status)
                        
                    # print("[opswat]: Return non 200 code")
                    # print(query_result.content)
                    # resultado="{\"file_info\":{\"md5\":404003,\"file_size\":[\"The hash was not found\"]}}}"
                    # response = json.loads(query_result.content)

                    result_status = PluginResultStatus.RETURN_NONE
                    PluginManager.set_plugin_results(resource_id, plugin_name, project_id, response, result_status)


                else:
                    response = json.loads(query_result.content)
                    new_item_to_store = fix_dict(response, ignore_duplicate_key=True)
                    print( new_item_to_store)
                    result_status = PluginResultStatus.COMPLETED
                    PluginManager.set_plugin_results(resource_id, plugin_name, project_id,  new_item_to_store, result_status)

    except Exception as e:
        tb1 = traceback.TracebackException.from_exception(e)
        print("".join(tb1.format()))
        return None


def fix_dict(data, ignore_duplicate_key=True):
    """
    Removes dots "." from keys, as mongo doesn't like that.
    If the key is already there without the dot, the dot-value get's lost.
    This modifies the existing dict!

    :param ignore_duplicate_key: True: if the replacement key is already in the dict, now the dot-key value will be ignored.
                                 False: raise ValueError in that case.
    """
    if isinstance(data, (list, tuple)):
        list2 = list()
        for e in data:
            list2.append(fix_dict(e))
        # end if
        return list2
    if isinstance(data, dict):
        # end if
        for key, value in data.items():
            value = fix_dict(value)
            old_key = key
            if "." in key:
                key = old_key.replace(".", "")
                if key not in data:
                    data[key] = value
                else:
                    error_msg = "Dict key {key} containing a \".\" was ignored, as {replacement} already exists".format(
                        key=old_key, replacement=key)
                    # if force:
                    #     import warnings
                    #     warnings.warn(error_msg, category=RuntimeWarning)
                    # else:
                    #     raise ValueError(error_msg)
                    # end if
                # end if
                del data[old_key]
            # end if
            data[key] = value
        # end for
        return data
    # end if
    return data
# end def
