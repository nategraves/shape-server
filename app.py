""" Simple server that returns a path string generated from a char model RNN """
from __future__ import division, print_function

import re
import subprocess
import threading
import json

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

VERSIONS = [
    'cv/paths_60000.t7',
    'cv/paths_1116_195000.t7',
    'cv/paths_1120_50000.t7',
    'cv/paths_1125_26200.t7',
]

class Path(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    d = db.Column(db.String(300), unique=True, nullable=False)
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

    def as_dict(self):
        return { col.name: getattr(self, col.name) for col in self.__table__.columns }

    def __repr__(self):
        return 'Path #%s | %s\n' % (self.path_id, self.created)

def add_cors(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

def get_all_paths():
    with open('shapes.txt', 'r') as f:
        paths = [line.rstrip() for line in f.readlines()]
        paths = list(reversed(paths))
        return paths

def generate(version = 0, min_size = 2, max_size = 500, repeat=False):
    """ Returns an SVG path as a string """
    if repeat: threading.Timer(60.0, generate).start()
    length = randint(30, 300)

    ####### Next character
    sample = 1
    #temperature = 0

    ####### Argmax !!! Doesn't work
    #sample = 0
    #temperature = uniform(0.1, 0.3)

    ####### Random
    #sample = randint(0, 1)
    #temperature = uniform(0.1, 0.3) if sample == 0 else 0

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
                    if width > min_size and width < max_size and height > min_size and height < max_size:
                        final_path = p.d()
                        break
            sampling = False

        path = Path(d=final_path)
        db.session.add(path)
        db.session.commit()
        with open('shapes.txt', 'r+') as f:
            svgs = f.read().splitlines()
            if final_path not in svgs:
                f.write(path + '\n')
                forever = False
                break
    return final_path

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

if __name__ == '__main__':
    db.create_all()
    manager = APIManager(app, flask_sqlalchemy_db=db)

    path_manager = manager.create_api(Path, methods=['GET'], collection_name='paths', page_size=20)
    name_manager = manager.create_api(Name, methods=['GET', 'POST', 'DELETE'], collection_name='names')
    vote_manager = manager.create_api(Vote, methods=['GET', 'POST', 'DELETE'], collection_name='votes')

    app.after_request(add_cors)
    app.run(debug=True)
