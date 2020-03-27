import functools, pickle, random

from flask import Blueprint, render_template, request, redirect, url_for

from cards.db import get_db, deserialize_user_state

# Some constants and functions to manage playing cards
SUITS = SPADE, CLUB, DIAMOND, HEART = list('\u2660\u2663\u2662\u2661')
RANKS = '2 3 4 5 6 7 8 9 10 J Q K A'.split()
def i2card(i, number_of_cards=52):
	global RANKS, SUITS
	n = number_of_cards // 4
#	suit, rank = divmod(i, n)  # 2, 3, 4, 5, 6, 7, 8, 9, 10, J, Q, K, A, ..., repeated for all four suits
	rank, suit = divmod(i, 4)  # 2, 2, 2, 2, 3, 3, 3, 3, ..., A, A, A, A. In this way i can be used to compare two cards
	rank += 13 - n
	return suit, rank, RANKS[rank] + SUITS[suit]
NUMBER_OF_CARDS = 32  # 7, 8, 9, 10, J, Q, K, A for four suits
def show_cards(cs):
	global NUMBER_OF_CARDS
	return ', '.join([i2card(c, NUMBER_OF_CARDS)[2] for c in cs])
def get_cards(cs, s):
	if s.strip() == '0':
		return []
	indices = s.split(',') if ',' in s else s.split()
	try:
		indices = [int(i) for i in indices]
		return sorted([cs[i - 1] for i in indices])
	except (ValueError, IndexError):
		return cs

bp = Blueprint('play', __name__)

@bp.route('/', methods=('GET', 'POST'))
def index():
	db = get_db()
	random.seed()
#	num_users = db.execute('SELECT COUNT(*) FROM user').fetchone()[0]
	users = [deserialize_user_state(user) for user in db.execute('SELECT * FROM user').fetchall()]
	players = [user for user in users if (user['state'] and user['state']['available_to_play'])]
	ordered_players = None
	phase_ante, phase_action_before_change, phase_change, phase_action_after_change = 0, 0, 0, 0
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

		# Antes
		# TODO: manage the ante phase
#		for i, player in enumerate(ordered_players):
#			if player['state']['ante'] == 0:
#				phase_ante = i
#				break
#		else:  # "else" branch executed if the loop terminates without a break
#			phase_ante = 4
		phase_ante = 4
#		if phase_ante < 4 and request.method == 'POST' and 'ante' in request.form:
#			ordered_players[phase_ante]['state']['ante'] =  request.form['ante']
#			db.execute('UPDATE user SET state = ? WHERE id = ?',
#			           (pickle.dumps(ordered_players[phase_ante]['state']), ordered_players[phase_ante]['id']))
#			db.commit()
#			return redirect(url_for('index'))

		# Give the cards
		if phase_ante == 4 and ordered_players[0]['state']['cards_before_change'] is None:
			deck = list(range(NUMBER_OF_CARDS))
			random.shuffle(deck)
			for i, player in enumerate(ordered_players):
				player['state']['cards_before_change'] = sorted(deck[5 * i : 5 * (i + 1)])
				db.execute('UPDATE user SET state = ? WHERE id = ?', (pickle.dumps(player['state']), player['id']))
			db.commit()

		# Actions before change
		if phase_ante == 4 and ordered_players[0]['state']['cards_before_change'] is not None:
			# TODO: manage the actions-before-change phase
#			for i, player in enumerate(ordered_players):
#				if player['state']['action_before_change'] == 0:
#					phase_action_before_change = i
#					break
#			else:  # "else" branch executed if the loop terminates without a break
#				phase_action_before_change = 4
			phase_action_before_change = 4
			# TODO: update state in the database

		# Ask how many cards to change
		if phase_ante == 4 and ordered_players[0]['state']['cards_before_change'] is not None and \
		   phase_action_before_change == 4:
			for i, player in enumerate(ordered_players):
				if player['state']['cards_to_be_changed'] is None:
					phase_change = i
					break
			else:  # "else" branch executed if the loop terminates without a break
				phase_change = 4
		if phase_change < 4 and request.method == 'POST' and 'change' in request.form:
			ordered_players[phase_change]['state']['cards_to_be_changed'] = \
				get_cards(ordered_players[phase_change]['state']['cards_before_change'], request.form['change'])
			db.execute('UPDATE user SET state = ? WHERE id = ?',
			           (pickle.dumps(ordered_players[phase_change]['state']), ordered_players[phase_change]['id']))
			db.commit()
			return redirect(url_for('index'))

		# Change the cards
		if phase_change == 4 and ordered_players[0]['state']['new_cards'] is None:
			deck = set(range(NUMBER_OF_CARDS))
			all_players_cards = set(sum([player['state']['cards_before_change'] for player in ordered_players], []))
			all_cards_to_be_changed = set(sum([player['state']['cards_to_be_changed'] for player in ordered_players], []))
			for i, player in enumerate(ordered_players):
				# TODO
				pass
#				db.execute('UPDATE user SET state = ? WHERE id = ?', (pickle.dumps(player['state']), player['id']))
#			db.commit()

		# Actions after change
		phase_action_after_change = 4

		# Show the cards and give the winner money
		# TODO

	else:
		# Reset playing order for all users and hand state for all users
		for user in users:
			user['state']['playing_order'       ] =    0
			user['state']['ante'                ] =    0
			user['state']['cards_before_change' ] = None
			user['state']['action_before_change'] =    0
			user['state']['cards_to_be_changed' ] = None
			user['state']['new_cards'           ] = None
			user['state']['action_after_change' ] =    0
			db.execute('UPDATE user SET state = ? WHERE id = ?', (pickle.dumps(user['state']), user['id']))
		db.commit()
	return render_template(
		'play/index.html',
		show_cards=show_cards,
		users=users,
		players=players,
		ordered_players=ordered_players,
		phase_ante=phase_ante,
		phase_action_before_change=phase_action_before_change,
		phase_change=phase_change,
		phase_action_after_change=phase_action_after_change,
	)
