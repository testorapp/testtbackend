"""Testora Backend - Route Blueprints"""
from flask import Blueprint

auth_bp = Blueprint('auth', __name__)
users_bp = Blueprint('users', __name__)
tests_bp = Blueprint('tests', __name__)

from . import auth, users, tests

