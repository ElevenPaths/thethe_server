import traceback
import json

from flask import Blueprint, request, jsonify

from server.entities.user import UsersManager

authentication_api = Blueprint("authentication", __name__)


@authentication_api.route("/api/check_init", methods=["POST"])
def check_init():
    try:
        if UsersManager.initial_user_exists():
            return jsonify(True)
        else:
            return jsonify(False)

    except Exception as e:
        tb1 = traceback.TracebackException.from_exception(e)
        print("".join(tb1.format()))
        return (
            jsonify({"error_message": "General exception at checking initial user"}),
            401,
        )


@authentication_api.route("/api/init", methods=["POST"])
def init():
    try:
        # Check (again) we have an initial user
        if UsersManager.initial_user_exists():
            return jsonify({"error_message": "Initial user already exists"}), 401

        # Check all required fields are filled
        username = request.json.get("username")
        password1 = request.json.get("password1")
        password2 = request.json.get("password2")
        if not all([username, password1, password2]):
            return jsonify({"error_message": "Complete all fields"}), 401

        # Prototype user
        user = {
            "username": username,
            "password1": password1,
            "password2": password2,
            "admin": True,
            "permissions": {},
        }

        # Try to create a new user
        success, message = UsersManager.create_user(user)
        if success:
            return jsonify({"success_message": message})
        return jsonify({"error_message": message}), 400

    except Exception as e:
        tb1 = traceback.TracebackException.from_exception(e)
        print("".join(tb1.format()))
        return jsonify({"error_message": "General exception at init thethe user"}), 400


@authentication_api.route("/api/auth", methods=["POST"])
def auth():
    try:
        username = request.json["data"]["username"]
        password = request.json["data"]["password"]

        token = UsersManager.authenticate(username, password)
        if not token:
            return jsonify({"error_message": "Bad user or password"}), 401

        return jsonify({"token": token, "username": username})

    except Exception as e:
        tb1 = traceback.TracebackException.from_exception(e)
        print("".join(tb1.format()))
        return jsonify({"error_message": "Exception at authentication"}), 401
