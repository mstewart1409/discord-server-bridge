from discord.message import Message as DiscordMessage
from sqlalchemy import Column, Integer, String
from database import db


class Message(db.Model):
    __tablename__ = 'chat_messages'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    discord_id = Column(Integer, nullable=False)
    text = Column(String, nullable=False)

    def __init__(self, data):
        if isinstance(data, DiscordMessage):
            self.from_discord(data)
        else:
            self.from_server(data)

    def from_discord(self, data: DiscordMessage):
        self.discord_id = data.id
        self.text = data.content
        self.user_id = self.try_get_server_user(data.author)

    @staticmethod
    def try_get_server_user(discord_author):
        user = User.query.filter_by(discord_id=discord_author.id).first()
        return user.id if user else None

    def __repr__(self):
        return f'<Message {self.id}>'


class User(db.Model):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    discord_id = Column(Integer, nullable=False)

    def __repr__(self):
        return f'<User {self.id}>'
