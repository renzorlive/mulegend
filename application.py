import os
import re
from cs50 import SQL
from tempfile import mkdtemp
from flask import Flask, jsonify, render_template, request, url_for, flash, redirect, session
from flask_session import Session
from flask_jsglue import JSGlue

from flask import send_file

# configure application
app = Flask(__name__)
JSGlue(app)

# Ensure responses aren't cached
if app.config["DEBUG"]:
    @app.after_request
    def after_request(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///mashup.db")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/<string:filename>")
def main(filename):
    """Render file."""
    return render_template(filename)

@app.route("/favicon.ico")
def favicon():
    filename = 'images/fav.png'
    return send_file(filename, mimetype='image/png')