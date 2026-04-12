from flask import Flask, Blueprint, request
from utils import get_db


constituency_bp = Blueprint("constituency", __name__)

@constituency_bp.route("/constituency", methods=["GET"])
def get_constituency():
    constituency = db.constituency.find()

