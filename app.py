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
    return render_template('homepage.html')

@app.route('/insert', methods=['POST', 'GET'])
def insert():
    if request.method == 'POST':
        name = request.form['username']
        date = request.form['date']
        start_time = int(request.form(['start time']))
        end_time = int(request.form(['end time']))
        event = request.form(['event name'])
        post = {"date": date,
                "start": start_time,
                "end": end_time,
                "event": event}
        inserted_event = db[name].insert_one(post)
        return redirect(url_for(homepage))
    else:
        return render_template('error.html')
