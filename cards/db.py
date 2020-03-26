import sqlite3, pickle

import click
from flask import g, current_app
from flask.cli import with_appcontext

def get_db():
	'''Connect to the application's configured database. The connection
	is unique for each request and will be reused if this is called
	again.
	'''
	if 'db' not in g:
		g.db = sqlite3.connect(current_app.config['DATABASE'],
		                       detect_types=sqlite3.PARSE_DECLTYPES)
		g.db.row_factory = sqlite3.Row

	return g.db

def deserialize_user_state(user):
	user_dict = dict(user)
	if user['state'] is not None:
		user_dict['state'] = pickle.loads(user['state'])
	return user_dict

def close_db(e=None):
	'''If this request connected to the database, close the connection.'''
	db = g.pop('db', None)
	if db is not None:
		db.close()

def init_db():
	'''Clear existing data and create new tables.'''
	with current_app.open_resource('schema.sql') as f:
		get_db().executescript(f.read().decode('utf8'))

@click.command('init-db')
@with_appcontext
def init_db_command():
	'''Clear existing data and create new tables.'''
	init_db()
	click.echo('The database has been initialized.')

def init_app(app):
	'''Register database functions with the Flask app. This is called by
	the application factory.
	'''
	app.teardown_appcontext(close_db)
	app.cli.add_command(init_db_command)
