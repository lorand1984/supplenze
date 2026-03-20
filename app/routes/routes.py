from flask import Blueprint, jsonify

main = Blueprint("main", __name__)

@main.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200