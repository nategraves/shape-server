""" Simple server that returns a path string generated from a char model RNN """
from __future__ import division, print_function

import re
import subprocess
import threading

from flask import Flask, jsonify
from random import randint, uniform
from svgpathtools import parse_path, Path

app = Flask(__name__.split('.')[0]) # pylint: disable=invalid-name
VERSIONS = [
    'cv/paths_60000.t7',
    'cv/paths1116_195000.t7',
    'cv/paths1120_50000.t7',
    'cv/paths_1125_26200.t7',
]

def get_all_paths():
    with open('shapes.txt', 'r') as f:
        paths = [line.rstrip() for line in f.readlines()]
        paths = list(reversed(paths))
        return paths

def generate(version = 0, min_size = 2, max_size = 500, repeat=False):
    """ Returns an SVG path as a string """
    if repeat: threading.Timer(60.0, generate).start()
    length = randint(30, 300)
    #sample = randint(0, 1)
    sample = 1
    temperature = ''
    #if sample is 0: temperature = '-temperature %s' % uniform(0.1, 0.9)
    #temperature = '-temperature %s' % uniform(0.1, 0.3)

    while True:
        final_path = None
        sampling = False
        while final_path is None and not sampling:
            sampling = True
            generate_path = "th sample.lua -checkpoint %s -length %s -start_text M -sample %s %s -gpu -1" % (VERSIONS[version], length, sample, temperature)
            print("Generating....")
            print(generate_path)
            print("**********************************")
            nn_output = subprocess.getoutput(generate_path)
            reg_ex = re.compile(r'M.+Z')
            path_strings = reg_ex.findall(nn_output) 
            for path in path_strings:
                p = parse_path(path)
                if p.isclosed():
                    xmin, xmax, ymin, ymax = p.bbox()
                    width = xmax - xmin
                    print(width)
                    height = ymax - ymin
                    print(height)
                    print("**********************************")
                    if width > min_size and width < max_size and height > min_size and height < max_size:
                        final_path = p.d()
                        break
            sampling = False

        with open('shapes.txt', 'r+') as f:
            svgs = f.read().splitlines()
            if final_path not in svgs:
                f.write(path + '\n')
                forever = False
                break
    return final_path


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
    max_per_page = 30
    paths = get_all_paths()
    response = jsonify({ 'paths': paths[0:max_per_page] })
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

if __name__ == '__main__':
    app.run(debug=True)
    #generate(repeat=True)
