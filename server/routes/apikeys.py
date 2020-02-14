import time
import bson
import json
import traceback

from bson.json_util import dumps
from flask import Blueprint, request, abort, jsonify

from server.db import DB
from server.utils.password import token_required

apikeys_api = Blueprint("apikeys", __name__)


@apikeys_api.route("/api/get_apikeys", methods=["POST"])
@token_required
def get_apikeys(user):
    try:
        results = DB("apikeys").collection.find({}, {"_id": False})
        list_results = list(results)

        return dumps(list_results)

    except Exception as e:
        print(e)
        return jsonify({"error_message": "Error getting API keys"}), 400


@apikeys_api.route("/api/upload_apikeys", methods=["POST"])
@token_required
def upload_apikeys(user):
    try:
        apikeys = request.json["entries"]
        for apikey in apikeys:
            result = DB("apikeys").collection.update_one(
                {"name": apikey["name"]},
                {"$set": {"apikey": apikey["apikey"]}},
                upsert=True,
            )

            # Also updating "plugins" metadata
            plugins = DB("plugins")
            plugin = plugins.collection.update_one(
                {"apikey_names": apikey["name"]}, {"$set": {"apikey_in_ddbb": True}}
            )

        return json.dumps(apikeys, default=str)

    except Exception as e:
        print(f"[routes/apikeys.upload_apikeys]: {e}")
        tb1 = traceback.TracebackException.from_exception(e)
        print("".join(tb1.format()))
        return jsonify({"error_message": "Error uploading API keys"}), 400


@apikeys_api.route("/api/remove_apikeys", methods=["POST"])
@token_required
def remove_apikeys(user):
    try:
        apikeys = request.json["entries"]
        for name in apikeys:
            result = DB("apikeys").collection.remove({"name": name["name"]})

            # Also updating "plugins" metadata
            plugins = DB("plugins")
            plugin = plugins.collection.update_one(
                {"apikey_names": name["name"]}, {"$set": {"apikey_in_ddbb": False}}
            )

        return json.dumps(apikeys, default=str)

    except Exception as e:
        print(f"[routes/apikeys.remove_apikeys]: {e}")
        tb1 = traceback.TracebackException.from_exception(e)
        print("".join(tb1.format()))
        return jsonify({"error_message": "Error removing API keys"}), 400
