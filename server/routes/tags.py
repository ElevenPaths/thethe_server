import time
import bson
import json
import traceback
import urllib.parse


from flask import Blueprint, request, abort, jsonify

from server.utils.password import token_required

from server.entities.resource_manager import ResourceManager
from server.entities.resource_types import ResourceType, ResourceTypeException
from server.entities.user import User

from server.entities.tag_manager import TagManager, AVAILABLE_COLORS, TagErrors

tags_api = Blueprint("tags", __name__)


@tags_api.route("/api/get_tags", methods=["POST"])
@token_required
def get_tags(user):
    try:
        tags_list = TagManager().get_tags()
        result = {"tags": json.loads(json.dumps(tags_list, default=str))}
        return jsonify(result)

    except Exception as e:
        print(e)
        return jsonify({"error_message": "Error getting global tags"}), 400


@tags_api.route("/api/add_new_tag", methods=["POST"])
@token_required
def add_new_tag(user):
    try:
        name = request.json["tag"]["name"]
        color = request.json["tag"]["color"]

        results = TagManager().new({"name": name, "color": color})

        if results == TagErrors.NONE:
            return jsonify({"done": True, "message": f"Tag {name} created"})

        elif results == TagErrors.NAME_NOT_COMPLIANT:
            return jsonify(
                {
                    "done": False,
                    "message": "Name should be only alphanumeric, all lowercase",
                },
            )

        elif results == TagErrors.ALREADY_EXISTS:
            return jsonify({"done": False, "message": f"Tag {name} already exists"})

        elif results == TagErrors.COLOR_NOT_COMPLIANT:
            return jsonify({"done": False, "message": "Unknown color"})

    except Exception as e:
        print(e)
        return jsonify({"done": False, "message": "Error adding new tag"})


@tags_api.route("/api/update_tag", methods=["POST"])
@token_required
def update_tag(user):
    try:

        pass
    except Exception as e:
        print(e)
        return (
            jsonify({"error_message": "Something gone wrong when getting paste"}),
            400,
        )


@tags_api.route("/api/get_tag_colors", methods=["POST"])
@token_required
def get_tag_colors(user):
    try:
        tag_colors = {"tag_colors": AVAILABLE_COLORS}
        return jsonify(tag_colors)

    except Exception as e:
        print(e)
        return jsonify({"error_message": "Error getting global tags"}), 400


@tags_api.route("/api/add_tag", methods=["POST"])
@token_required
def add_tag(user):
    try:
        resource_id = bson.ObjectId(request.json["params"]["resource_id"])
        tag = request.json["params"]["tag"]

        if TagManager().exists(tag):
            resource = ResourceManager.get(resource_id)

            if resource.add_tag(tag):
                return jsonify(
                    {"done": True, "message": f"Tag {tag['name']} added to resource"}
                )

            else:
                jsonify(
                    {
                        "done": False,
                        "message": "Cannot add this tag to the selected resource",
                    }
                )

        return jsonify({"done": False, "message": "Error adding new tag"})

    except Exception as e:
        tb1 = traceback.TracebackException.from_exception(e)
        print("".join(tb1.format()))
        return jsonify({"error_message": "Error adding tag"}), 400


@tags_api.route("/api/remove_tag", methods=["POST"])
@token_required
def remove_tag(user):
    try:
        resource_id = bson.ObjectId(request.json["params"]["resource_id"])
        tag = request.json["params"]["tag"]

        if TagManager().exists(tag):
            resource = ResourceManager.get(resource_id)

            if resource.remove_tag(tag):
                return jsonify(
                    {
                        "done": True,
                        "message": f"Tag {tag['name']} removed from resource",
                    }
                )

            else:
                jsonify(
                    {
                        "done": False,
                        "message": "Cannot remove this tag on the selected resource",
                    }
                )

        return jsonify({"done": False, "message": "Error removing new tag"})

    except Exception as e:
        tb1 = traceback.TracebackException.from_exception(e)
        print("".join(tb1.format()))
        return jsonify({"error_message": "Error removing tag"}), 400
