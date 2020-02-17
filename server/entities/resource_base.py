import traceback
import json
import bson
import pymongo
import time
import urllib.parse


from server.db import DB
from server.entities.plugin_manager import PluginManager
from server.entities.plugin_result_types import PluginResultStatus
from server.entities.update_central import UpdateCentral
from server.entities.resource_types import ResourceType
from server.entities.hash_types import HashType

COLLECTION = "resources"
LIMIT_OF_TIMEMACHINE_RESULTS = 5

# TODO: Legacy method for old database resources
# TODO: Get rid of this legacy method
def get_resource_legacy_method(resource_id):
    """
        Lookup the resource_id in all old documents
        Returns resource and doc name to change global COLLECTION
    """

    print(
        f"[resource_base.get_resource_legacy_method]: Legacy method called looking for resource {resource_id}"
    )

    docs = ["ip", "url", "username", "hash", "email", "domain"]

    for doc in docs:
        collection = DB(doc).collection
        resource = collection.find_one({"_id": resource_id})

        if resource:
            return (resource, doc)

    print(f"[resource_base/get_resource_legacy_method]: {resource_id}")

    return (None, None)


# TODO: This is calling for trouble. We need to have a proper hierarchy to handle diferent ENTITIES
def enrich_by_type(args):
    resource_type = ResourceType(args["resource_type"])

    if resource_type == ResourceType.IPv4:
        args["address"] = args["canonical_name"]

    elif resource_type == ResourceType.USERNAME:
        args["username"] = args["canonical_name"]

    elif resource_type == ResourceType.URL:
        args["full_url"] = args["canonical_name"]

        url_parts = urllib.parse.urlparse(args["full_url"])
        args["scheme"] = url_parts.scheme
        args["netloc"] = url_parts.netloc
        args["path"] = url_parts.path
        args["params"] = url_parts.params
        args["query"] = url_parts.query
        args["fragment"] = url_parts.fragment

    elif resource_type == ResourceType.HASH:
        args["hash"] = args["canonical_name"]
        args["hash_type"] = HashType.hash_detection(args["hash"]).value
        # canonical_name == printable name in the view
        args["canonical_name"] = args["hash"][:8]

    elif resource_type == ResourceType.EMAIL:
        args["email"] = args["canonical_name"]
        if "@" in args["email"]:
            args["domain"] = args["email"].split("@")[1]
        else:
            args["domain"] = None

    elif resource_type == ResourceType.DOMAIN:
        args["domain"] = args["canonical_name"]

    else:
        print(
            f"[entities/resource_base/enrich_by_type]: Unknown resource type {args['resource_type']} when creating resource."
        )

    return args


class Resource:
    @staticmethod
    def collection(collection=COLLECTION):
        return DB(collection).collection

    @staticmethod
    def create(name, resource_type):
        """
            name: name of the resource
            type: type as ResourceType
        """
        args = {
            "canonical_name": name,
            "resource_type": resource_type.value,
            "creation_time": time.time(),
            "plugins": [],
            "tags": [],
        }

        args = enrich_by_type(args)
        result = Resource.collection().insert_one(args)
        print(f"Creating new resource with {args}")
        return Resource(str(result.inserted_id))

    def __init__(self, resource_id):
        self.resource_id = bson.ObjectId(resource_id)
        collection = COLLECTION
        self.resource = Resource.collection(collection).find_one(
            {"_id": self.resource_id}
        )
        # TODO: Get rid of this legacy method
        # We have not found anything, try legacy database method
        if not self.resource:
            # If found, change global resource database
            self.resource, collection = get_resource_legacy_method(self.resource_id)

        # Store collection name
        self.own_collection = collection

    def get_collection(self):
        return Resource.collection(self.own_collection)

    def get_id_as_string(self):
        return str(self.resource_id)

    def get_type(self):
        return ResourceType.get_type_from_string(self.resource["resource_type"])

    def get_type_value(self):
        return self.get_type().value

    def get_data(self):
        return self.resource

    def launch_plugins(self, project_id, profile=None):
        try:
            PluginManager(self, project_id).launch_all()

        except Exception as e:
            tb1 = traceback.TracebackException.from_exception(e)
            print("".join(tb1.format()))

    def launch_plugin(self, project_id, plugin_name, profile=None):
        try:
            return PluginManager(self, project_id).launch(plugin_name)

        except Exception as e:
            tb1 = traceback.TracebackException.from_exception(e)
            print("".join(tb1.format()))

    def set_plugin_results(
        self,
        plugin_name,
        project_id,
        query_result,
        result_status=PluginResultStatus.COMPLETED,
    ):

        PluginManager.set_plugin_results(
            self.resource_id, plugin_name, project_id, query_result, result_status
        )

    def manage_tag(self, tag):
        try:
            resource = self.get_collection().find_one({"_id": self.resource_id})

            if "tags" in resource:
                if tag["name"] in [t["name"] for t in resource["tags"]]:
                    resource["tags"] = [
                        t for t in resource["tags"] if not t["name"] == tag["name"]
                    ]
                else:
                    resource["tags"].append(
                        {"name": tag["name"], "color": tag["color"]}
                    )
            else:
                resource["tags"] = [tag]

            self.get_collection().replace_one({"_id": self.resource_id}, resource)

        except Exception as e:
            tb1 = traceback.TracebackException.from_exception(e)
            print("".join(tb1.format()))

    def to_JSON(self, timestamp_index=0):
        """
            Get the doc from DB and returns a JSON without the ObjectId
            Client must JSON.parse() it in browser before passing it to Vuex
        """

        # Doc is this resource json itself
        doc = self.resource

        # Needed because FE expect it to be there
        doc["plugins"] = []

        # We need how many plugins can deal with this current resource type
        plugins_names = PluginManager.get_plugins_names_for_resource(
            self.get_type_value()
        )

        # Scan for results in all plugins resource type related
        for plugin_name in plugins_names:
            result_cursor = (
                DB(plugin_name)
                .collection.find(
                    {"resource_id": self.resource_id, "results": {"$exists": True},}
                )
                .sort([("timestamp", pymongo.DESCENDING)])
            )

            result_cursor = list(result_cursor)
            if not len(result_cursor) == 0:
                # Test timestamp index
                if timestamp_index < 0 or timestamp_index > len(result_cursor) - 1:
                    result = result_cursor[0]
                else:
                    result = result_cursor[timestamp_index]

                # Add name of the plugin, because we do not store it in database
                result["name"] = plugin_name

                # If this plugin results is a list of external references (case pastebin), load it:
                _load_external_results(result)

                # Load all timemachine timestamps
                timemachine = []

                # Add the last LIMIT_OF_TIMEMACHINE_RESULTS timestamps to timemachine
                for ts in result_cursor:
                    timemachine.append(
                        {
                            "timestamp": ts["timestamp"],
                            "result_status": ts["result_status"],
                        }
                    )

                # Plug timemachine results in our plugin results
                result["timemachine"] = timemachine

                # Plug this plugin results to doc
                doc["plugins"].append(result)

        return json.loads(json.dumps(doc, default=str))

    # Get the complete document from a valid bson string reference


def _load_external_results(plugin):
    if "results" in plugin and isinstance(plugin["results"], list):
        plugin["results"] = [
            _get_doc_if_reference(plugin["name"], entry) for entry in plugin["results"]
        ]


def _get_doc_if_reference(plugin_name, entry):
    if bson.ObjectId.is_valid(entry):
        entry = DB(plugin_name + "s").collection.find_one(
            {"_id": entry}, {"content": 0}
        )
    return entry
