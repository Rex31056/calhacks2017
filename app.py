from flask import Flask
from flask import render_template, request, redirect, url_for
import pymongo
from pymongo import MongoClient
import time

app = Flask(__name__)
client = MongoClient()
db = client['schedule']

@app.route('/')
def homepage():
    return render_template('insert.html')

@app.route('/<name>')
def schedule(name):
    events = []
    query = db[name].find().sort('Date')
    for i in query:
        events.append(i)
    return str(events)



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
