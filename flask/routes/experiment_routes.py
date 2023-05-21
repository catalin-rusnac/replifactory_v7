from flask import Blueprint, request, jsonify
import time

# cors

experiment_routes = Blueprint('experiment_routes', __name__)
