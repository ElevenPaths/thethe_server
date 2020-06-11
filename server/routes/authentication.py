import traceback
import bson
import json

import server.utils.password as utils
import server.utils.tokenizer as tokenizer

from server.db import DB
from server.utils.password import token_required, hash_password
from flask import Blueprint, request, jsonify
from zxcvbn import zxcvbn

authentication_api = Blueprint("authentication", __name__)

MIN_PASSWORD_LENGHT = 16


def _check_pass_strengh(candidate_pass):
    try:
        if not candidate_pass:
            return False
        result = zxcvbn(candidate_pass)
        if not result.get("score") == 4:
            return False
        return True

    except Exception as e:
        tb1 = traceback.TracebackException.from_exception(e)
        print("[_check_pass_strengh]")
        print("".join(tb1.format()))


@authentication_api.route("/api/check_init", methods=["POST"])
def check_init():
    try:
        print("check init")
        db = DB("users")
        count = db.collection.count_documents({})
        if not count:
            return jsonify(True)
        else:
            return jsonify(False)

    except Exception as e:
        tb1 = traceback.TracebackException.from_exception(e)
        print("".join(tb1.format()))
        return jsonify({"error_message": "General exception at init thethe user"}), 401


@authentication_api.route("/api/init", methods=["POST"])
def init():
    try:
        username = request.json.get("username")
        pass1 = request.json.get("pass1")
        pass2 = request.json.get("pass2")

        if not all([username, pass1, pass2]):
            return jsonify({"error_message": "Complete all fields"}), 401

        db = DB("users")
        count = db.collection.count_documents({})
        if not count:
            if not pass1 == pass2:
                return jsonify({"error_message": "Passwords does not match"}), 401
            else:
                good = _check_pass_strengh(pass1)
                if good:
                    db.collection.insert_one(
                        {"username": username, "password": hash_password(pass1)}
                    )
                    return jsonify({})
                else:
                    return jsonify({"error_message": "Weak password"}), 401
        else:
            return jsonify({"error_message": "Initial user exists"}), 401

    except Exception as e:
        tb1 = traceback.TracebackException.from_exception(e)
        print("".join(tb1.format()))
        return jsonify({"error_message": "General exception at init thethe user"}), 401


@authentication_api.route("/api/auth", methods=["POST"])
def auth():
    try:
        username = request.json["data"]["username"]
        password = request.json["data"]["password"]
        db = DB("users")
        cursor = db.collection.find_one({"username": username})
        if cursor:
            password_hash = cursor["password"]
            if utils.verify_password(password, password_hash):
                token = tokenizer.generate_auth_token(str(cursor["_id"]))
                return jsonify({"token": token.decode("utf-8"), "username": username})
        return jsonify({"error_message": "Bad user or password"}), 401

    except Exception as e:
        tb1 = traceback.TracebackException.from_exception(e)
        print("".join(tb1.format()))
        return jsonify({"error_message": "Exception at authentication"}), 401


@authentication_api.route("/api/changepassword", methods=["POST"])
@token_required
def change_password(user):
    try:
        # username = request.json["username"]
        old_password = request.json["old_password"]
        new_password_1 = request.json["new_password_1"]
        new_password_2 = request.json["new_password_2"]
        user = bson.ObjectId(user)

        db = DB("users")
        cursor = db.collection.find_one({"_id": user})
        if cursor:
            password_hash = cursor["password"]
            if not utils.verify_password(old_password, password_hash):
                return jsonify({"error_message": "Bad user or password"}), 401

        if not new_password_1 == new_password_2:
            print("[AUTH] Unmatched new password for change password operation")
            return jsonify({"error_message": "New password does not match"}), 401

        if len(new_password_1) < MIN_PASSWORD_LENGHT:
            print("[AUTH] new password is less than 8 characters")
            return (
                jsonify(
                    {
                        "error_message": "Password is too short (must be at least 8 characters)"
                    }
                ),
                401,
            )

        db.collection.update(
            {"_id": user}, {"$set": {"password": hash_password(new_password_1)}}
        )
        return jsonify({"success_message": "Password changed"})

    except Exception as e:
        tb1 = traceback.TracebackException.from_exception(e)
        print("".join(tb1.format()))
        return jsonify({"error_message": "Exception at authentication"}), 401
