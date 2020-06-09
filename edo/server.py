from flask import Flask, url_for, request
from flask import render_template
from flask_bootstrap import Bootstrap

from edo.edo import query_cache

app = Flask(__name__)
Bootstrap(app)
app.config['BOOTSTRAP_SERVE_LOCAL'] = True


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/results', methods=['POST'])
def results():
    query = request.form.get('searchInput')

    results = query_cache(query)

    # transform results
    data = []
    for i in results:
        row = {
            'path'  : i[0], 
            'score' : i[1], 
            'substring' : i[2],
        }
        data.append(row)

    return render_template('results.html', data=data)
