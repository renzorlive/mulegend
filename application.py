import os
import re
from flask import Flask, jsonify, render_template, request, url_for
from flask_jsglue import JSGlue

from flask import send_file

# configure application
app = Flask(__name__)
JSGlue(app)

# prevent cached responses
@app.after_request
def add_header(r):
    """
    Add headers to both force latest IE rendering engine or Chrome Frame,
    and also to cache the rendered page for 10 minutes.
    """
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    r.headers['Cache-Control'] = 'public, max-age=0'
    return r

@app.route("/<string:filename>")
def main(filename):
    """Render file."""
    return render_template(filename)

@app.route("/favicon.ico")
def favicon():
    filename = 'images/fav.png'
    return send_file(filename, mimetype='image/png')