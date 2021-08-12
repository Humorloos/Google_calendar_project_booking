import logging
import sys

from flask import Flask, request
from flask_restful import Resource, Api, reqparse
from logging.handlers import RotatingFileHandler
from pathlib import Path

app = Flask(__name__)
api = Api(app)

# setup logger
info_filehandler = RotatingFileHandler(Path('logs').joinpath('app.log'), maxBytes=10000000, backupCount=3)
info_filehandler.setLevel(logging.INFO)
logger = logging.getLogger()
logger.addHandler(info_filehandler)
logger.setLevel(logging.INFO)


# log all requests
@app.before_request
def log_request_info():
    logger.info(f'Headers: {request.headers}')
    logger.info(f'Body: {request.get_data()}')


class HelloWorld(Resource):
    @staticmethod
    def get():
        return {'hello': 'world'}


api.add_resource(HelloWorld, '/')

if __name__ == '__main__':
    app.run(debug=True)
