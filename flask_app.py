from flask import Flask, render_template, request

def capitalize(s):
	return s[0].upper() + s[1:].lower() if s else ''

app = Flask(__name__)

@app.route('/')
@app.route('/<greeting>/')
@app.route('/<greeting>/<name>')
def hello(greeting=None, name=None):
	greeting, name = (capitalize(s) for s in [greeting, name])
	return render_template('flask_app.html', greeting=greeting, name=name)
