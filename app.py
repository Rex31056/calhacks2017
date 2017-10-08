from flask import Flask
from flask import render_template, request, redirect, url_for, session
import pymongo
from pymongo import MongoClient
import time
from flask_oauth import OAuth

app = Flask(__name__)

SECRET_KEY = 'peyrin'
DEBUG = True
FACEBOOK_APP_ID = '188477911223606'
FACEBOOK_APP_SECRET = '621413ddea2bcc5b2e83d42fc40495de'

app.debug = DEBUG
app.secret_key = SECRET_KEY
oauth = OAuth()

client = MongoClient()
db = client['schedule']


facebook = oauth.remote_app('facebook',
    base_url='https://graph.facebook.com/',
    request_token_url=None,
    access_token_url='/oauth/access_token',
    authorize_url='https://www.facebook.com/dialog/oauth',
    consumer_key=FACEBOOK_APP_ID,
    consumer_secret=FACEBOOK_APP_SECRET,
    request_token_params={'scope': 'email'}
)


#@app.route('/')
#def index():
#    return redirect(url_for('login'))

@app.route('/')
def homepage():
    return render_template('insert.html')

@app.route('/login')
def login():
    return facebook.authorize(callback=url_for('facebook_authorized',
        next=request.args.get('next') or request.referrer or None,
        _external=True))

@app.route('/login/authorized')
@facebook.authorized_handler
def facebook_authorized(resp):
    if resp is None:
        return 'Access denied: reason=%s error=%s' % (
            request.args['error_reason'],
            request.args['error_description']
        )
    session['oauth_token'] = (resp['access_token'], '')
    me = facebook.get('/me')
    return 'Logged in as id=%s name=%s redirect=%s' % \
        (me.data['id'], me.data['name'], request.args.get('next'))

@facebook.tokengetter
def get_facebook_oauth_token():
    return session.get('oauth_token')


@app.route('/<name>')
def schedule(name):
    events = []
    query = db[name].find().sort('Date')
    for i in query:
        events.append(i)
    return render_template('display_schedule.html', events=events)



@app.route('/insert', methods=['POST', 'GET'])
def insert():
    if request.method == 'POST':
        user = request.form['User']
        date = request.form['Date']
        start_time = request.form['StartTime']
        end_time = request.form['EndTime']
        event = request.form['Name']
        post = {"date": date,
                "start": start_time,
                "end": end_time,
                "event": event}
        inserted_event = db[user].insert_one(post)
        return redirect(url_for('homepage'))
    else:
        return render_template('error.html')
