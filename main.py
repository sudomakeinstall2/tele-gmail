import json

from hashing import make_secure

import flask
import httplib2

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, current_user, login_required

from apiclient import discovery
from oauth2client import client
import os
basedir = os.path.abspath(os.path.dirname(__file__))

app = flask.Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

with open('secret_key.txt') as f:
    key = f.read().strip()
    app.secret_key = key

lm = LoginManager()
lm.init_app(app)
lm.login_view = 'login'
db = SQLAlchemy(app)


#### models
class User(db.Model):
    
    __tablename__ = 'users'
    
    user_id = db.Column(db.Integer, primary_key = True)
    email = db.Column(db.String(120), unique = True)
    previous = db.Column(db.String(120))
    chat_id = db.Column(db.String(120))
    credentials = db.Column(db.Text)
    
    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        try:
            return unicode(self.user_id)  # python 2
        except NameError:
            return str(self.user_id)  # python 3

    def __repr__(self):
        return '<User %r>' % (self.email)


#### end models

@lm.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
    
@app.before_request
def before_request():
    flask.g.user = current_user    

@app.route('/login', methods=['GET', 'POST'])
def login():
    if flask.g.user is not None and flask.g.user.is_authenticated and 'credentials' not in flask.session:
        print 'we know the user'
        return flask.redirect(flask.url_for('index'))
    elif 'credentials' in flask.session:
        print 'credentials is in session'
        c = json.loads(flask.session['credentials'])
        email = c['id_token']['email']
        user = User.query.filter_by(email = email).first()
        if user :
            print 'user in database'
            user.credentials = flask.session['credentials']
            db.session.commit()
        else:
            print 'create new user in database'
            user = User()
            user.email = email
            user.credentials = flask.session['credentials']
            db.session.add(user)
            db.session.commit()
        remember = True
        flask.session.pop('remember_me',None)
        flask.session.pop('credentials',None)
        login_user(user, remember)
        print 'logged in successful'
        return flask.redirect(flask.url_for('index'))
    else:
        print 'you should oauth'
        return flask.redirect(flask.url_for('oauth2callback'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return flask.redirect(flask.url_for('index'))

@app.route('/revoke')
@login_required
def revoke():
    credentials = client.OAuth2Credentials.from_json(flask.g.user.credentials)
    http = credentials.authorize(httplib2.Http())
    credentials.revoke(http)
    db.session.delete(flask.g.user)
    db.session.commit()
    logout_user()
    return flask.redirect(flask.url_for('index'))

@app.route('/')
def index():
    message = ""
    if flask.g.user and flask.g.user.is_authenticated:
        if flask.g.user.chat_id:
            message = "you are already registered."
        else:
            message = "send this to @telegmailbot in telegram:\n" + \
            "<b>" + \
            "/register " + \
             make_secure(str(flask.g.user.user_id))
             
    return flask.render_template('mails.html',message=message)

    
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/userinfo.email',
    #'https://www.googleapis.com/auth/userinfo.profile',
    # Add other requested scopes.
]


@app.route('/oauth2callback')
def oauth2callback():
  flow = client.flow_from_clientsecrets(
      'client_secrets.json',
      scope=' '.join(SCOPES),
      redirect_uri=flask.url_for('oauth2callback', _external=True))
  flow.params['access_type'] = 'offline'
  flow.params['approval_prompt'] = 'force'
  if 'code' not in flask.request.args:
    print 'code not in request'
    auth_uri = flow.step1_get_authorize_url()
    return flask.redirect(auth_uri)
  else:
    print 'code in request'
    auth_code = flask.request.args.get('code')
    credentials = flow.step2_exchange(auth_code)
    flask.session['credentials'] = credentials.to_json()
    print >> open('log.txt','w') , credentials.to_json()
    return flask.redirect(flask.url_for('login'))


if __name__ == '__main__':  
  app.debug = True
  app.run(host='0.0.0.0')
