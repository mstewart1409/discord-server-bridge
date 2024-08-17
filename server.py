from flask import Flask


class Server:
    def __init__(self, endpoint, key):
        self.app = Flask(__name__)
        self.endpoint = endpoint
        self.key = key

    def start(self):
        self.app.run()

    def send_to_server(self, message):
        # Send the message to the server
        return {'message': message, 'message_id': None}

    def edit_message_text(self, message_id, text):
        # Edit the message on the server
        pass

    def delete_message(self, message_id):
        # Delete the message on the server
        pass
