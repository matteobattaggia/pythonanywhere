import functools, pickle, random

from flask import Blueprint, render_template, request, redirect, url_for, g, session

from cards.db import get_db, INITIAL_USER_STATE, deserialize_user_state

#-------------------------------------------------------------------------------
# Some constants and functions to manage playing cards

SUITS = SPADE, CLUB, DIAMOND, HEART = list('\u2660\u2663\u2662\u2661')
RANKS = '2 3 4 5 6 7 8 9 10 J Q K A'.split()
SUITS_NAMES = ['picche', 'fiori', 'quadri', 'cuori']
RANKS_NAMES = \
[
	( 'due'     , 'due'     , 'al'   , 'ai'   ),
	( 'tre'     , 'tre'     , 'al'   , 'ai'   ),
	( 'quattro' , 'quattro' , 'al'   , 'ai'   ),
	( 'cinque'  , 'cinque'  , 'al'   , 'ai'   ),
	( 'sei'     , 'sei'     , 'al'   , 'ai'   ),
	( 'sette'   , 'sette'   , 'al'   , 'ai'   ),
	( 'otto'    , 'otto'    , "all'" , 'agli' ),
	( 'nove'    , 'nove'    , 'al'   , 'ai'   ),
	( 'dieci'   , 'dieci'   , 'al'   , 'ai'   ),
	( 'fante'   , 'fanti'   , 'al'   , 'ai'   ),
	( 'donna'   , 'donne'   , 'alla' , 'alle' ),
	( 're'      , 're'      , 'al'   , 'ai'   ),
	( 'asso'    , 'assi'    , "all'" , 'agli' ),
]

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
	cards_str = ', '.join([i2card(c, NUMBER_OF_CARDS)[2] for c in cs])
	if len(cs) != 5:
		return cards_str
	else:
		hand_desc = evaluate_hand(cs)
		return f'{cards_str}: {hand_desc}'
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
#	1 coppia             a pair            (m = rank della coppia, p = seme piu' alto della coppia)
#	2 doppia coppia      two pairs         (m = rank della coppia piu' alta, p = rank della coppia piu' bassa, q = seme piu' alto della coppia piu' alta)
#	3 tris               3-of-a-kind       (m = rank del tris)
#	4 scala semplice     straight          (m = rank carta piu' alta [ATTENZIONE alle scale minime!], p = seme della carta piu' alta)
#	5 full               full house        (m = rank del tris)
#	6 colore             flush             (m = seme del colore, p = rank della carta piu' alta)
#	7 poker              4-of-a-kind       (m = rank del poker)
#	8 scala reale        straight flush    (m = seme del scala reale, p = rank della carta piu' alta)

def evaluate_hand(cs):
	global NUMBER_OF_CARDS, SUITS_NAMES, RANKS_NAMES
	ranks = [i2card(c, NUMBER_OF_CARDS)[0] for c in cs]
	suits = [i2card(c, NUMBER_OF_CARDS)[1] for c in cs]
	is_straight = len(set(ranks)) == 5 and (set(ranks) == set(range(min(ranks), max(ranks) + 1)))
	is_flush = (len(set(suits)) == 1)
	ranks_cnt = {r: ranks.count(r) for r in set(ranks)}
	min_ranks_cnt, max_ranks_cnt = min(ranks_cnt.values()), max(ranks_cnt.values())
	if is_straight and is_flush:
		suit, highest_rank, prep = \
			SUITS_NAMES[suits[0]], RANKS_NAMES[max(ranks)][0], RANKS_NAMES[max(ranks)][2]
		return f'scala reale di {suit} {prep} {highest_rank}'
	elif is_flush:
		suit = SUITS_NAMES[suits[0]]
		return f'colore di {suit}'
	elif is_straight:
		max_rank, max_suit = i2card(max(cs), NUMBER_OF_CARDS)[:2]
		suit, highest_rank, prep = \
			SUITS_NAMES[max_suit], RANKS_NAMES[max_rank][0], RANKS_NAMES[max_rank][2]
		return f'scala {prep} {highest_rank} di {suit}'
	elif max_ranks_cnt == 4:
		rank = RANKS_NAMES[[r for r in ranks_cnt if ranks_cnt[r] == 4][0]][1]
		return f'poker di {rank}'
	elif max_ranks_cnt == 3:
		rank3 = RANKS_NAMES[[r for r in ranks_cnt if ranks_cnt[r] == 3][0]][1]
		if min_ranks_cnt == 2:
			rank2 = RANKS_NAMES[[r for r in ranks_cnt if ranks_cnt[r] == 2][0]][1]
			return f'full di {rank3} e {rank2}'
		else:
			return f'tris di {rank3}'
	elif max_ranks_cnt == 2:
		if len(ranks_cnt) == 3:
			r1, r2 = sorted([r for r in ranks_cnt if ranks_cnt[r] == 2])
			rank2_1, rank2_2 = [RANKS_NAMES[r][1] for r in [r1, r2]]
			suit = SUITS_NAMES[max([s for (r, s) in zip(ranks, suits) if r == r2])]
			return f'doppia coppia di {rank2_2} e {rank2_1} ({suit})'
		else:
			r2 = [r for r in ranks_cnt if ranks_cnt[r] == 2][0]
			rank2 = RANKS_NAMES[r2][1]
			suit = SUITS_NAMES[max([s for (r, s) in zip(ranks, suits) if r == r2])]
			return f'coppia di {rank2} ({suit})'
	else:
		max_rank, max_suit = i2card(max(cs), NUMBER_OF_CARDS)[:2]
		suit, highest_rank = \
			SUITS_NAMES[max_suit], RANKS_NAMES[max_rank][0]
		return f'{highest_rank} di {suit}'

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
		try:
			g.user = deserialize_user_state(get_db().execute(
				'SELECT * FROM user WHERE id = ?', (user_id,)).fetchone())
		except TypeError:
			# Current user not found in the database: clear the session
			g.user = None
			session.clear()

@bp.route('/', methods=('GET', 'POST'))
def index():
	db = get_db()
	random.seed()
#	num_users = db.execute('SELECT COUNT(*) FROM user').fetchone()[0]
	users = [deserialize_user_state(user) for user in db.execute('SELECT * FROM user').fetchall()]
	players = [user for user in users if (user['state'] and user['state']['available_to_play'])]
	ordered_players = None
	phase_ante, phase_action_before_change, phase_change, phase_action_after_change = 0, 0, 0, 0
	finished = False
	if len(players) == 4:

		# If not already chosen, choose a random playing order
		playing_orders = [player['state']['playing_order'] for player in players]
		if set(playing_orders) != set(range(4)):
			playing_orders = random.sample(range(4), 4)
			for player, playing_order in zip(players, playing_orders):
				player['state']['playing_order'] = playing_order
				db.execute('UPDATE user SET state = ? WHERE id = ?', (pickle.dumps(player['state']), player['id']))
			db.commit()
		ordered_players = sorted(players, key=lambda p: p['state']['playing_order'])
		assert [p['state']['playing_order'] for p in ordered_players] == list(range(4))

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
					remaining_cards = []
					discarded_cards = discarded_cards[num_discarded_cards_needed:]
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

		# Show the hands (TODO)
		if phase_action_after_change == 4:
			folds_after_change = [player['state']['fold_after_change'] for player in ordered_players]
			if None in folds_after_change and request.method == 'POST' and 'show_hand' in request.form:
				i = int(request.form['playing_order'])
				ordered_players[i]['state']['fold_after_change'] = (request.form['show_hand'] == 'no')
				db.execute('UPDATE user SET state = ? WHERE id = ?',
				           (pickle.dumps(ordered_players[i]['state']), ordered_players[i]['id']))
				db.commit()
				return redirect(url_for('index'))
			elif None not in folds_after_change:
				finished = True

	else:  # if len(players) == 4

		# Reset playing order and hand state for all users
		for user in users:
			user['state']['playing_order'       ] =    0
			user['state']['ante'                ] =    0
			user['state']['cards_before_change' ] = None
			user['state']['action_before_change'] =    0
			user['state']['fold_before_change'  ] = None
			user['state']['cards_to_be_changed' ] = None
			user['state']['new_cards'           ] = None
			user['state']['action_after_change' ] =    0
			user['state']['fold_after_change'   ] = None
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
		finished=finished,
		show_cards=show_cards,
		merge_cards=merge_cards,
	)

@bp.route('/restart/')
@bp.route('/restart/<playing_order>')
def restart(playing_order=None):
	if playing_order is not None:
		if playing_order == 'random':
			playing_orders = [0, 0, 0, 0]
		elif set(playing_order) == set('0123'):
			playing_orders = [int(c) for c in playing_order]
		else:
			playing_order = None
	db = get_db()
	# Reset hand state (and possibly playing order) for all users
	users = [deserialize_user_state(user) for user in db.execute('SELECT * FROM user').fetchall()]
	for i, user in enumerate(users):
		user['state']['ante'                ] =    0
		user['state']['cards_before_change' ] = None
		user['state']['action_before_change'] =    0
		user['state']['fold_before_change'  ] = None
		user['state']['cards_to_be_changed' ] = None
		user['state']['new_cards'           ] = None
		user['state']['action_after_change' ] =    0
		user['state']['fold_after_change'   ] = None
		if playing_order:
			user['state']['playing_order'] = playing_orders[i]
		db.execute('UPDATE user SET state = ? WHERE id = ?', (pickle.dumps(user['state']), user['id']))
	db.commit()
	return redirect(url_for('index'))

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
