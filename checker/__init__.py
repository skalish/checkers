# Bare minimum file to run app.
# Contains the application factory and tells Python that the 'checker'
#  directory should be treated as a package.
import os

from flask import Flask


# application factory function
def create_app(test_config=None):
    """Create and configure an instance of the Flask application."""
    # create Flask instance
    # '__name__' gives name of current Python module
    # 'inst...' tells that config files are relative to instance folder
    app = Flask(__name__, instance_relative_config=True)
    # set some default configuration
    app.config.from_mapping(
        # a default secret that should be overridden by instance config
        SECRET_KEY='jJjw0jileutrd6X2PivXvdhwKztEIAzJ',
        # store the database in the instance folder
        DATABASE=os.path.join(app.instance_path, 'checker.sqlite'),
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # a simple page that says hello
    @app.route('/hello')
    def hello():
        return 'Hello, World!'

    # register the database commands
    from . import db
    db.init_app(app)

    # apply the blueprints to the app
    from . import auth
    app.register_blueprint(auth.bp)
    from . import game
    app.register_blueprint(game.bp)

    # make url_for('index') == url_for('blog.index')
    app.add_url_rule('/', endpoint='index')

    return app
