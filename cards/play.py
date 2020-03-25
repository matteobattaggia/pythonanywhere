import functools

from flask import Blueprint, render_template

from cards.db import get_db

bp = Blueprint('play', __name__)

@bp.route('/')
def index():
	db = get_db()
	num_users = db.execute('SELECT COUNT(*) FROM user').fetchone()[0]
	return render_template('play/index.html', num_users=num_users)
