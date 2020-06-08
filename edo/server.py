from flask import Flask, url_for
from flask import render_template
from flask_bootstrap import Bootstrap


app = Flask(__name__)
Bootstrap(app)
app.config['BOOTSTRAP_SERVE_LOCAL'] = True


@app.route('/')
def index():
    return 'index'

