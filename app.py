import functools
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
    room = data["room"]
    join_room(room)
    if (room == "computer" or room == "laptop"):
        print(room)
        info = db.session.execute(db.select(ColdTurkeyPass).filter_by(computer=room)).scalar_one_or_none()
        if (info.locked and info.confirm == "unlocked"):
            emit("lock", {"locked": True, "password": "test-password"}, json=True, to=room) #Set a whole new password
        elif (info.locked == False and info.confirm == "locked"):
            emit("unlock", {"locked": False, "password": "test-password"}, json=True, to=room) #Use the past password
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
def lock():
    
    #Broadcast to all phones, and to all the computer types
    emit("lock", {"locked": True},json=True, to="phone")
    #Check if computer is defintely unlocked
    for (computerType) in ["computer", "laptop"]:
        coldInfo = db.session.execute(db.select(ColdTurkeyPass).filter_by(computer=computerType)).scalar_one_or_none()
        coldInfo.locked = True
        db.session.commit()
        if (coldInfo.confirm == "unlocked"):
            createdPassword = secrets.token_urlsafe(16)
            emit("lock", {"locked": True, "password": createdPassword}, json=True, to=computerType) #Set a whole new password

@socketio.on("unlock")
def unlock():
    #Broadcast to all phones, and to all the computer types
    emit("unlock", {"locked": False},json=True, to="phone")
    #Check if computer is defintely unlocked
    for (computerType) in ["computer", "laptop"]:
        coldInfo = db.session.execute(db.select(ColdTurkeyPass).filter_by(computer=computerType)).scalar_one_or_none()
        coldInfo.locked = False
        db.session.commit()
        if (coldInfo.confirm == "locked"):
            emit("unlock", {"locked": False, "password": coldInfo.password}, json=True, to=computerType) #Use the past password]

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
            db.session.add(user)
            db.session.commit()
        if (user.admin):
            return {"image" : id_info["picture"], "name": id_info["name"], "idToken": token} 
        return {"message": "invalid request, you are not admin"}, 403

        #if admin, return, otherwise, this is invalid
    return {"message": "invalid request, missing id_token"}, 406



if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", allow_unsafe_werkzeug=True)
