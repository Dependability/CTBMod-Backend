from app import app, db, ColdTurkeyPass

with app.app_context():
    db.create_table()
    db.session.add(ColdTurkeyPass(computer="computer", locked=False, password="hi", confirm="unlocked"))
    db.session.add(ColdTurkeyPass(computer="computer", locked=False, password="hi", confirm="unlocked"))
    db.session.commit()