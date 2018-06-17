# Blueprint for authentication functions
import functools

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
# session is a dict that stores data across requests
from werkzeug.security import check_password_hash, generate_password_hash

from checker.db import get_db

# create a Blueprint named 'auth' defined in current Python module
# all associated URLs with have prefix '/auth/' prepended
bp = Blueprint('auth', __name__, url_prefix='/auth')


def login_required(view):
    """View decorator that redirects anonymous users to the login page.."""
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('auth.login'))

        return view(**kwargs)

    return wrapped_view


# run before view function regardless of requested url
@bp.before_app_request
def load_logged_in_user():
    """If a user id is stored in the session, load the user object from the
    database into ''g.user''.
    """
    user_id = session.get('user_id')

    if user_id is None:
        g.user = None
    else:
        cur = get_db().cursor()
        cur.execute(
            'SELECT * FROM users WHERE id = %s', (user_id,)
        )
        g.user = cur.fetchone()

# define Register view at '/auth/register'
@bp.route('/register', methods=('GET', 'POST'))
def register():
    """Register a new user.
    Validates that the username is not already taken. Hashes the password
    for security.
    """
    from checker.game import create_game
    from checker.game import populate_board

    if request.method == 'POST':
        # get username and password entered by user
        username = request.form['username']
        password = request.form['password']
        # load database
        db = get_db()
        cur = db.cursor()
        cur.execute(
            'SELECT id FROM users WHERE username = %s', (username,)
        )
        error = None

        # check that a username is entered, a password is entered, and that
        # username is not already registered
        if not username:
            error = 'Username is required.'
        elif not password:
            error = 'Password is required.'
        elif cur.fetchone() is not None:
            error = 'User {} is already registered.'.format(username)

        if error is None:
            # the name is available, store it in the database and go to the
            # login page
            cur.execute(
                'INSERT INTO users (username, password) VALUES (%s, %s)',
                (username, generate_password_hash(password))
            )
            cur.execute(
                'SELECT id FROM users WHERE username = %s', (username,)
            )
            user = cur.fetchone()

            db.commit()
            return redirect(url_for('auth.login'))

        flash(error)

    return render_template('auth/register.html')


# define Login view at '/auth/login'
@bp.route('/login', methods=('GET', 'POST'))
def login():
    """Log in a registered user by adding the user id to the session."""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        cur = db.cursor()
        error = None
        cur.execute(
            'SELECT * FROM users WHERE username = %s', (username,)
        )
        user = cur.fetchone()

        if user is None:
            error = 'Incorrect username.'
        elif not check_password_hash(user['password'], password):
            error = 'Incorrect password.'

        if error is None:
            # store the user id in a new session and return to the index
            session.clear()
            session['user_id'] = user['id']
            if user['game_id'] != None and user['game_id'] > 0:
                return redirect(url_for('game.play'))
            else:
                return redirect(url_for('game.join'))

        flash(error)

    return render_template('auth/login.html')

# define Logout view at '/auth/logout'
@bp.route('/logout')
def logout():
    """Clear the current session, including the stored user id."""
    session.clear()
    return redirect(url_for('index'))

