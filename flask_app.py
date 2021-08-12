import logging
import sys

from flask import Flask, request
from flask_restful import Resource, Api, reqparse

app = Flask(__name__)
api = Api(app)
path = '/home/Humorloos/log'
# info_fh = RotatingFileHandler(os.path.join(path, 'app.log'), maxBytes=10000000, backupCount=3)
info_fh = logging.StreamHandler(sys.stdout)

info_fh.setLevel(logging.INFO)
logger = logging.getLogger()
logger.addHandler(info_fh)


@app.before_request
def log_request_info():
    logger.info(f'Headers: {request.headers}')
    logger.info(f'Body: {request.get_data()}')


parser = reqparse.RequestParser()


class HelloWorld(Resource):
    @staticmethod
    def get():
        return {'hello': 'world'}

    # def post(self):


api.add_resource(HelloWorld, '/')

if __name__ == '__main__':
    app.run(debug=True)
