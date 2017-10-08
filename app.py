from flask import Flask, g, render_template, request, redirect, url_for, session, flash
import pymongo
from pymongo import MongoClient
import time
import datetime
from flask_oauthlib.client import OAuth, OAuthException
from facebook import GraphAPI
import bson
import json

app = Flask(__name__)

SECRET_KEY = 'peyrin'
DEBUG = True
FACEBOOK_APP_ID = '188477911223606'
FACEBOOK_APP_SECRET = '621413ddea2bcc5b2e83d42fc40495de'

app.debug = DEBUG
app.secret_key = SECRET_KEY
oauth = OAuth(app)

client = MongoClient()
database = client['schedule']


facebook = oauth.remote_app(
    'facebook',
    consumer_key=FACEBOOK_APP_ID,
    consumer_secret=FACEBOOK_APP_SECRET,
    request_token_params={'scope': 'email'},
    base_url='https://graph.facebook.com',
    request_token_url=None,
    access_token_url='/oauth/access_token',
    access_token_method='GET',
    authorize_url='https://www.facebook.com/dialog/oauth'
)


@app.route('/')
def homepage():
    return redirect(url_for('login'))

@app.route('/index')
def index():
    me = facebook.get('/me')
    user = 'u' + str(me.data['id'])
    return render_template('insert.html', user=user)

@app.route('/login')
def login():
    callback = url_for(
        'facebook_authorized',
        next=request.args.get('next') or request.referrer or None,
        _external=True
    )
    return facebook.authorize(callback=callback)

@app.route('/login/authorized')
def facebook_authorized():
    resp = facebook.authorized_response()
    if resp is None:
        return 'Access denied: reason=%s error=%s' % (
            request.args['error_reason'],
            request.args['error_description']
        )
    if isinstance(resp, OAuthException):
        return 'Access denied: %s' % resp.message

    session['oauth_token'] = (resp['access_token'], '')
    me = facebook.get('/me')
    #return 'Logged in as id=%s name=%s redirect=%s' % \
    #        (me.data['id'], me.data['name'], url_for('index'))
    return redirect(url_for('index'))

@facebook.tokengetter
def get_facebook_oauth_token():
    return session.get('oauth_token')

#@app.before_request
#def get_current_user():
#    me = facebook.get('/me')
#    g.user = User(id=str(me.data['id']), name=me.data['name'],
#                        profile_url=me.data['link'],
#                        access_token=me.data['access_token'])

@app.route('/<name>')
def schedule(name):
    me = facebook.get('/me')
    if name[1:] == str(me.data['id']):
        today = datetime.datetime.now()
        today_date = str(today.year) + '-' + '{:02d}'.format(today.month) + '-' + '{:02d}'.format(today.day)
        query = database[name].find({'date': today_date})

        schedule = DaySchedule()
        event_count = []
        for i in query:
            event_count.append(i)
        for j in event_count:
            schedule.add_event(Event(j['event'], j['date'], j['start'], j['end'], j['urgency']))
        conflict, schedule1_events, schedule2_events = schedule.generate_schedule()
        schedule1_strings = []
        schedule2_strings = []
        for k in range(len(schedule1_events)):
            schedule1_strings.append([])
            schedule1_strings[k].append(str(schedule1_events[k].name))
            schedule1_strings[k].append(str(schedule1_events[k].start))
            schedule1_strings[k].append(str(schedule1_events[k].end))
        for m in range(len(schedule2_events)):
            schedule2_strings.append([])
            schedule2_strings[m].append(str(schedule2_events[m].name))
            schedule2_strings[m].append(str(schedule2_events[m].start))
            schedule2_strings[m].append(str(schedule2_events[m].end))
        schedule1_length = len(schedule1_events)
        schedule2_length = len(schedule2_events)
        return render_template('display_schedule.html', conflict = conflict, schedule1 = schedule1_strings,
            schedule2 = schedule2_strings, schedule1_length = schedule1_length,
            schedule2_length = schedule2_length, today = today_date)
    else:
        return 'You do not have permission for this.'


@app.route('/insert', methods=['POST', 'GET'])
def insert():
    if request.method == 'POST':
        me = facebook.get('/me')
        user = 'u' + str(me.data['id'])
        date = request.form['Date']
        start_time = request.form['StartTime']
        end_time = request.form['EndTime']
        event = request.form['Name']
        try:
            urgent = request.form['Urgent']
            urgent = 1
        except:
            urgent = 0
        post = {"date": date,
                "start": start_time,
                "end": end_time,
                "event": event,
                "urgency": urgent}
        inserted_event = database[user].insert_one(post)
        return redirect(url_for('index'))
    else:
        return render_template('error.html')

class Event:
    def __init__(self, Name, Date, StartTime = None, EndTime = None, urgency = False, time_span = 0):
        self.name = Name
        self.date = Date
        self.start = StartTime
        self.end = EndTime
        self.urgency = urgency
        self.time_span = time_span
        if StartTime is not None and EndTime is not None:
            self.priority = 1
            self.time_span = (datetime.datetime.strptime(EndTime, '%H:%M') - datetime.datetime.strptime(StartTime, '%H:%M')).seconds
        else:
            self.priority = 0

class DaySchedule:
    def __init__(self):
        self.priority0 = []
        self.priority1 = []
        self.urgent0 = 0
    def add_event(self, event):
        """adds an event to the day
        >>> day = DaySchedule()
        >>> event1 = Event("Get Ready", "08-14-1999", None, None, False)
        >>> event2 = Event("Sleep", "08-14-1999", None, None, True)
        >>> timeEvent1 = Event("Leave", "08-14-1999", 123456, 123480)
        >>> timeEvent2 = Event("Come", "08-14-1999", 123470, 123490)
        >>> day.add_event(event1)
        >>> day.add_event(event2)
        >>> day.add_event(timeEvent1)
        >>> day.add_event(timeEvent2)
        >>> day.priority0[0] is event2
        True
        >>> day.priority0[1] is event1
        True
        >>> day.priority1[0] is timeEvent1
        True
        >>> day.priority1[1] is timeEvent2
        True
        """
        if event.priority == 0:
            if event.urgency:
                self.priority0.insert(self.urgent0, event)
                self.urgent0 += 1
            else:
                self.priority0.append(event)
        else:
            self.priority1.append(event)

    def is_conflict(self, event1, event2):
        if event2.start < event1.end:
            return True
        return False

    def check_for_conflicts(self):
        """checks for conflicts in a schedule
        >>> day = DaySchedule()
        >>> timeEvent1 = Event("Leave", "08-14-1999", 123456, 123480)
        >>> timeEvent2 = Event("Come", "08-14-1999", 123470, 123490)
        >>> day.add_event(timeEvent1)
        >>> day.add_event(timeEvent2)
        >>> x = day.check_for_conflicts()
        >>> x[0] is timeEvent1
        True
        >>> x[1] is timeEvent2
        True
        """
        i = 0
        while i < len(self.priority1)-1:
            if self.is_conflict(self.priority1[i], self.priority1[i+1]):
                return self.priority1[i], self.priority1[i+1]
        return True

    def generate_schedule(self):
        unused_events = []
        if self.check_for_conflicts() == True:
            schedule = self.priority1[:]
            for event in self.priority0:
                needed_time = event.time_span
                i = 0
                unused = True #Did you succesfully fit the event in your schedule?
                while i < len(self.schedule) - 1:
                    if unused and needed_time <= schedule[i+1].start - schedule[i].end:
                        schedule.insert(i+1, make_timed_event(event, schedule[i].end, schedule[i].end + needed_time))
                        unused = False
                if unused:
                    unused_events.append(unused)
            return True, schedule, unused_events
        else:
            return False, self.check_for_conflicts()

    def make_timed_event(self, event, start_time, end_time):
        return Event(event.name, event.date, start_time, end_time)
