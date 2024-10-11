from flask import Blueprint, render_template

user = Blueprint("user", __name__, static_folder="static", template_folder="templates")

