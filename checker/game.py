# Blueprint for blog post functions
from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
from werkzeug.exceptions import abort

from checker.auth import login_required
from checker.db import get_db

# create a Blueprint named 'game' defined in current Python module
# no automatically prepended url here but could be applied
bp = Blueprint('game', __name__)


# define view at index url: '/'
@bp.route('/', methods=('GET', 'POST'))
def index():
    """Show game."""
    db = get_db()
    cur = db.cursor()

    cur.execute(
        'SELECT g.id, player1_id, player2_id FROM game g'
    )
    games = cur.fetchall()
    
    game_id = 1

    if request.method == 'POST':
        game_id = request.form['game_id']
    
    cur.execute(
        'SELECT p.id, position, king, player_id, ingame_id'
        ' FROM piece p WHERE game_id = %s',
        (game_id,)
    )
    pieces = cur.fetchall()

    players = get_players(game_id)
    player1 = players[0]
    player2 = players[1]

    return render_template('game/index.html', pieces=pieces, \
                        games=games, game_id=game_id, \
                        player1=player1, player2=player2)    


# define Play view at '/play'
# uses 'login_required' decorator defined in 'auth.py'
@bp.route('/play', methods=('GET', 'POST'))
@login_required
def play():
    """Allow user to play moves in game."""
    
    db = get_db()
    cur = db.cursor()

    cur.execute(
        'SELECT u.id, username, game_id FROM users u WHERE u.id = %s',
        (g.user['id'],)
    )
    user_info = cur.fetchone()

    game_id = user_info['game_id']
    
    if game_id == None:
        flash('You are not currently in a game.')
        return redirect(url_for('/'))

    cur.execute(
        'SELECT g.id, player_turn FROM game g WHERE g.id = %s',
        (game_id,)
    )
    game = cur.fetchone()

    players = get_players(game_id)
    player1 = players[0]
    player2 = players[1]

    cur.execute(
        'SELECT p.id, position, king, player_id, ingame_id'
        ' FROM piece p WHERE game_id = %s', (game_id,)
    )
    pieces = cur.fetchall()

    cur.execute(
        'SELECT m.id, player_id, created FROM move m WHERE game_id = %s '
        ' ORDER BY m.id DESC', (game_id,)
    )
    moves = cur.fetchall()

    # check if player still has pieces
    own_pieces = False
    for piece in pieces:
        if piece['player_id'] == g.user['id']:
            own_pieces = True
            break
    
    if player1 is None or player2 is None:
        flash('Still waiting on another player.')
        return render_template('game/play.html', pieces=pieces, player1=player1, player2=player2,
                               game=game, player_id=user_info['id'])

    elif not own_pieces:
        flash('You lost!')
        return render_template('game/play.html', pieces=pieces, player1=player1, player2=player2,
                               game=game, player_id=user_info['id'])

    else:
        legal_pos = legal_positions()

        if request.method == 'POST':
            pos_before = request.form['pos_before']
            pos_after = request.form['pos_after']
            error = None

            player_num = 0
            if g.user['id'] == player1['id']:
                player_num = 1
            elif g.user['id'] == player2['id']:
                player_num = 2

            if game['player_turn'] != player_num:
                error = 'It is not your turn.'

            # make sure a current position is entered
            elif not pos_before:
                error = 'Current piece position is required.'

            # make sure a legal position is input
            elif not pos_before in legal_pos:
                error = 'That is not a legal position.'

            # get piece at current position
            piece_tomove = get_piece(pos_before, game_id)
            if piece_tomove == None or piece_tomove['player_id'] != \
                                              g.user['id']:
                error = 'You have no piece at that location.'
    
            else:
                # make sure a destination is entered
                if not pos_after:
                    error = 'Piece destination is required.'
    
                # set legitimate directions for piece movement
                directions = []
                if piece_tomove['player_id'] == player1['id'] or \
                   piece_tomove['king'] == 1:
                    directions.append(7)
                    directions.append(9)
                if piece_tomove['player_id'] == player2['id'] or \
                   piece_tomove['king'] == 1:
                    directions.append(1)
                    directions.append(3)

                # create list of legal moves
                legal_moves = legal_move_fn(piece_tomove, pos_before, \
                                            pos_after, player1, player2)
                # make sure a legal position is input
                if not pos_after in legal_moves[0]:
                    error = 'That is not a legal move.'
        
                # return error if a piece is in destination
                if get_piece(pos_after, game_id) != None:
                    error = 'There is a piece there already.'
    
            if error is not None:
                flash(error)
            else:
                # move piece and 'king' it if it reached far row
                is_king = piece_tomove['king']
                if piece_tomove['player_id'] == player1['id'] and \
                   pos_after[1] == '8':
                    is_king = 1
                if piece_tomove['player_id'] == player2['id'] and \
                   pos_after[1] == '1':
                    is_king = 1
    
                cur.execute(
                    'UPDATE piece SET position = %s'
                    ' WHERE (id = %s AND game_id = %s)',
                    (pos_after, piece_tomove['id'], game_id)
                )
                cur.execute(
                    'UPDATE piece SET king = %s'
                    ' WHERE (id = %s AND game_id = %s)',
                    (is_king, piece_tomove['id'], game_id)
                )
                # record move
                cur.execute(
                    'INSERT INTO move (player_id, piece_id,'
                    ' position_before, position_after, game_id)'
                    ' VALUES (%s, %s, %s, %s, %s)',
                    (piece_tomove['player_id'], piece_tomove['id'], \
                     pos_before, pos_after, game_id)
                )
                cur.execute(
                    'UPDATE game SET player_turn = %s WHERE id = %s',
                    ((game['player_turn']) % 2 + 1, game_id)
                )
                # if a piece was captured, remove it from the game
                cap_index = 0
                for cap_move in legal_moves[1]:
                    if pos_after == cap_move:
                        cur.execute(
                            'DELETE FROM piece'
                            ' WHERE (id = %s AND game_id = %s)',
                            (legal_moves[2][cap_index]['id'], game_id)
                        )
                    cap_index += 1

                db.commit()

        cur.execute(
            'SELECT p.id, position, king, player_id, ingame_id'
            ' FROM piece p WHERE game_id = %s', (game_id,)
        )
        pieces = cur.fetchall()

        cur.execute(
            'SELECT m.id, player_id, created FROM move m WHERE game_id = %s '
            ' ORDER BY m.id DESC', (game_id,)
        )
        moves = cur.fetchall()

        # check if opponent still has pieces
        opponents = False
        for piece in pieces:
            if piece['player_id'] != g.user['id']:
                opponents = True
                break
    
        if opponents == False and player1 != None and player2 != None:
            flash('You won!')

    return render_template('game/play.html', pieces = pieces, \
                            player1 = player1, player2 = player2, \
                            game = game, player_id = g.user['id'])


# define Moves view at '/moves'
@bp.route('/moves', methods=('GET','POST'))
def moves():
    """Show history of moves in game."""
    db = get_db()
    cur = db.cursor()
    cur.execute(
        'SELECT m.id, m.game_id, m.player_id, username, piece_id, king, '
        ' position_before, position_after, '
        ' created FROM (move m JOIN piece p ON m.piece_id ='
        ' p.id) JOIN users u ON m.player_id = u.id ORDER BY created ASC'
    )
    gamemoves = cur.fetchall()
    return render_template('game/moves.html', gamemoves=gamemoves)


# define Join view at '/join'
@bp.route('/join', methods=('GET','POST'))
@login_required
def join():
    """Allow players to join open games."""
    db = get_db()
    cur = db.cursor()
    error = None

    cur.execute(
        'SELECT g.id, player1_id, player2_id FROM game g'
        ' WHERE player1_id = 0 OR player2_id = 0'
    )
    open_games = cur.fetchone()

    if request.method == 'GET':
        if open_games == None:
            create_game()

    cur.execute(
        'SELECT g.id, player1_id, player2_id FROM game g'
        ' WHERE player1_id = 0 OR player2_id = 0'
    )
    open_games = cur.fetchall()

    cur.execute(
        'SELECT u.id, game_id FROM users u WHERE u.id = %s',
        (g.user['id'],)
    )
    player = cur.fetchone()

    if player['game_id'] != None:
        if player['game_id'] != 0:
            error = 'You are already in an unfinished game.'

    game_id = 1
    if request.method == 'POST':
        game_id = request.form['game_id']

    cur.execute(
        'SELECT g.id, player1_id, player2_id FROM game g'
        ' WHERE g.id = %s',
        (game_id,)
    )
    game = cur.fetchone()

    if error is not None:
        flash(error)
        return redirect(url_for('game.play'))
    elif game is not None:
        if game['player1_id'] == 0:
            cur.execute(
                'UPDATE game SET player1_id = %s WHERE id = %s',
                (g.user['id'], game['id'])
            )
            cur.execute(
                'UPDATE users SET game_id = %s WHERE id = %s',
                (game['id'], g.user['id'])
            )
            populate_board(game['id'], g.user['id'], 1)
            return redirect(url_for('game.play'))
    
        elif game['player2_id'] == 0:
            cur.execute(
                'UPDATE game SET player2_id = %s WHERE id = %s',
                (g.user['id'], game_id)
            )
            cur.execute(
                'UPDATE users SET game_id = %s WHERE id = %s',
                (game['id'], g.user['id'])
            )
            populate_board(game['id'], g.user['id'], 2)
            create_game()
            return redirect(url_for('game.play'))

        db.commit()

    return render_template('game/join.html', games=open_games)


# define Delete view at '/delete'
@bp.route('/<int:id>/delete', methods=('POST',))
@login_required
def delete(id):
    """Delete current game."""
    db = get_db()
    cur = db.cursor()

    cur.execute(
        'SELECT g.id, player1_id, player2_id FROM game g WHERE g.id = %s',
        (id,)
    )
    game = cur.fetchone()

    cur.execute('UPDATE users SET game_id = 0 WHERE id = %s',
        (game['player1_id'],)
    )

    cur.execute('UPDATE users SET game_id = 0 WHERE id = %s',
        (game['player2_id'],)
    )

    cur.execute('DELETE FROM move WHERE game_id = %s', (id,))
    cur.execute('DELETE FROM piece WHERE game_id = %s', (id,))
    cur.execute('DELETE FROM game WHERE id = %s', (id,))

    db.commit()
    return redirect(url_for('game.index'))


# define function to create new game in database
def create_game():
    """Creates a new game in database.  Returns game_id."""
    db = get_db()
    cur = db.cursor()

    cur.execute(
        'INSERT INTO game (player1_id, player2_id)'
        ' VALUES (0, 0)'
    )
    cur.execute(
        'SELECT id FROM game ORDER BY id DESC'
    )
    newgame_id = cur.fetchone()
    db.commit()

    return newgame_id


# define function that populates game with pieces for new user
def populate_board(game_id, player_id, player_number):
    """Fills a board with pieces of newly added player."""
    db = get_db()
    cur = db.cursor()
    legal_pos = legal_positions()

    legal_pos.sort(key = lambda x : x[1])

    init_position = legal_pos[0:12] + legal_pos[20:32]

    if player_number == 1:
        for i in range(0,12):
            cur.execute(
                'INSERT INTO piece (player_id, game_id, ingame_id, position)'
                ' VALUES (%s, %s, %s, %s)',
                (player_id, game_id, (i+1), legal_pos[i])
            )

    elif player_number == 2:
        for i in range(0,12):
            cur.execute(
                'INSERT INTO piece (player_id, game_id, ingame_id, position)'
                ' VALUES (%s, %s, %s, %s)',
                (player_id, game_id, (i+13), legal_pos[31-i])
            )
    db.commit()


# define function that returns the piece at a location in a game
def get_piece(position, game_id):
    """Get a piece and its owner by position.
    Checks that the a piece exists at that position.
    :param position: position of piece to get
    :return: the piece with owner information
    """
    cur = get_db().cursor()
    cur.execute(
        'SELECT p.id, player_id, p.game_id, ingame_id, position, king,'
        ' username FROM piece p JOIN users u ON p.player_id = u.id'
        ' WHERE (p.position = %s AND p.game_id = %s)',
        (position, game_id)
    )
    piece = cur.fetchone()

    return piece


# def function that return an array of the two players in a game
def get_players(game_id):
    """Get the players in a game by game id number."""
    cur = get_db().cursor()
    cur.execute(
        'SELECT player1_id, player2_id FROM game WHERE id = %s', (game_id,)
    )
    players = cur.fetchone()

    if players == None:
        return [None, None]

    cur.execute(
        'SELECT id, username, game_id FROM users WHERE id = %s',
        (players['player1_id'],)
    )
    player1 = cur.fetchone()

    cur.execute(
        'SELECT id, username, game_id FROM users WHERE id = %s',
        (players['player2_id'],)
    )
    player2 = cur.fetchone()

    return [player1, player2]


# define function that defines legal squares
def legal_positions():
    """Return a list of legal positions in checkers."""
    l_p = []
    for a in 'aceg':
        for i in '1357':
            l_p.append(a + i)

    for a in 'bdfh':
        for i in '2468':
            l_p.append(a + i)

    return l_p


# define function that defines legal moves for a given piece
def legal_move_fn(piece, pos_before, pos_after, player1, player2):
    """Return a list of legal moves for a piece stored in first element.
    Store capturing moves in second element and pieces captured in third.    
    """
    directions = []
    if piece['player_id'] == player1['id'] or piece['king'] == 1:
        directions.append(7)
        directions.append(9)
    if piece['player_id'] == player2['id'] or piece['king'] == 1:
        directions.append(1)
        directions.append(3)
    
    game_id = piece['game_id']
    legal_moves = [[],[],[]]
    for direction in directions:
        temp_sqr = next_square(pos_before, direction)
        if temp_sqr != None:
            if get_piece(temp_sqr, game_id) == None:
                legal_moves[0].append(temp_sqr)
            elif get_piece(temp_sqr, game_id)['player_id'] != g.user['id']:
                if next_square(temp_sqr, direction) != None:
                    cap_piece = get_piece(temp_sqr, game_id)
                    temp_sqr = next_square(temp_sqr, direction)
                    if temp_sqr != None and \
                       get_piece(temp_sqr, game_id) == None:
                        legal_moves[0].append(temp_sqr)
                        legal_moves[1].append(temp_sqr)
                        legal_moves[2].append(cap_piece)
    return legal_moves


# define function to find adjacent legal squares
def next_square(current_square, direction):
    """Find the next available square in the given direction.
    :param direction: directions as numpad orientation.
    """
    
    result_a = current_square[0]
    result_i = current_square[1]

    if direction in [1, 2, 3]:
        result_i = chr(ord(current_square[1]) - 1)
    elif direction in [7, 8, 9]:
        result_i = chr(ord(current_square[1]) + 1)

    if direction in [1, 4, 7]:
        result_a = chr(ord(current_square[0]) - 1)
    elif direction in [3, 6, 9]:
        result_a = chr(ord(current_square[0]) + 1)

    result = result_a + result_i
    
    legal_pos = legal_positions()

    if not result in legal_pos:
        result = None

    return result

