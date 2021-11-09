from flask import Flask, templating
import threading

app = Flask(__name__)

global output_html
output_html = "test"

@app.route("/")
def index():
    return templating.render_template("index.html")

@app.route("/update")
def update():
    return output_html

def start(child_conn):
    global conn
    conn = child_conn
    threading.Thread(None, update_html, daemon=True).start()
    app.run("localhost", 5000)

def update_html():
    while True:
        global output_html
        global conn
        output_html = conn.recv()
