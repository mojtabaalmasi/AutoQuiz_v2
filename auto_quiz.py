from __init__ import *
import os
from sqlite3 import dbapi2 as sqlite3
from contextlib import closing
from flask import Flask, request, session, g, redirect, url_for, abort, \
     render_template, flash
import xml.etree.ElementTree as ET
import json
from werkzeug.contrib.cache import SimpleCache
import time
import datetime

from fileio_func import read_xml
from database_func import check_user, user_registration, user_login, log_exercise_db, get_topic_info, fetch_questions

@app.route('/topic/<topic_id_marked>')
def topic_question_lst(topic_id_marked):
    topic_id = int(topic_id_marked) - 1
    # print "topic id = {0}".format(topic_id)
    user_id = user_cache.get('user_id')
    questions = fetch_questions(topic_id, user_id)
    last_idx = len(questions) - 1
    for i in range(last_idx):
        next_cache.set(questions[i]["id"], questions[i + 1]["id"])
    if last_idx >= 0:
        next_cache.set(questions[last_idx]["id"], -1)
    return json.dumps(questions)

@app.route('/exercise/', methods=['GET', 'POST'])
def exercise_section():
    # request.args.get('name', '')
    if request.method == 'POST':
        # print request.values
        # print request.args
        question_id = request.form['question_id']
        # next_id = request.form['next_id']
        # next_id = session["question_next"][int(question_id)] # doesn't work because session only works within this temp thread
        next_id = next_cache.get(int(question_id))
    else:
        return redirect(url_for('welcome'))
    question_fname = "Q{0}.xml".format(question_id)
    # print "question file name {0}".format(question_fname)
    question, answers, correct_ans_id, hint = read_xml(question_fname, os.path.join(app.root_path, 'static', 'dataset'))
    # print "next question is {0}".format(next_id)

    return render_template('exercise.html', question=question, answers=answers, \
        question_id=question_id, correct_ans_id=correct_ans_id, hint=hint, next_id=next_id)
    # return render_template('exercise.html', **locals())

@app.route('/challenge/', methods=['GET', 'POST'])
def challenge_section():
    question_id = 1
    question_fname = "Q{0}.xml".format(question_id)
    # print "question file name {0}".format(question_fname)
    question, answers, correct_ans_id, hint = read_xml(question_fname, os.path.join(app.root_path, 'static', 'dataset'))
    # print "next question is {0}".format(next_id)

    return render_template('challenge.html', question=question, answers=answers, \
        question_id=question_id, correct_ans_id=correct_ans_id, hint=hint)

# https://segmentfault.com/a/1190000007605055
@app.route('/log_exercise', methods=['GET', 'POST'])
def log_exercise_result():
    jsondata = request.form.get('data')
    data = json.loads(jsondata)
    question_id = data["question_id"]
    correctness = data["correctness"]
    # timestamp = time.time()
    # timestring = datetime.datetime.fromtimestamp(timestamp).strftime('%Y/%m/%d %H:%M:%S')
    user_id = user_cache.get('user_id')
    log_ip = request.remote_addr
    log_time = datetime.datetime.now()
    # print "user {0} do exe {1} at time {2}, correctness: {3}".format(user_id, question_id, timestring, correctness)
    result = log_exercise_db(question_id, user_id, correctness, log_ip, log_time)
    if result:
        success = 1
    else:
        success = 0
    info = [{
            "success": success
        }
    ]
    return json.dumps(info)

@app.route('/check_user', methods=['GET', 'POST'])
def check_user_exists():
    jsondata = request.form.get('data')
    data = json.loads(jsondata)
    username = data["username"]
    if check_user(username):
        success = 0
    else:
        success = 1
    info = [{
            "success": success
        }
    ]
    return json.dumps(info)

@app.route('/home/', methods=['GET', 'POST'])
def welcome():
    if request.method == 'POST':
        # if it is login, not logout
        status = request.form.get('confirm_logout', '0')
        if str(status) == '1':
            # logout
            username = user_cache.get('user_name')
            user_cache.clear()
            show_msg = True
            msg = ['success', 'Done', 'You successfully logged out {0}'.format(username)]
            login = False
            username=None
        else:
            # get login / register information
            username = request.form.get('username', '')
            password = request.form.get('password', '')
            confirm = request.form.get('confirm', '')
            to_register = len(request.form.get('reg', '')) > 0 # on or None
            # print "User Name is: {0}, password {1}, confirm {2}, to register {3}.".format(username, password, confirm, to_register)
            # try to login
            if to_register:
                # print "register"
                log_time = datetime.datetime.now()
                reg_success, user_id = user_registration(username, password, log_time)
                if reg_success:
                    show_msg = True
                    msg = ['success', 'Welcome', 'You are registered in our system as {0}'.format(username)]
                    login = True
                    user_cache.set('user_name', username)
                    user_cache.set('user_id', user_id)
                else:
                    show_msg = True
                    msg = ['danger', 'Sorry', 'The user name "{0}" you came up with already exists in our system. Please try another one.'.format(username)]
                    login = False
            else:
                # login
                # print "login"
                login_success, user_id = user_login(username, password)
                if login_success:
                    show_msg = True
                    msg = ['success', 'Hi {0}'.format(username), 'Welcome back!'.format(username)]
                    login = True
                    user_cache.set('user_name', username)
                    user_cache.set('user_id', user_id)
                else:   
                    login = False
                    show_msg = True
                    msg = ['danger', 'ERROR', 'Incorrect Password or User Name; Please try again, or contact us at {0} if you need help.'.format(OFFICIAL_MAILBOX)]
    else:
        # check it up in cache
        username = user_cache.get('user_name')
        if username is None:
            # userip = request.remote_addr
            login = False
            # message to show when not logged in
            show_msg = True
            msg = ['warning', 'WARNING', 'You are not logged in, so all your records will not be logged.']
        else:
            login = True
            # no message
            show_msg = False
            msg = []

    # fetch personal topic information from database
    user_id = user_cache.get('user_id')
    all_topics, topic_links = get_topic_info(user_id)

    return render_template('welcome.html', login=login, username=username, \
        all_topics=all_topics, topic_links=topic_links,\
        show_msg=show_msg, msg=msg)


@app.route('/')
def default_entry():
    return redirect(url_for('welcome'))

if __name__ == '__main__':
    app.run(debug=False)