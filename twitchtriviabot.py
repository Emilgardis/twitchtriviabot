#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@author: cleartonic
"""
import random
import json
import pandas as pd
import collections
import time
import socket
import re
import configparser
import os
import traceback
import inflect

# SETTINGS

p = inflect.engine()

class var():
    infomessage = 'Twitch Trivia Bot loaded. Version 0.1.3. Developed by cleartonic.'

    # SETTINGS FOR END USERS
    # Specify the filename (default "triviaset")
    trivia_filename = 'trivia'
    # Specify the file type. CSV (MUST be UTF-8), XLS, XLSX
    trivia_filetype = 'csv'

    # Total questions to be answered for trivia round
    trivia_questions = 'INIT'
    # Type of hints used, easy or harder
    trivia_hintmode = 'INIT'
    # Seconds to 1st hint after question is asked
    trivia_hinttime_1 = 'INIT'
    # Seconds to 2nd hint after question is asked
    trivia_hinttime_2 = 'INIT'
    # current hint in mode 1, [hinttype,letter_index,currenthint]
    hint_current = [-1, [-1], '']
    # Seconds until the question is skipped automatically
    trivia_skiptime = 'INIT'
    # Seconds to wait after previous question is answered before asking next question
    trivia_questiondelay = 'INIT'
    # BONUS: How much points are worth in BONUS round
    trivia_bonusvalue = 'INIT'
    trivia_num_answers = 1
    trivia_answered_by = []
    trivia_wait_for_next = 1
    trivia_answered_wait = 0
    admins = 'INIT'

    # FUNCTION VARIABLES
    if trivia_filetype == 'csv':                # open trivia source based on type
        ts = pd.read_csv(trivia_filename+"."+trivia_filetype)
    if trivia_filetype == 'xlsx' or trivia_filetype == 'xls':
        # open trivia source based on type
        ts = pd.read_excel(trivia_filename+"."+trivia_filetype)
    if trivia_filetype != 'xlsx' and trivia_filetype != 'xls' and trivia_filetype != 'csv':
        print("Warning! No file loaded. Type !stopbot and try loading again.")
    # Dynamic # of rows based on triviaset
    tsrows = ts.shape[0]
    # Set columns in quizset to same as triviaset
    qs = pd.DataFrame(columns=list(ts))
    # Dictionary holding user scores, kept in '!' and loaded/created upon trivia. [1,2,3] 1: Session score 2: Total trivia points 3: Total wins
    userscores = {}
    COMMANDLIST = ["!triviastart", "!triviaend", "!top3", "!hint", "!bonus", "!score", "!next",
                   "!stop", "!loadconfig", "!backuptrivia", "!loadtrivia", "!creator", "!ask"]  # All commands
    SWITCH = True                           # Switch to keep bot connection running
    trivia_active = False                   # Switch for when trivia is being played
    # Switch for when a question is actively being asked
    trivia_questionasked = False
    # Time when the last question was asked (used for relative time length for hints/skip)
    trivia_questionasked_time = 0
    # 0 = not asked, 1 = first hint asked, 2 = second hint asked
    trivia_hintasked = 0
    session_questionno = 0                  # Question # in current session
    # How much each question is worth (altered by BONUS only)
    session_answervalue = 1
    session_bonusround = 0                  # 0 - not bonus, 1 - bonus
    TIMER = 0                               # Ongoing active timer


class chatvar():                            # Variables for IRC / Twitch chat function
    HOST = 'INIT'
    PORT = 'INIT'
    NICK = 'INIT'
    PASS = 'INIT'
    CHAN = 'INIT'
    RATE = (120)  # messages per second
    CHAT_MSG = re.compile(r"^:\w+!\w+@\w+\.tmi\.twitch\.tv PRIVMSG #\w+ :")


# CODE


# Trivia start build. ts = "Trivia set" means original master trivia file. qs = "Quiz set" means what's going to be played with for the session
def trivia_start():
    print("Trivia has been initiated. Generating trivia base for session...")
    # starts at zero, must reach trivia_questions to be complete during while loop
    qs_buildrows = 0

    # Loop through TS and build QS until qs_buildrows = trivia_numbers

    if var.tsrows < var.trivia_questions:
        var.trivia_questions = int(var.tsrows)
        print("Warning: Trivia questions for session exceeds trivia set's population. Setting session equal to max questions.")
    numberlist = []
    for i in range(var.tsrows):             # Create a list of all indices
        numberlist.append(i)
    while qs_buildrows < var.trivia_questions:
        temprando = random.choice(numberlist)
        numberlist.remove(temprando)
        try:
            # Check for duplicates with last argument, skip if so
            var.qs = var.qs.append(
                var.ts.loc[temprando], verify_integrity=True)
            qs_buildrows += 1
        except:                             # pass on duplicates and re-roll
            print("Duplicate index. This should not happen, dropping row from table. Please check config.txt's trivia_questions are <= total # of questions in trivia set.")
            var.ts.drop(var.ts.index[[temprando]])
    print("Quizset built.")
    var.trivia_active = True
    print("Trivia has begun! Question Count: "+str(var.trivia_questions) +
          ". Trivia will start in "+str(var.trivia_questiondelay)+" seconds.")
    # time.sleep(var.trivia_questiondelay) # Removed for making time flow
    trivia_callquestion()


def loadscores():
    # Load score list
    try:
        with open('userscores.txt', 'r') as fp:
            print("Score list loaded.")
            var.userscores = json.load(fp)
    except:
        with open('userscores.txt', "w") as fp:
            print("No score list, creating...")
            var.userscores = {'trivia_dummy': [0, 0, 0]}
            json.dump(var.userscores, fp)


def loadconfig():
    config = configparser.ConfigParser()
    config.read('config.txt')
    var.trivia_filename = config['Trivia Settings']['trivia_filename']
    var.trivia_filetype = config['Trivia Settings']['trivia_filetype']
    var.trivia_questions = int(config['Trivia Settings']['trivia_questions'])
    var.trivia_hintmode = int(config['Trivia Settings']['trivia_hintmode'])
    var.trivia_hinttime_1 = int(config['Trivia Settings']['trivia_hinttime_1'])
    var.trivia_hinttime_2 = int(config['Trivia Settings']['trivia_hinttime_2'])
    var.trivia_skiptime = int(config['Trivia Settings']['trivia_skiptime'])
    var.trivia_questiondelay = int(
        config['Trivia Settings']['trivia_questiondelay'])
    var.trivia_bonusvalue = int(config['Trivia Settings']['trivia_bonusvalue'])
    var.trivia_num_answers = int(config['Trivia Settings']['trivia_num_answers'])

    var.trivia_wait_for_next = int(config['Trivia Settings']['trivia_wait_for_next'])
    admin1 = config['Admin Settings']['admins']
    var.admins = admin1.split(',')

    chatvar.HOST = str(config['Bot Settings']['HOST'])
    chatvar.PORT = int(config['Bot Settings']['PORT'])
    chatvar.NICK = config['Bot Settings']['NICK']
    chatvar.PASS = config['Bot Settings']['PASS']
    chatvar.CHAN = config['Bot Settings']['CHAN']


def dumpscores():
    try:
        with open('userscores.txt', 'w') as fp:
            json.dump(var.userscores, fp)
    except:
        print("Scores NOT saved!")
        pass

# Trivia command switcher


def trivia_commandswitch(cleanmessage, username):

    # ADMIN ONLY COMMANDS
    if username in var.admins:
        if cleanmessage == "!triviastart":
            if var.trivia_active:
                print("Trivia already active.")
            else:
                trivia_start()
        if cleanmessage == "!triviaend":
            if var.trivia_active:
                trivia_end()
        if cleanmessage == "!stop":
            stopbot()
        if cleanmessage == "!loadconfig":
            loadconfig()
            sendmessage("Config reloaded.")
        if cleanmessage == "!backuptrivia":
            trivia_savebackup()
            sendmessage("Backup created.")
        if cleanmessage == "!loadtrivia":
            trivia_loadbackup()
        if cleanmessage == "!next":
            trivia_skipquestion()
        if cleanmessage == "!ask" and var.trivia_answered_wait == 0:
            trivia_callquestion()
            var.trivia_answered_wait = 1

    # ACTIVE TRIVIA COMMANDS
    if var.trivia_active:
        if cleanmessage == "!top3":
            topscore = trivia_top3score()
            print("topscore", topscore)
            print("Len", len(topscore))
            try:
                if (len(topscore) >= 3):
                    msg = "In 1st: "+str(topscore[0][0])+" "+str(topscore[0][1])+" points. 2nd place: "+str(topscore[1][0])+" "+str(
                        topscore[1][1])+" points. 3rd place: "+str(topscore[2][0])+" "+str(topscore[2][1])+" points."
                    sendmessage(msg)
                if (len(topscore) == 2):
                    msg = "In 1st: "+str(topscore[0][0])+" "+str(topscore[0][1])+" points. 2nd place: "+str(
                        topscore[1][0])+" "+str(topscore[1][1])+" points."
                    sendmessage(msg)
                if (len(topscore) == 1):
                    msg = "In 1st: " + \
                        str(topscore[0][0])+" "+str(topscore[0][1])+" points."
                    sendmessage(msg)
            except:
                msg = "No scores yet."
                sendmessage(msg)
        if cleanmessage == "!hint":
            if var.trivia_hintasked == 0:
                trivia_askhint(0)
            if var.trivia_hintasked == 1:
                trivia_askhint(0)
            if var.trivia_hintasked == 2:
                trivia_askhint(1)

        if cleanmessage == "!bonus":
            if var.session_bonusround == 0:
                trivia_startbonus()
                var.session_bonusround = 1
            if var.session_bonusround == 1:
                trivia_endbonus()
                var.session_bonusround = 0

    # GLOBAL COMMANDS
    if cleanmessage == "!score":
        trivia_userscore(username)


# Call trivia question
def trivia_callquestion():
    var.trivia_questionasked = True
    var.trivia_questionasked_time = round(time.time())
    msg = "Question "+str(var.session_questionno+1)+": " + \
        var.qs.iloc[var.session_questionno, 1] + " : " + \
        re.sub('[^\W_]', "_", var.qs.iloc[var.session_questionno, 2], re.U) # should be compiled
    var.hint_current = [-1,-1,'']
    sendmessage(msg)
    print("Question "+str(var.session_questionno+1) +
          ": | ANSWER: "+var.qs.iloc[var.session_questionno, 2])


def trivia_answer(username, cleanmessage, bypass = False):
    if username in var.trivia_answered_by:
        return
    if not bypass:
        try:
            var.userscores[username][0] += var.session_answervalue
            var.userscores[username][1] += var.session_answervalue
        except:
            print("Failed to find user! Adding new")
            var.userscores[username] = [var.session_answervalue,
                                    var.session_answervalue, 0]  # sets up new user

    if len(var.trivia_answered_by) != var.trivia_num_answers - 1 and not bypass:
        var.trivia_answered_by.append(username)
        print("** " + username + " answered correctly")
        var.userscores[username][0] += var.trivia_num_answers - len(var.trivia_answered_by)
        var.userscores[username][1] += var.trivia_num_answers - len(var.trivia_answered_by)
        return
    elif not bypass:
        var.trivia_answered_by.append(username)
        print("** " + username + " answered correctly")
    var.trivia_questionasked = False
    print("calling winners and doing stuff")
    dumpscores()  # Save all current scores 
    # TODO Make better
    print(var.trivia_answered_by)
    msg = p.join(var.trivia_answered_by)
    if var.session_answervalue == 1:
        msg += " answers question #"+str(var.session_questionno+1)+" correctly! The answer is ** "+str(
            var.qs.iloc[var.session_questionno, 2])
        print("3::")
    else:
        msg += " answers question #"+str(var.session_questionno+1)+" correctly! The answer is ** "+str(
            var.qs.iloc[var.session_questionno, 2])
        print("4::")
    sendmessage(msg)
    var.trivia_answered_by = []
    time.sleep((var.trivia_questiondelay))
    var.session_questionno += 1
    var.trivia_hintasked = 0
    var.trivia_questionasked = False
    var.trivia_questionasked_time = 0
    trivia_savebackup()
    if var.trivia_questions == var.session_questionno:          # End game check
        trivia_end()
    else:
        if var.trivia_wait_for_next == 0:
            trivia_callquestion()
        else:
            var.trivia_answered_wait = 0


# Finishes trivia by getting top 3 list, then adjusting final message based on how many participants. Then dumpscore()
def trivia_end():

    # Argument "1" will return the first in the list (0th position) for list of top 3
    topscore = trivia_top3score()
    trivia_clearscores()
    if (len(topscore) == 0):
        msg = "No answered questions. Results are blank."
        sendmessage(msg)

    else:
        msg = "Trivia is over! Calculating scores..."
        sendmessage(msg)
        time.sleep(2)
        trivia_assignwinner(topscore[0][0])
        if (len(topscore) >= 3):
            msg = " *** "+str(topscore[0][0])+" *** is the winner of trivia with "+str(topscore[0][1])+" points! 2nd place: "+str(
                topscore[1][0])+" "+str(topscore[1][1])+" points. 3rd place: "+str(topscore[2][0])+" "+str(topscore[2][1])+" points."
            sendmessage(msg)
        if (len(topscore) == 2):
            msg = " *** "+str(topscore[0][0])+" *** is the winner of trivia with "+str(
                topscore[0][1])+" points! 2nd place: "+str(topscore[1][0])+" "+str(topscore[1][1])+" points."
            sendmessage(msg)
        if (len(topscore) == 1):
            msg = " *** " + \
                str(topscore[0][0])+" *** is the winner of trivia with " + \
                str(topscore[0][1])+" points!"
            sendmessage(msg)

    dumpscores()
    time.sleep(3)
    msg2 = "Thanks for playing! See you next time!"
    sendmessage(msg2)

    var.session_questionno = 0                # reset variables for trivia
    var.trivia_active = False
    var.trivia_hintasked = 0
    var.trivia_questionasked = False
    var.trivia_questionasked_time = 0
    var.qs = pd.DataFrame(columns=list(var.ts))

    # Clear backup files upon finishing trivia
    os.remove('backup/backupquizset.csv', dir_fd=None)
    os.remove('backup/backupscores.txt', dir_fd=None)
    os.remove('backup/backupsession.txt', dir_fd=None)


def trivia_routinechecks():                   # after every time loop, routine checking of various vars/procs
    var.TIMER = round(time.time())
    # print(var.TIMER)

    if var.trivia_questions == var.session_questionno:          # End game check
        trivia_end()

    if ((var.TIMER - var.trivia_questionasked_time) > var.trivia_hinttime_2 and var.trivia_active and var.trivia_hintasked == 1 and var.trivia_questionasked):
        var.trivia_hintasked = 2
        trivia_askhint(1)  # Ask second hint

    if ((var.TIMER - var.trivia_questionasked_time) > var.trivia_hinttime_1 and var.trivia_active and var.trivia_hintasked == 0 and var.trivia_questionasked):
        var.trivia_hintasked = 1
        trivia_askhint(0)  # Ask first hint

    if ((var.TIMER - var.trivia_questionasked_time) > var.trivia_skiptime and var.trivia_active and var.trivia_questionasked):
        trivia_skipquestion()


def trivia_askhint(hinttype=0):
    if len(str(var.qs.iloc[var.session_questionno, 2])) <= 2:
        print("Hint requested, not served")
        msg = "Question "+str(var.session_questionno+1)+": " + \
        var.qs.iloc[var.session_questionno, 1] + " : " + \
        re.sub('[^\W_]', "_", var.qs.iloc[var.session_questionno, 2], re.U) # should be compiled
        sendmessage(msg)
        return
    if var.trivia_hintmode == 0:
        trivia_askhint_mode0(hinttype)
    else: 
        trivia_askhint_mode1(hinttype)


def trivia_askhint_mode1(hinttype):                 # hinttype: 0 = 1st hint, 1 = 2nd hint
    # type 0, reveal 1 character, higher chance to reveal vowel, maybe
    if hinttype == 0:
        msg = "Question "+str(var.session_questionno+1)+": " + \
        var.qs.iloc[var.session_questionno, 1]
        if var.hint_current[0] == 0:
            sendmessage(msg + " Hint #1: "+var.hint_current[2])
            return
        prehint = str(var.qs.iloc[var.session_questionno, 2])
        # only reveal letters, don't reveal -, _, ', etc
        kept_letter_i = random.randrange(0, len(prehint))
        while not prehint[kept_letter_i].isalnum():
            kept_letter_i = random.randrange(0, len(prehint))
        kept_letter = prehint[kept_letter_i]
        hint = list(re.sub('[^\W_]', "_", var.qs.iloc[var.session_questionno, 2], re.U))
        hint[kept_letter_i] = kept_letter
        var.hint_current = [0,[kept_letter_i],"".join(hint)]
        sendmessage(msg + " Hint #1: "+var.hint_current[2])
    if hinttype == 1:
        # reveal up to 3 more, depending on length
        prehint = str(var.qs.iloc[var.session_questionno, 2])
        msg = "Question "+str(var.session_questionno+1)+": " + \
        var.qs.iloc[var.session_questionno, 1]
        if var.hint_current[0] == 1:
            sendmessage(msg + " Hint #2: "+var.hint_current[2])
            print("here1")
            return
        reveal_n = 3
        if len(prehint) <= 6:
            reveal_n = 1
        if len(prehint) <= 3:
            print("here2")
            sendmessage("Hint #1: "+var.hint_current[2])
            return
        # only reveal letters, don't reveal -, _, ', etc
        print("here3 no" + str(len(prehint)))
        kept_letters_i = [var.hint_current[1][0]]
        while len(kept_letters_i) != reveal_n +1:
            kept_letter_i = random.randrange(0, len(prehint))
            while not prehint[kept_letter_i].isalnum() or kept_letters_i.count(kept_letter_i) >= 1:
                kept_letter_i = random.randrange(0, len(prehint))
            kept_letters_i.append(kept_letter_i)
        kept_letters = [prehint[i] for i in kept_letters_i]
        hint = list(re.sub('[^\W_]', "_", var.qs.iloc[var.session_questionno, 2], re.U))
        for (i, letter) in zip(kept_letters_i,kept_letters):
            hint[i] = letter
        var.hint_current = [1,[kept_letter_i],"".join(hint)]
        sendmessage(msg + " Hint #2: "+var.hint_current[2])


def trivia_askhint_mode0(hinttype):                 # hinttype: 0 = 1st hint, 1 = 2nd hint
    # type 0, replace 2 out of 3 chars with _
    if hinttype == 0:
        prehint = str(var.qs.iloc[var.session_questionno, 2])
        listo = []
        hint = ''
        counter = 0
        for i in prehint:
            if counter % 3 >= 0.7:
                listo += "_"
            else:
                listo += i
            counter += 1
        for i in range(len(listo)):
            hint += hint.join(listo[i])
        sendmessage("Hint #1: "+hint)

    # type 1, replace vowels with _
    if hinttype == 1:
        prehint = str(var.qs.iloc[var.session_questionno, 2])
        hint = re.sub('[aeiou]', '_', prehint, flags=re.I)
        sendmessage("Hint #2: "+hint)


def trivia_skipquestion():
    if len(var.trivia_answered_by) > 0:
        trivia_answer('','',bypass=True)
        return
    if var.trivia_active:
        var.session_questionno += 1
        var.trivia_hintasked = 0
        var.trivia_questionasked = False
        var.trivia_questionasked_time = 0
        try:
            sendmessage("Question was not answered in time. Answer: "+str(
                var.qs.iloc[var.session_questionno-1, 2])+".")
        except:
            sendmessage(
                "Question was not answered in time.")
        time.sleep(var.trivia_questiondelay)
        if var.trivia_questions == var.session_questionno:          # End game check
            trivia_end()
        else:
            if var.trivia_wait_for_next == 0:
                trivia_callquestion()
            else:
                var.trivia_answered_wait = 0


# B O N U S
def trivia_startbonus():
    msg = "B O N U S Round begins! Questions are now worth " + \
        str(var.trivia_bonusvalue)+" points!"
    sendmessage(msg)
    var.session_answervalue = var.trivia_bonusvalue


def trivia_endbonus():
    msg = "Bonus round is over! Questions are now worth 1 point."
    sendmessage(msg)
    var.session_answervalue = 1


# Top 3 trivia
def trivia_top3score():
    # temp dictionary just for keys & sessionscore
    data2 = {}
    for i in var.userscores.keys():
        if var.userscores[i][0] > 0:
            data2[i] = var.userscores[i][0]

    data3 = collections.Counter(data2)  # top 3 counter
    data3.most_common()
    top3 = []  # top 3 list
    for k, v in data3.most_common(3):
        top3 += [[k, v]]
    return top3

# clears scores and assigns a win to winner


def trivia_clearscores():
    for i in var.userscores.keys():
        var.userscores[i][0] = 0

# Add +1 to winner's win in userscores


def trivia_assignwinner(winner):
    var.userscores[winner][2] += 1


# temp function to give 100 score to each
def trivia_givescores():
    for i in var.userscores.keys():
        var.userscores[i][0] = random.randrange(0, 1000)


def trivia_userscore(username):
    try:
        msg = str(username)+" has "+str(var.userscores[username][0])+" points for this trivia session, "+str(
            var.userscores[username][1])+" total points and "+str(var.userscores[username][2])+" total wins."
        sendmessage(msg)
    except:
        msg = str(username)+" not found in database."
        sendmessage(msg)

# Chat message sender func


def sendmessage(msg):
    print("Sent: " + msg)
    answermsg = ":"+chatvar.NICK+"!"+chatvar.NICK+"@"+chatvar.NICK + \
        ".tmi.twitch.tv PRIVMSG "+chatvar.CHAN+" :/me "+msg+"\r\n"
    answermsg2 = answermsg.encode("utf-8")
    s.send(answermsg2)

# STOP BOT (sets loop to false)


def stopbot():
    var.SWITCH = False

# CALL TIMER


def calltimer():
    print("Timer: "+str(var.TIMER))


# BACKUP SAVING/LOADING

def trivia_savebackup():            # backup session saver
    # Save session position/variables
    if not os.path.exists('backup/'):
        os.mkdir('backup/')
    config2 = configparser.ConfigParser()
    config2['DEFAULT'] = {'session_questionno': var.session_questionno,
                          'session_answervalue': var.session_answervalue, 'session_bonusround': var.session_bonusround}
    with open('backup/backupsession.txt', 'w') as c:
        config2.write(c)

    # Save CSV of quizset
    var.qs.to_csv('backup/backupquizset.csv', index=False, encoding='utf-8')
    # Save session scores
    try:
        with open('backup/backupscores.txt', 'w') as fp:
            json.dump(var.userscores, fp)
    except:
        print("Scores NOT saved!")
        pass


def trivia_loadbackup():            # backup session loader
    if var.trivia_active:
        sendmessage("Trivia is already active. Prior session was not reloaded.")
    else:
        # Load session position/variables
        config2 = configparser.ConfigParser()
        config2.read('backup/backupsession.txt')

        var.session_questionno = int(config2['DEFAULT']['session_questionno'])
        var.session_answervalue = int(
            config2['DEFAULT']['session_answervalue'])
        var.session_bonusround = int(config2['DEFAULT']['session_bonusround'])

        # Load quizset
        var.qs = pd.read_csv('backup/backupquizset.csv', encoding='utf-8')

        # Load session scores

        try:
            with open('backup/backupscores.txt', 'r') as fp:
                print("Score list loaded.")
                var.userscores = json.load(fp)
        except:
            with open('backup/backupscores.txt', "w") as fp:
                print("No score list, creating...")
                var.userscores = {'trivia_dummy': [0, 0, 0]}
                json.dump(var.userscores, fp)

        print("Loaded backup.")
        var.trivia_active = True
        sendmessage("Trivia sessions reloaded. Trivia will begin again in " +
                    str(var.trivia_questiondelay)+" seconds.")
        time.sleep(var.trivia_questiondelay)
        trivia_callquestion()


############### CHAT & BOT CONNECT ###############


# STARTING PROCEDURES
print("Bot loaded. Loading config and scores...")
try:
    loadconfig()
    print("Config loaded.")
except:
    print("Config not loaded! Check config file and reboot bot")
    var.SWITCH = False

try:
    loadscores()
    print("Scores loaded.")
except:
    print("Scores not loaded! Check or delete 'userscores.txt' file and reboot bot")
    var.SWITCH = False


if var.SWITCH:
    try:
        s = socket.socket()
        s.connect((chatvar.HOST, chatvar.PORT))
        s.send("PASS {}\r\n".format(chatvar.PASS).encode("utf-8"))
        s.send("NICK {}\r\n".format(chatvar.NICK).encode("utf-8"))
        s.send("JOIN {}\r\n".format(chatvar.CHAN).encode("utf-8"))
        time.sleep(1)
        # sendmessage(var.infomessage)  # disabled
        s.setblocking(0)
    except:
        print("Connection failed. Check config settings and reload bot.")
        var.SWITCH = False


def scanloop():
    try:
        response = s.recv(1024).decode("utf-8")
        if response == "PING :tmi.twitch.tv\r\n":
            s.send("PONG :tmi.twitch.tv\r\n".encode("utf-8"))
            print("Pong sent")
        else:
            username = re.search(r"\w+", response).group(0)
            if username == chatvar.NICK:  # Ignore this bot's messages
                pass
            else:
                message = chatvar.CHAT_MSG.sub("", response)
                cleanmessage = re.sub(r"\s+", "", message, flags=re.UNICODE)
                print("USER RESPONSE: " + username + " : " + message)
                if cleanmessage in var.COMMANDLIST:
                    print("Command recognized.")
                    trivia_commandswitch(cleanmessage, username)
                    time.sleep(1)
                try:
                    #                   if re.match(var.qs.iloc[var.session_questionno,2], message, re.IGNORECASE):   # old matching

                    # strict new matching
                    if bool(re.match("\\b"+var.qs.iloc[var.session_questionno, 2]+"\\b", message, re.IGNORECASE)):
                        print("Answer recognized.")
                        trivia_answer(username, cleanmessage)
                    # strict new matching
                    if bool(re.match("\\b"+var.qs.iloc[var.session_questionno, 3]+"\\b", message, re.IGNORECASE)):
                        print("Answer recognized.")
                        trivia_answer(username, cleanmessage)
                except Exception as e:
                    print(e)
                    traceback.print_exc()
                    pass
    except Exception as e:
        if not str(e).startswith("["):
            print(e)
            traceback.print_exc()
        pass


# Infinite loop while bot is active to scan messages & perform routines

while var.SWITCH:
    if var.trivia_active:
        trivia_routinechecks()
    scanloop()
    time.sleep(1 / chatvar.RATE)



# 0: Index
# 0: Game
# 1: Question
# 2: Answer
# 3: Answer 2
# 4: Grouping
# 5: Creator
