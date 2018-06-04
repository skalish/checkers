# File that creates connection to SQLite database.
import psycopg2
import psycopg2.extras
import click
from flask import current_app, g
# current_app points to Flask application handling request
# g is a special object unique for each request
from flask.cli import with_appcontext


def get_db():
    """Connect to the application's configured database. The connection is
    unique for each request and will be reused if this is called again.
    """

    if 'db' not in g:
        g.db = psycopg2.connect(dbname="checker", user="skalish",
                                cursor_factory=psycopg2.extras.RealDictCursor)
    return g.db


def close_db(e=None):
    """If this request connected to the database, close the connection."""
    db = g.pop('db', None)
    cur = g.pop('cur', None)

    if db is not None:
        db.close()
    if cur is not None:
        cur.close()


def init_db():
    """Clear existing data and create new tables."""
    db = get_db()
    cur = db.cursor()

    with current_app.open_resource('schema.sql') as f:
        cur.execute(f.read().decode('utf8'))
    
    from checker.game import create_game
    create_game()

    db.commit()


@click.command('init-db')
@with_appcontext
def init_db_command():
    """Defines a command-line command 'init-db' that calls init_db() and
    shows a success message to the user.
    """
    init_db()
    click.echo('Initialized the database.')


def init_app(app):
    """Register database functions with the Flask app. This is called by
    the application factory.
    """
    # tell Flask to call 'close_db' when cleaning up after returning response
    app.teardown_appcontext(close_db)
    # add new command to be called with flask command
    app.cli.add_command(init_db_command)
