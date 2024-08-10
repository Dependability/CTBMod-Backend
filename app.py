import functools
from threading import Timer
from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, disconnect, join_room, emit
from flask_login import UserMixin, current_user, login_user
from flask_cors import CORS
from google.oauth2 import id_token
from google.auth.transport import requests
import os, secrets

app = Flask(__name__)
CORS(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
CLIENT_ID = os.environ["GOOGLE_CLIENT_ID"]



db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*")
currentTimer = None

class ColdTurkeyPass(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    computer = db.Column(db.String(20), nullable=False)
    locked = db.Column(db.Boolean, default=False, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    confirm = db.Column(db.String(20), nullable=False)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.String(256), nullable=False)
    email = db.Column(db.String(100), nullable = False)
    realName = db.Column(db.String(25))
    name = db.Column(db.String(100), nullable=False)
    picture = db.Column(db.String(312), nullable=False)
    admin = db.Column(db.Boolean, default=False, nullable=False)
    robloxPic = db.Column(db.String(312))

robloxTable = {
    "alasfartimey@gmail.com" : {"picture": "https://tr.rbxcdn.com/30DAY-AvatarHeadshot-AE8B6841F37258AB0AA856C1597C918B-Png/150/150/AvatarHeadshot/Webp/noFilter", "realName": "Timey"},
    "alasfarzouhour7@gmail.com" : {"picture": "https://tr.rbxcdn.com/30DAY-AvatarHeadshot-0AC9DA3F66D63F3DFFF7C80F7DFDD46A-Png/150/150/AvatarHeadshot/Webp/noFilter", "realName": "Zuzu"},
    "fatimaalasfar751@gmail.com" : {"picture": "https://tr.rbxcdn.com/30DAY-AvatarHeadshot-6E87FD7E0B40FC2B9DBB6DDF4BD62BEB-Png/150/150/AvatarHeadshot/Webp/noFilter", "realName": "Timer"},
    "robloxplayer307@gmail.com" : {"picture": "https://tr.rbxcdn.com/30DAY-AvatarHeadshot-0570A1C4880EA0930A7B5A5897344304-Png/150/150/AvatarHeadshot/Webp/noFilter", "realName": "King"},
}

adminList = ["alasfartimey@gmail.com", "alasfarzouhour7@gmail.com", "fatimaalasfar751@gmail.com", "robloxplayer307@gmail.com"]


def checkAdmin(token):
    try:
        id_info = id_token.verify_oauth2_token(token, requests.Request(), CLIENT_ID)
        user = db.session.execute(db.select(User).filter_by(uid=id_info["sub"])).scalar_one_or_none()
        if (user):
            if (user.admin):
                return True
        return False
    except ValueError:
        return False
    

@socketio.on('connect')
def onConnect(auth):
    if (auth):
        return checkAdmin(auth["token"])

@socketio.on('join')
def on_join(data):
    global currentTimer
    def sendToClient(socketio, app):
        with app.app_context():
            for (computerType) in ["computer", "laptop"]:
                coldInfo = db.session.execute(db.select(ColdTurkeyPass).filter_by(computer=computerType)).scalar_one_or_none()
                lock = coldInfo.locked
                password = coldInfo.password
                confirm = coldInfo.confirm
                if (lock and confirm == "unlocked"):
                    password = secrets.token_urlsafe(16)
                    socketio.emit(lock, {"locked": lock, "password": password}, to=computerType) #Set a whole new password
                elif ((not lock) and confirm == "locked"):
                    socketio.emit(lock, {"locked": lock, "password": password}, to=computerType)

    room = data["room"]
    join_room(room)
    if (room == "computer" or room == "laptop"):
        print(room)
        if (currentTimer):
            currentTimer.cancel()
        currentTimer = Timer(3, sendToClient, [socketio, app])
        currentTimer.start()
    else:
        info = db.session.execute(db.select(ColdTurkeyPass).filter_by(computer="laptop")).scalar_one_or_none()
        if (info.locked):
            emit("lock", {"locked": True}, json=True)
        else:
            emit("unlock", {"locked": False}, json=True)


@socketio.on("confirm-lock")
def confirmLock(data):
    coldTurkeyInfo = db.session.execute(db.select(ColdTurkeyPass).filter_by(computer=data["origin"])).scalar_one_or_none()
    coldTurkeyInfo.confirm = "locked" if data["locked"] else "unlocked"
    print(data)
    if ("password_locked" in data):
        coldTurkeyInfo.password = data["password_locked"]
    db.session.commit()

@socketio.on("lock")
def lock(data):
    #Broadcast to all phones, and to all the computer types
    emit("lock", {"locked": True, "user": data["user"]},json=True, to="phone")
    #Check if computer is defintely unlocked

    #Set a timer for 3 seconds, if timer is active, then replace it.
    def sendToClients():
        with app.app_context():
            for (computerType) in ["computer", "laptop"]:
                    coldInfo = db.session.execute(db.select(ColdTurkeyPass).filter_by(computer=computerType)).scalar_one_or_none()
                    coldInfo.locked = True
                    db.session.commit()
                    if (coldInfo.confirm == "unlocked"):
                        createdPassword = secrets.token_urlsafe(16)
                        socketio.emit("lock", {"locked": True, "password": createdPassword}, to=computerType) #Set a whole new password
    global currentTimer
    if (currentTimer):
        currentTimer.cancel()
    currentTimer = Timer(3, sendToClients)
    currentTimer.start()
        

@socketio.on("unlock")
def unlock(data):
    #Broadcast to all phones, and to all the computer types
    emit("unlock", {"locked": False, "user": data["user"]},json=True, to="phone")
    #Check if computer is defintely unlocked

    def sendToClients():
        with app.app_context():
            for (computerType) in ["computer", "laptop"]:
                coldInfo = db.session.execute(db.select(ColdTurkeyPass).filter_by(computer=computerType)).scalar_one_or_none()
                coldInfo.locked = False
                db.session.commit()
                if (coldInfo.confirm == "locked"):
                    socketio.emit("unlock", {"locked": False, "password": coldInfo.password}, to=computerType) #Use the past password]
    global currentTimer
    if (currentTimer):
        currentTimer.cancel()
    currentTimer = Timer(3, sendToClients)
    currentTimer.start()

@app.route("/callback", methods=["POST"])
def callback():
    body = request.json
    if (body.get("id_token")):
        token = body["id_token"]
        id_info = id_token.verify_oauth2_token(token, requests.Request(), CLIENT_ID)
        print(id_info)

        user = db.session.execute(db.select(User).filter_by(uid=id_info["sub"])).scalar_one_or_none()
        if (user):
            print(user)
        else:
            user = User(uid=id_info["sub"], email=id_info["email"], name=id_info["name"], picture=id_info["picture"], admin=False)
            print(user)
            if (id_info["email"] in robloxTable):
                robloxInfo = robloxTable[id_info["email"]]
                user.realName = robloxInfo["realName"]
                user.robloxPic = robloxInfo["picture"]
            if (id_info["email"] in adminList):
                user.admin = True
            db.session.add(user)
            db.session.commit()
        if (user.admin):
            return {"image" : id_info["picture"], "name": id_info["name"], "idToken": token, "rblxname": user.realName, "rblxpic": user.robloxPic} 
        return {"message": "invalid request, you are not admin"}, 403

        #if admin, return, otherwise, this is invalid
    return {"message": "invalid request, missing id_token"}, 406



if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", allow_unsafe_werkzeug=True)
