from flask import Flask
from flask_restful import Api

from calendar_handler import CalendarHandler

app = Flask(__name__)
api = Api(app)

api.add_resource(CalendarHandler, '/')

if __name__ == '__main__':
    app.run(debug=True)
