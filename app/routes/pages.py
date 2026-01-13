from flask import Blueprint, render_template

bp_pages = Blueprint("pages", __name__)

@bp_pages.route("/")
def index():
    return render_template("index.html")
