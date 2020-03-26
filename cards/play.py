import functools, pickle

from flask import Blueprint, render_template

from cards.db import get_db

bp = Blueprint('play', __name__)

def deserialize_user_state(user):
	user_dict = dict(user)
	if user['state'] is not None:
		user_dict['state'] = pickle.loads(user['state'])
	return user_dict

@bp.route('/')
def index():
	db = get_db()
#	num_users = db.execute('SELECT COUNT(*) FROM user').fetchone()[0]
	users = [deserialize_user_state(user) for user in db.execute('SELECT * FROM user').fetchall()]
	players = [user for user in users
	           if (user['state'] and user['state']['available_to_play'])]
	return render_template('play/index.html', num_users=len(users), players=players)
