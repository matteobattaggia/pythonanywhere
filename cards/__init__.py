import os

from flask import Flask, render_template

def create_app(test_config=None):
	'''Create and configure an instance of the Flask application.'''

	# Create and configure the app
	app = Flask(__name__, instance_relative_config=True)
	app.config.from_mapping(
		# A default secret key that should be overridden by instance config
		SECRET_KEY = 'dev',
		# Store the database in the instance folder
		DATABASE = os.path.join(app.instance_path, 'cards.sqlite'),
	)
	if test_config is None:
		# load the instance config (if it exist) when not testing
		app.config.from_pyfile('config.py', silent=True)
	else:
		# load the test config if passed in
		app.config.update(test_config)

	# Ensure the instance folder exists
	try:
		os.makedirs(app.instance_path)
	except OSError:
		pass

	# Register the database commands
	import cards.db
	cards.db.init_app(app)

	# Apply the blueprints to the app
	import cards.auth, cards.play
	app.register_blueprint(cards.auth.bp)
	app.register_blueprint(cards.play.bp)

	# make url_for('index') == url_for('play.index')
	app.add_url_rule('/', endpoint='index')

	return app
