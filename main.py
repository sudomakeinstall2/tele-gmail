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
        credentials = client.OAuth2Credentials.from_json(flask.g.user.credentials)
        if credentials.access_token_expired:
            print 'credentials expired go ouath'
            return flask.redirect(flask.url_for('oauth2callback'))
        else:
            print 'credentials okay go to index'
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
    return flask.redirect(flask.url_for('login'))

@app.route('/')
@login_required
def index():
  #flask.session['credentials'] = """{"_module": "oauth2client.client", "scopes": ["https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/gmail.readonly"], "token_expiry": "2050-08-04T23:35:52Z", "id_token": {"aud": "785316539664-vgrvgpha6alj44q4jtld2mqfl8i71kid.apps.googleusercontent.com", "iss": "accounts.google.com", "email_verified": true, "at_hash": "ZoioOZIoObKRHn_KcAVZ0Q", "exp": 1470353752, "azp": "785316539664-vgrvgpha6alj44q4jtld2mqfl8i71kid.apps.googleusercontent.com", "iat": 1470350152, "email": "askari.saeed@gmail.com", "sub": "101928282744361867794"}, "access_token": "ya29.Ci81A1jjDj33wnCgvCIvRDfhnq3FmdMB1GnRNbmSOiCTZvdPoWBVnYROJPer0nhMkg", "token_uri": "https://accounts.google.com/o/oauth2/token", "invalid": false, "token_response": {"access_token": "ya29.Ci81A1jjDj33wnCgvCIvRDfhnq3FmdMB1GnRNbmSOiCTZvdPoWBVnYROJPer0nhMkg", "token_type": "Bearer", "expires_in": 3600, "refresh_token": "1/KtpHewMGrvUzJutFspUbZvLCpvipso4vA_j2wU5u-Sg", "id_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6IjBmMmY1ZTMxNjE0YmIxYTc4ZjkxNTYxZWIxMmE0M2I5ZjUwNTQ2NDMifQ.eyJpc3MiOiJhY2NvdW50cy5nb29nbGUuY29tIiwiYXRfaGFzaCI6IlpvaW9PWklvT2JLUkhuX0tjQVZaMFEiLCJhdWQiOiI3ODUzMTY1Mzk2NjQtdmdydmdwaGE2YWxqNDRxNGp0bGQybXFmbDhpNzFraWQuYXBwcy5nb29nbGV1c2VyY29udGVudC5jb20iLCJzdWIiOiIxMDE5MjgyODI3NDQzNjE4Njc3OTQiLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZSwiYXpwIjoiNzg1MzE2NTM5NjY0LXZncnZncGhhNmFsajQ0cTRqdGxkMm1xZmw4aTcxa2lkLmFwcHMuZ29vZ2xldXNlcmNvbnRlbnQuY29tIiwiZW1haWwiOiJhc2thcmkuc2FlZWRAZ21haWwuY29tIiwiaWF0IjoxNDcwMzUwMTUyLCJleHAiOjE0NzAzNTM3NTJ9.qEcbP9vuyy9jROu11AmXJ3ikxkM4vxfaRjfIld5oBH2CHTjk9wH100UiKmxLNQLl2FKofCHVCddAa5Vjkr2WlZveVmMYpo5H7hn7MnAtTcT2GgFbHd360W3Z0nSiAEs7wwIrDBbs-hb_XLiDEJ2A-luDnYmEUEP5rEMdjz5KqwXL3DweAf1tp3__3i1pBWUqL2gVCi5JD8jBQxGtIWakhsPRAy8Irqgxg-GVF9fx9eVCVdbF32UBXFd66kX36LRoM9Lees16LoJNGrLcvTUNyf0EDBmVANPx4sCjGfBujtIoL6kHJ1oxapunRwbTTOIo7SXSWHDMxtAl_M2XkXJl6Q"}, "client_id": "785316539664-vgrvgpha6alj44q4jtld2mqfl8i71kid.apps.googleusercontent.com", "token_info_uri": "https://www.googleapis.com/oauth2/v3/tokeninfo", "client_secret": "d0V_EMXeu9Xo1Zl8xCtJWmM1", "revoke_uri": "https://accounts.google.com/o/oauth2/revoke", "_class": "OAuth2Credentials", "refresh_token": "1/KtpHewMGrvUzJutFspUbZvLCpvipso4vA_j2wU5u-Sg", "user_agent": null}"""
  #if 'credentials' not in flask.session:
  #  print 'credentials not in session'
  #  return flask.redirect(flask.url_for('oauth2callback'))
  credentials = client.OAuth2Credentials.from_json(flask.g.user.credentials)
  if credentials.access_token_expired:
    print 'credentials expired in index'
    return flask.redirect(flask.url_for('oauth2callback'))
  else:
    print 'credentials okay in index'
    return make_secure(str(flask.g.user.user_id))
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('gmail', 'v1', http=http)
    l = ListMessagesWithLabels(service, flask.g.user.email)
    mails = []
    for x in l:
        message = GetMessage(service, flask.g.user.email, x['id'])
#        print >> open('log.txt','w') , message['payload']['headers']
        mail = Mail()
        mail.snippet = message['snippet']
        for x in message['payload']['headers']:
            if x['name'] == 'Subject':
                mail.subject = x['value']
            elif x['name'] == 'Date':
                mail.date = x['value']
            elif x['name'] == 'From':
                mail.from_ = x['value']
        mails.append(mail)
        #print mails[-1]
    return flask.render_template("mails.html", mails=mails)
    
    
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
