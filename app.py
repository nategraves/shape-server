""" Simple server that returns a path string generated from a char model RNN """
from __future__ import division, print_function

import re
import subprocess
import threading
import json
import uuid

from datetime import datetime
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from random import randint, uniform
from svgpathtools import parse_path, Path
from marshmallow import Schema, fields, ValidationError, pre_load
from flask_restless import APIManager

app = Flask(__name__) # pylint: disable=invalid-name
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
db = SQLAlchemy(app)
PATH_MAX = 300

VERSIONS = [
    'cv/paths_60000.t7',
    'cv/paths_1116_195000.t7',
    'cv/paths_1120_50000.t7',
    'cv/paths_1125_26200.t7',
]

class User(db.Model):
    id = db.Column(db.String(255), primary_key=True)
    names = db.relationship('Name', back_populates='name_user')
    votes = db.relationship('Vote', back_populates='vote_user')

class Path(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    d = db.Column(db.Text, unique=True, nullable=False)
    created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    names = db.relationship('Name', back_populates='path')

    def as_dict(self):
        return { col.name: getattr(self, col.name) for col in self.__table__.columns }

    def __repr__(self):
        return 'Path #%s | Size: %s\n' % (self.id, len(self.d))

class Name(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    path_id = db.Column(db.Integer, db.ForeignKey('path.id'))
    path = db.relationship('Path', back_populates='names')
    user_id = db.Column(db.String(255), db.ForeignKey('user.id'))
    name_user = db.relationship('User', back_populates='names')
    votes = db.relationship('Vote', back_populates='name')

    def as_dict(self):
        return { col.name: getattr(self, col.name) for col in self.__table__.columns }

    def __repr__(self):
        return '#%s | %sx | ' % (self.id, self.count)

class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    name_id = db.Column(db.Integer, db.ForeignKey('name.id'))
    name = db.relationship('Name', back_populates='votes')
    user_id = db.Column(db.String(255), db.ForeignKey('user.id'))
    vote_user = db.relationship('User', back_populates='votes')

    def as_dict(self):
        return { col.name: getattr(self, col.name) for col in self.__table__.columns }

    def __repr__(self):
        return 'Path #%s | %s\n' % (self.path_id, self.created)

def add_cors(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

def generate(version = 0, min_shape_size = 2, max_shape_size = 500, repeat=False, max_length=300):
    """ Returns an SVG path as a string """

    min_length = 30
    length = randint(min_length, max_length)

    ####### Next character
    sample = 1

    while True:
        final_path = None
        sampling = False
        while final_path is None and not sampling:
            sampling = True
            generate_path = "th sample.lua -checkpoint %s -length %s -start_text M -sample %s -gpu -1" % (VERSIONS[version], length, sample)
            nn_output = subprocess.getoutput(generate_path)
            reg_ex = re.compile(r'M.+Z')
            path_strings = reg_ex.findall(nn_output) 
            for path in path_strings:
                p = parse_path(path)
                if p.isclosed():
                    xmin, xmax, ymin, ymax = p.bbox()
                    width = xmax - xmin
                    height = ymax - ymin
                    if width > min_shape_size and width < max_shape_size and height > min_shape_size and height < max_shape_size:
                        final_path = p.d()
                        break
            sampling = False
        path = Path(d=final_path)
        db.session.add(path)
        db.session.commit()
    return final_path

@app.route('/user/new')
def new_user():
    id = uuid.uuid1()
    print (id)
    user = User(id=id)
    response = jsonify({ 'id': id })
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route('/sample')
def sample_path():
    path = generate(len(VERSIONS) - 1)
    response = jsonify({ 'path': path })
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route('/generate')
@app.route('/generate/<version>')
def new_path(version = 0):
    version = int(version)
    if version > len(VERSIONS):
        version = len(VERSIONS) - 1
    path = generate(version)
    response = jsonify({ 'path': path })
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    db.create_all()
    manager = APIManager(app, flask_sqlalchemy_db=db)

    path_manager = manager.create_api(Path, methods=['GET'], collection_name='paths', page_size=20)
    name_manager = manager.create_api(Name, methods=['GET', 'POST', 'DELETE'], collection_name='names')
    vote_manager = manager.create_api(Vote, methods=['GET', 'POST', 'DELETE'], collection_name='votes')

    app.after_request(add_cors)
    app.run(debug=True)
