from discord.message import Message as DiscordMessage
from sqlalchemy import Column, Integer, String
from database import Base, session


class Message(Base):
    __tablename__ = 'chat_messages'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    discord_id = Column(Integer, nullable=False)
    text = Column(String, nullable=False)

    def __init__(self, data):
        super().__init__()
        self.session = session
        if isinstance(data, DiscordMessage):
            self.from_discord(data)
        else:
            self.user_id = data['user_id']
            self.discord_id = data['discord_id']
            self.text = data['text']

    def from_discord(self, data: DiscordMessage):
        self.discord_id = data.id
        self.text = data.content
        self.user_id = self.try_get_server_user(data.author)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'discord_id': self.discord_id,
            'text': self.text
        }

    def try_get_server_user(self, discord_author):
        user = None
        #user = self.session.query(User).filter_by(discord_id=discord_author.id).first()
        return user.id if user else None

    def __repr__(self):
        return f'<Message {self.id}>'


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    discord_id = Column(Integer, nullable=False)

    def __repr__(self):
        return f'<User {self.id}>'
