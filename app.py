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

def generate(min_size=2, max_size = 500):
    """ Returns an SVG path as a string """
    print("Generating....")
    forever = True
    while forever:
        final_path = None
        while final_path is None:
            generate_path = ('th sample.lua -checkpoint cv/paths_60000.t7 -length 3500 '
                '-start_text M -sample 1 -temperature 0.5').split()
            nn_output = subprocess.check_output(generate_path).decode('utf-8')
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
    print("Finished generating..." + final_path)
    threading.Timer(60 * 10, generate).start()
    return final_path


@app.route('/generate')
def new_path():
    generate()
    paths = get_all_paths()
    response = jsonify({ 'paths': paths })
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route('/')
def index():
    max_per_page = 6
    paths = get_all_paths()
    response = jsonify({ 'paths': paths[0:max_per_page] })
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

if __name__ == '__main__':
    threading.Timer(60 * 10, generate).start()
    app.run(debug=True)
