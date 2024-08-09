from app import app, db, ColdTurkeyPass

with app.app_context():
    db.create_all()
    db.session.add(ColdTurkeyPass(computer="computer", locked=False, password="test-password", confirm="unlocked"))
    db.session.add(ColdTurkeyPass(computer="laptop", locked=False, password="test-password", confirm="unlocked"))
    db.session.commit()
