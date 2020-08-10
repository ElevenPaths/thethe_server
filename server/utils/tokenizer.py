import os
import sys
import traceback

from datetime import datetime, timedelta

from flask import request, jsonify
from functools import wraps
from jose import jwt


_SECRET_KEY = os.environ["THETHE_SECRET"]
_EXPIRATION = 6000000

# TODO: Change expiration time when in production
def generate_auth_token(data):
    data["exp"] = datetime.utcnow() + timedelta(seconds=_EXPIRATION)
    return jwt.encode(data, _SECRET_KEY)


def verify_auth_token(token):
    s = {}
    try:
        s = jwt.decode(token, _SECRET_KEY)
        return s
    except jwt.ExpiredSignatureError:
        print("[!] Expired token")
        return s
    except jwt.JWTError:
        print("[!] Invalid token")
        return s


def token_required(f):
    @wraps(f)
    def decorated_function(*args, **kargs):
        try:
            if not "Authorization" in request.headers:
                return (
                    jsonify({"error_message": "No authorization header in request"}),
                    401,
                )
            token = request.headers["Authorization"]
            user = verify_auth_token(token)
            if user:
                return f(user, *args, **kargs)
            else:
                return (
                    jsonify({"error_message": "Invalid token"}),
                    401,
                )
        except Exception as e:
            tb1 = traceback.TracebackException.from_exception(e)
            print("".join(tb1.format()))
            return jsonify({"error_message": "Invalid token"}), 401

    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kargs):
        try:
            if not "Authorization" in request.headers:
                return (
                    jsonify({"error_message": "No authorization header in request"}),
                    401,
                )
            token = request.headers["Authorization"]
            admin = verify_auth_token(token)
            if admin.get("is_admin"):
                return f(admin, *args, **kargs)
            else:
                return (
                    jsonify({"error_message": "User is not admin"}),
                    400,
                )
        except Exception as e:
            tb1 = traceback.TracebackException.from_exception(e)
            print("".join(tb1.format()))
            return jsonify({"error_message": "Invalid token"}), 401

    return decorated_function


def tags_required(f):
    @wraps(f)
    def decorated_function(*args, **kargs):
        try:
            if not "Authorization" in request.headers:
                return (
                    jsonify({"error_message": "No authorization header in request"}),
                    401,
                )
            token = request.headers["Authorization"]
            user = verify_auth_token(token)
            if user.get("permissions").get("tags"):
                return f(user, *args, **kargs)
            else:
                return (
                    jsonify({"error_message": "User does not have tags permission"}),
                    400,
                )
        except Exception as e:
            tb1 = traceback.TracebackException.from_exception(e)
            print("".join(tb1.format()))
            return jsonify({"error_message": "Invalid token"}), 401

    return decorated_function


def projects_required(f):
    @wraps(f)
    def decorated_function(*args, **kargs):
        try:
            if not "Authorization" in request.headers:
                return (
                    jsonify({"error_message": "No authorization header in request"}),
                    401,
                )
            token = request.headers["Authorization"]
            user = verify_auth_token(token)
            if user.get("permissions").get("projects"):
                return f(user, *args, **kargs)
            else:
                return (
                    jsonify(
                        {"error_message": "User does not have projects permission"}
                    ),
                    400,
                )
        except Exception as e:
            tb1 = traceback.TracebackException.from_exception(e)
            print("".join(tb1.format()))
            return jsonify({"error_message": "Invalid token"}), 401

    return decorated_function


def resources_required(f):
    @wraps(f)
    def decorated_function(*args, **kargs):
        try:
            if not "Authorization" in request.headers:
                return (
                    jsonify({"error_message": "No authorization header in request"}),
                    401,
                )
            token = request.headers["Authorization"]
            user = verify_auth_token(token)
            if user.get("permissions").get("resources"):
                return f(user, *args, **kargs)
            else:
                return (
                    jsonify(
                        {"error_message": "User does not have resources permission"}
                    ),
                    400,
                )
        except Exception as e:
            tb1 = traceback.TracebackException.from_exception(e)
            print("".join(tb1.format()))
            return jsonify({"error_message": "Invalid token"}), 401

    return decorated_function


def exclude_readonly(f):
    @wraps(f)
    def decorated_function(*args, **kargs):
        try:
            if not "Authorization" in request.headers:
                return (
                    jsonify({"error_message": "No authorization header in request"}),
                    401,
                )
            token = request.headers["Authorization"]
            user = verify_auth_token(token)
            if user.get("permissions").get("readonly"):
                return (
                    jsonify(
                        {
                            "error_message": "Your account is readonly. Operation not permitted."
                        }
                    ),
                    400,
                )
            else:
                return f(user, *args, **kargs)

        except Exception as e:
            tb1 = traceback.TracebackException.from_exception(e)
            print("".join(tb1.format()))
            return jsonify({"error_message": "Invalid token"}), 401

    return decorated_function
