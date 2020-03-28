import functools, pickle, random

from flask import Blueprint, render_template, request, redirect, url_for, g, session

from cards.db import get_db, INITIAL_USER_STATE, deserialize_user_state

#-------------------------------------------------------------------------------
# Some constants and functions to manage playing cards

SUITS = SPADE, CLUB, DIAMOND, HEART = list('\u2660\u2663\u2662\u2661')
RANKS = '2 3 4 5 6 7 8 9 10 J Q K A'.split()
def i2card(i, number_of_cards=52):
	global RANKS, SUITS
	n = number_of_cards // 4
#	suit, rank = divmod(i, n)  # 2, 3, 4, 5, 6, 7, 8, 9, 10, J, Q, K, A, ..., repeated for all four suits
	rank, suit = divmod(i, 4)  # 2, 2, 2, 2, 3, 3, 3, 3, ..., A, A, A, A. In this way i can be used to compare two cards
	rank += 13 - n
	return rank, suit, RANKS[rank] + SUITS[suit]
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
def merge_cards(cards_before_change, cards_to_be_changed, new_cards):
	return sorted(set(cards_before_change) - set(cards_to_be_changed) | set(new_cards))

#	Punteggi (n, m, p, q)
#
#	n
#	0 carta piu' alta    high card         (m = rank della carta piu' alta, p = seme della carta piu' alta)
#	1 coppia             pair              (m = rank della coppia, p = seme piu' alto della coppia)
#	2 doppia coppia      two pairs         (m = rank della coppia piu' alta, p = rank della coppia piu' bassa, q = seme piu' alto della coppia piu' alta)
#	3 tris               3-of-a-kind       (m = rank del tris)
#	4 scala semplice     straight          (m = rank carta piu' alta [ATTENZIONE alle scale minime!], p = seme della carta piu' alta)
#	5 full               full house        (m = rank del tris)
#	6 colore             flush             (m = seme del colore, p = rank della carta piu' alta)
#	7 poker              4-of-a-kind       (m = rank del poker)
#	8 scala reale        straight flush    (m = seme del scala reale, p = rank della carta piu' alta)

def ranks_and_suits(cs):
	global NUMBER_OF_CARDS
	ranks = [i2card(c, NUMBER_OF_CARDS)[0] for c in cs]
	suits = [i2card(c, NUMBER_OF_CARDS)[1] for c in cs]
	return ranks, suits

def is_straight(ranks):
	return set(ranks) == set(range(min(ranks), max(ranks) + 1))

def is_flush(suits):
	return len(set(suits)) == 1

def is_straight_flush(ranks, suits):
	return is_straight(ranks) and is_flush(suits)

def is_four_of_a_kind(ranks):
	sorted_ranks = sorted(ranks)
	return (sorted_ranks[0] == sorted_ranks[1] == sorted_ranks[2] == sorted_ranks[3]) or \
	       (sorted_ranks[1] == sorted_ranks[2] == sorted_ranks[3] == sorted_ranks[4])

def is_full_house(ranks):
	sorted_ranks = sorted(ranks)
	return (sorted_ranks[0] == sorted_ranks[1] == sorted_ranks[2] and sorted_ranks[3] == sorted_ranks[4]) or \
	       (sorted_ranks[2] == sorted_ranks[3] == sorted_ranks[4] and sorted_ranks[0] == sorted_ranks[1])

def is_three_of_a_kind(ranks):
	pass

def is_two_pairs(ranks):
	pass

def is_pair(ranks):
	pass

#-------------------------------------------------------------------------------
# Main route

bp = Blueprint('play', __name__)

@bp.before_app_request
def load_logged_in_user():
	'''If a user id is stored in the session, load the user object from
	the database into "g.user".'''
	user_id = session.get('user_id')
	if user_id is None:
		g.user = None
	else:
		g.user = deserialize_user_state(get_db().execute(
			'SELECT * FROM user WHERE id = ?', (user_id,)).fetchone())

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
		# TODO: ante phase temporarily disabled
		phase_ante = 4
#		for i, player in enumerate(ordered_players):
#			if player['state']['ante'] == 0:
#				phase_ante = i
#				break
#		else:  # "else" branch executed if the loop terminates without a break
#			phase_ante = 4
#		# Update state in the database
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
			# TODO: action-before-change phase temporarily disabled
			phase_action_before_change = 4
#			for i, player in enumerate(ordered_players):
#				if player['state']['action_before_change'] == 0:
#					phase_action_before_change = i
#					break
#			else:  # "else" branch executed if the loop terminates without a break
#				phase_action_before_change = 4
#			# Update state in the database
#			if phase_action_before_change < 4 and request.method == 'POST' and \
#			   'action_before_change' in request.form:
#				ordered_players[phase_action_before_change]['state']['action_before_change'] = \
#					request.form['action_before_change']
#				db.execute('UPDATE user SET state = ? WHERE id = ?',
#				           (pickle.dumps(ordered_players[phase_action_before_change]['state']),
#				            ordered_players[phase_action_before_change]['id']))
#				db.commit()
#				return redirect(url_for('index'))

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
			remaining_cards = list(deck - all_players_cards)
			discarded_cards = []
			random.shuffle(remaining_cards)
			for player in ordered_players:
				num_cards_to_be_changed = len(player['state']['cards_to_be_changed'])
				if num_cards_to_be_changed <= len(remaining_cards):
					player['state']['new_cards'] = sorted(remaining_cards[:num_cards_to_be_changed])
					remaining_cards = remaining_cards[num_cards_to_be_changed:]
				else:
					random.shuffle(discarded_cards)
					num_discarded_cards_needed = num_cards_to_be_changed - len(remaining_cards)
					player['state']['new_cards'] = sorted(remaining_cards + discarded_cards[:num_discarded_cards_needed])
				discarded_cards += player['state']['cards_to_be_changed']
				db.execute('UPDATE user SET state = ? WHERE id = ?', (pickle.dumps(player['state']), player['id']))
			db.commit()

		# Actions after change
		if phase_change == 4 and ordered_players[0]['state']['new_cards'] is not None:
			# TODO: action-after-change phase temporarily disabled
			phase_action_after_change = 4
#			for i, player in enumerate(ordered_players):
#				if player['state']['action_after_change'] == 0:
#					phase_action_after_change = i
#					break
#			else:  # "else" branch executed if the loop terminates without a break
#				phase_action_after_change = 4
#			# Update state in the database
#			if phase_action_after_change < 4 and request.method == 'POST' and \
#			   'action_after_change' in request.form:
#				ordered_players[phase_action_after_change]['state']['action_after_change'] = \
#					request.form['action_after_change']
#				db.execute('UPDATE user SET state = ? WHERE id = ?',
#				           (pickle.dumps(ordered_players[phase_action_after_change]['state']),
#				            ordered_players[phase_action_after_change]['id']))
#				db.commit()
#				return redirect(url_for('index'))

		# Show the cards and give the winner money
		# TODO

	else:  # if len(players) == 4

		# Reset playing order and hand state for all users
		for user in users:
			user['state']['playing_order'       ] =     0
			user['state']['ante'                ] =     0
			user['state']['cards_before_change' ] =  None
			user['state']['action_before_change'] =     0
			user['state']['fold_before_change'  ] = False
			user['state']['cards_to_be_changed' ] =  None
			user['state']['new_cards'           ] =  None
			user['state']['action_after_change' ] =     0
			user['state']['fold_after_change'   ] = False
			db.execute('UPDATE user SET state = ? WHERE id = ?', (pickle.dumps(user['state']), user['id']))
		db.commit()

	return render_template(
		'play/index.html',
		users=users,
		players=players,
		ordered_players=ordered_players,
		phase_ante=phase_ante,
		phase_action_before_change=phase_action_before_change,
		phase_change=phase_change,
		phase_action_after_change=phase_action_after_change,
		show_cards=show_cards,
		merge_cards=merge_cards,
	)

#-------------------------------------------------------------------------------
# Debug routes

@bp.route('/debug/reset/<username>')
def reset(username):
	db = get_db()
	if username == '__ALL__':
		# Reset state for all users
		users = db.execute('SELECT * FROM user').fetchall()
		for user in users:
			db.execute('UPDATE user SET state = ? WHERE id = ?', (pickle.dumps(INITIAL_USER_STATE), user['id']))
	else:
		# Reset state for username
		user = db.execute('SELECT * FROM user WHERE username = ?', (username,)).fetchone()
		db.execute('UPDATE user SET state = ? WHERE id = ?', (pickle.dumps(INITIAL_USER_STATE), user['id']))
	db.commit()
	return redirect(url_for('index'))

@bp.route('/debug/restart/')
@bp.route('/debug/restart/<change_playing_order>')
def restart(change_playing_order=None):
	db = get_db()
	# Reset hand state (and possibly playing order) for all users
	users = [deserialize_user_state(user) for user in db.execute('SELECT * FROM user').fetchall()]
	for user in users:
		user['state']['ante'                ] =    0
		user['state']['cards_before_change' ] = None
		user['state']['action_before_change'] =    0
		user['state']['cards_to_be_changed' ] = None
		user['state']['new_cards'           ] = None
		user['state']['action_after_change' ] =    0
		if change_playing_order:
			user['state']['playing_order'] = 0
		db.execute('UPDATE user SET state = ? WHERE id = ?', (pickle.dumps(user['state']), user['id']))
	db.commit()
	return redirect(url_for('index'))
