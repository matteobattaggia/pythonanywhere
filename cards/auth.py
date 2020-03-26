import functools, pickle

from flask import Blueprint, flash, g, redirect, render_template, request, \
                  session, url_for
from werkzeug.security import check_password_hash
from werkzeug.security import generate_password_hash

from cards.db import get_db, deserialize_user_state

bp = Blueprint('auth', __name__, url_prefix='/auth')

def login_required(view):
	'''View decorator that redirects anonymous users to the login page.'''
	@functools.wraps(view)
	def wrapped_view(**kwargs):
		if g.user is None:
			return redirect(url_for('auth.login'))
		return view(**kwargs)
	return wrapped_view

@bp.before_app_request
def load_logged_in_user():
	'''If a user id is stored in the session, load the user object from
	the database into "g.user".'''
	user_id = session.get('user_id')
	if user_id is None:
		g.user = None
	else:
		g.user = get_db().execute(
			'SELECT * FROM user WHERE id = ?', (user_id,)).fetchone()

@bp.route('/register', methods=('GET', 'POST'))
def register():
	'''Register a new user.
	Validates that the username is not already taken. Hashes the
	password for security.
	'''
	if request.method == 'POST':

		username = request.form['username']
		password = request.form['password']
		db = get_db()
		error = None

		if not username:
			error = 'A username is required.'
		elif not password:
			error = 'A password is required.'
		elif db.execute('SELECT id FROM user WHERE username = ?',
		                (username,)).fetchone() is not None:
			error = 'User "{}" is already registered.'.format(username)

		if error is None:
			# The name is available: store it in the database and go to the login page
			initial_state = \
			{
				# These do not change each hand
				'available_to_play' : False,
				'playing_order'     :     0,
				'assets'            :     0,
				'liabilities'       :     0,

				# These change each hand
				'ante'                 :  0,
				'cards_before_change'  : [],
				'action_before_change' :  0,
				'cards_to_be_changed'  : [],
				'new_cards'            : [],
				'action_after_change'  :  0,
			}
			db.execute('INSERT INTO user (username, password, state) VALUES (?, ?, ?)',
			           (username, generate_password_hash(password), pickle.dumps(initial_state)))
			db.commit()
			flash('User "{}" successfully registered.'.format(username))
			return redirect(url_for('auth.login'))

		flash(error)

	return render_template('auth/register.html')

@bp.route('/login', methods=('GET', 'POST'))
def login():
	'''Log in a registered user by adding the user id to the session.'''

	if request.method == 'POST':

		error = None
		username = request.form['username']
		password = request.form['password']
		db = get_db()
		user = db.execute('SELECT * FROM user WHERE username = ?', (username,)).fetchone()

		if user is None:
			error = 'Incorrect username.'
		elif not check_password_hash(user['password'], password):
			error = 'Incorrect password.'

		if error is None:

			# Update the user state to "available to play"
			state = pickle.loads(user['state'])
			state['available_to_play'] = True
			db.execute('UPDATE user SET state = ? WHERE id = ?', (pickle.dumps(state), user['id']))
			db.commit()

			# Store the user id in a new session and return to the index
			session.clear()
			session['user_id'] = user['id']
			return redirect(url_for('index'))

		flash(error)

	return render_template('auth/login.html')

@bp.route('/logout')
def logout():
	'''Clear the current session, including the stored user id.'''

	# Update the user state to "unavailable to play"
	if g.user is not None:
		state = pickle.loads(g.user['state'])
		state['available_to_play'] = False
		db = get_db()
		db.execute('UPDATE user SET state = ? WHERE id = ?', (pickle.dumps(state), g.user['id']))
		db.commit()

	session.clear()
	return redirect(url_for('index'))
