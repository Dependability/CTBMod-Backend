from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, join_room, emit
from flask_login import UserMixin

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'

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
            emit("lock", {"locked": True, "password": "test-password"}, json=True, to=computerType) #Set a whole new password

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
            emit("unlock", {"locked": False, "password": "test-password"}, json=True, to=computerType) #Use the past password]
    
if __name__ == "__main__":
    socketio.run(app, allow_unsafe_werkzeug=True, host="0.0.0.0")
