""" Simple server that returns a path string generated from a char model RNN """
from __future__ import division, print_function

import re
import subprocess
import threading

from flask import Flask, jsonify
from svgpathtools import parse_path, Path

app = Flask(__name__.split('.')[0]) # pylint: disable=invalid-name

def get_all_paths():
    with open('shapes.txt', 'r') as f:
        paths = [line.rstrip() for line in f.readlines()]
        paths = list(reversed(paths))
        return paths

def generate(version = 0, min_size = 2, max_size = 500, repeat=False):
    """ Returns an SVG path as a string """
    versions = ['cv/paths_60000.t7', 'cv/paths1116_195000.t7', 'cv/paths1120_50000.t7', 'cv/paths_1124_33000.t7']
    if repeat:
        threading.Timer(60.0, generate).start()
    while True:
        final_path = None
        while final_path is None:
            print("Generating....")
            generate_path = "th sample.lua -checkpoint %s -length 1000 -start_text M -sample 1 -temperature 0.5 -gpu -1" % versions[version]
            print(generate_path)
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
    path = generate(int(version))
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
    generate(repeat=True)
