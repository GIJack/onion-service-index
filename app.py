#!/usr/bin/env python3
import sys
sys.path.append('/usr/lib/python3.8/site-packages')
import random
import configparser
import logging
from flask import Flask
from flask import abort, make_response, redirect, render_template, request
from flask import url_for

app = Flask(__name__)

#DEFAULTS
configuration = {
    "config_file" : "/etc/onion-service-index.config",
    "listen_port" : 8765,
    "listen_addr" : "localhost",
    "logfile"     : "/var/log/onion-service-index.log",
}
# try and read from a config   
try: 
   fileConfig = configparser.RawConfigParser()
   fileConfig.read(configuration.config_file)
   try:
       configuration[listen_port] = fileConfig.get("general","port")
       configuration[listen_addr] = fileConfig.get("general","address")
       configuration[logfile]     = fileConfig.get("general","logfile")
   except:
       print("Config read error, falling back to defaults...")
       pass
except:
    print("Could not open " + configuration["config_file"] + ", using defaults")
    pass

# Set up Logging
logger = logging.getLogger('onion-service-index')
logger.setLevel(logging.INFO)
log_handler = logging.FileHandler(configuration["logfile"])
logger.addHandler(log_handler)

BASE32_CHARS = list('234567abcdefghijklmnopqrstuvwxyz')
PAGE_LENGTH = 128
NUM_ONIONS = 32**16, 32**55
ONION_LENGTH = 16, 56

app.debug = False
app.jinja_env.globals.update({
    'app_name': 'All Onion Services',
    'num_onions': NUM_ONIONS,
    'page_length': PAGE_LENGTH,})

def num_to_base(n, b=10, min_length=0):
    digits = []
    while n:
        digits.append(int(n % b))
        n //= b
    if len(digits) < min_length:
        num_zeros = min_length - len(digits)
        digits.extend([0] * num_zeros)
    return digits[::-1]

def translate_with_lookup(digits, lookup):
    return ''.join([ lookup[d] for d in digits])

def get_page_url(page=1, v3=False):
    return '?page=%s' % page + ('&amp;v3' if v3 else '')

app.jinja_env.globals['get_page_url'] = get_page_url

def get_page_nav(current_page, v3=False):
    start = current_page - 10
    num_onions = NUM_ONIONS[v3]
    if start < 1:
	    start = 1
    end = current_page + 10
    if end > num_onions / PAGE_LENGTH:
        end = num_onions // PAGE_LENGTH
    return range(start, end+1)

def gen_page(page=1, v3=False, do_cache=True):
    num_onions = NUM_ONIONS[v3]
    onion_length = ONION_LENGTH[v3]
    if page < 1: page = 1
    if page > num_onions / PAGE_LENGTH:
        page = num_onions // PAGE_LENGTH
    start = (page - 1) * PAGE_LENGTH
    end = page * PAGE_LENGTH
    onions = [ num_to_base(o, 32, onion_length) for o in range(start, end) ]
    onions = [ translate_with_lookup(o, BASE32_CHARS) + ('d' if v3 else '') for o in onions ]
    nav = get_page_nav(page, v3)
    resp = make_response(render_template('index.html.j2',
        onions=onions, page=page, nav=nav))
    if do_cache: resp.headers['Cache-Control'] = 'max-age=600'
    return resp

@app.route('/', methods=['GET'])
def index_():
    if request.method != 'GET': abort(405)
    page = 1
    if 'page' in request.args:
        try: page = int(request.args['page'])
        except ValueError: page = 1
    v3 = 'v3' in request.args
    return gen_page(page, v3)

@app.route('/random', methods=['GET'])
def random_():
    if request.method != 'GET': abort(405)
    v3 = 'v3' in request.args
    num_onions = NUM_ONIONS[v3]
    max_page = num_onions // PAGE_LENGTH
    page = random.randint(1, max_page)
    page_url = '?page={}'
    page_url = page_url.format(page)
    if v3: page_url += '&v3'
    #return redirect(page_url.format(page), code=302)
    return redirect(url_for('index_')+page_url, code=302)


if __name__ == '__main__':
    app.run(host=configuration["listen_addr"], port=configuration["listen_port"])
