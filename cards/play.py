import functools, pickle, random

from flask import Blueprint, render_template

from cards.db import get_db, deserialize_user_state

bp = Blueprint('play', __name__)

@bp.route('/')
def index():
	db = get_db()
#	num_users = db.execute('SELECT COUNT(*) FROM user').fetchone()[0]
	users = [deserialize_user_state(user) for user in db.execute('SELECT * FROM user').fetchall()]
	players = [user for user in users if (user['state'] and user['state']['available_to_play'])]
	ordered_players = None
	random.seed()
	if len(players) == 4:

		# If not already chosen, choose a random playing order
		playing_orders = [player['state']['playing_order'] for player in players]
		if set(playing_orders) != set(range(4)):
			playing_orders = random.sample(range(4), 4)
			for player, playing_order in zip(players, playing_orders):
				player['state']['playing_order'] = playing_order
				db.execute('UPDATE user SET state = ? WHERE id = ?', (pickle.dumps(player['state']), player['id']))
			db.commit()
		ordered_players = [players[i] for i in playing_orders]

		# Check the antes
		# TODO

		# Give the cards
		# TODO

		# Actions before change
		# TODO

		# Change the cards
		# TODO

		# Actions after change
		# TODO

		# Show the cards and give the winner money
		# TODO

	else:
		# Reset playing order for all users and hand state for all users
		for user in users:
			user['state']['playing_order'       ] =  0
			user['state']['ante'                ] =  0
			user['state']['cards_before_change' ] = []
			user['state']['action_before_change'] =  0
			user['state']['cards_to_be_changed' ] = []
			user['state']['new_cards'           ] = []
			user['state']['action_after_change' ] =  0
			db.execute('UPDATE user SET state = ? WHERE id = ?', (pickle.dumps(user['state']), user['id']))
		db.commit()
	return render_template(
		'play/index.html',
		num_users=len(users),
		players=players,
		ordered_players=ordered_players,
	)
