from datetime import datetime
from twogplus import db


class User(db.Model):
    __tablename__ = "users"

    id: int = db.Column(db.Integer, primary_key=True)
    name: str = db.Column(db.Text, nullable=False)
    created_at: datetime = db.Column(
        db.Date, nullable=False, default=db.func.now()
    )
    is_tested: bool = db.Column(db.Boolean, nullable=False)
    is_vaccinated: bool = db.Column(db.Boolean, nullable=False)

    def __init__(
        self, name: str, is_vaccinated: bool = False, is_tested: bool = False
    ):
        self.name = name
        self.is_vaccinated = is_vaccinated
        self.is_tested = is_tested

    def __repr__(self):
        return f"<User id={self.id}, name={self.name}>"
