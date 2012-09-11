#!/usr/bin/env python
from flask import Flask, render_template, send_file, request, jsonify
app = Flask(__name__)

import os
import rrdtool
import tempfile
import urllib
from datetime import datetime

DBDIR = './dbs'

COLOR_BITS = ('00', '88', 'ff')

COLORS = []
for R in COLOR_BITS:
  for G in COLOR_BITS:
    for B in COLOR_BITS:
      COLORS.append('%s%s%s' % (R, G, B))
for base_color in ('ffff00', 'ff0000', '00ff00', '0000ff'):
  COLORS.remove(base_color)
  COLORS.insert(0, base_color)

HTML_TEMPLATE = '''<html>
<head>
  <title>%s - %s</title>
</head>
<body onload="self.setTimeout(function() {location.reload()}, 30000)" style="margin: 0;">
  <img src="%s/graph/%s/img%s" alt="%s graph"/>
</body>
</html>'''

@app.route('/test')
def test():
  html = '<html><head><title>TEST</title></head><body>'
  print '\n'.join(COLORS)
  for COLOR in COLORS:
    html += '<div style="width: 100px; height:20px;font-family:monospace;background-color: #%s">%s</div>' % (COLOR, COLOR)
  html += '</body></html>'
  return html

@app.route('/update/<db_name>/<data>')
def update(db_name, data):
  db_path = _get_db_path(db_name)
  rrdtool.update(db_path, str(data))
  return '', 206

@app.route('/info/<db_name>')
def info(db_name):
  db_path = _get_db_path(db_name)
  return jsonify(rrdtool.info(db_path))

@app.route('/graph/<db_name>')
def graph_html(db_name):
  query_string = request.url.replace(request.base_url, '')
  timestamp = datetime.isoformat(datetime.now()).split('.')[0].replace('T', ' ')
  return HTML_TEMPLATE % (db_name,timestamp,request.environ['SCRIPT_NAME'],db_name,query_string,db_name)

@app.route('/graph/<db_name>/img')
def graph_img(db_name):
  db_path = _get_db_path(db_name)
  tmp = tempfile.mktemp('.png')
  options_dict = request.args
  data_list = _deduplicate([data.split('[')[-1].split(']')[0] for data in rrdtool.info(db_path).keys() if data.startswith('ds[')])
  defs = ['DEF:%s=%s:%s:AVERAGE' % (data, db_path, data) for data in data_list]
  lines = ['LINE2:%s#%s:%s' % (data, COLORS[idx], data) for idx, data in enumerate(data_list)]
  options, raw_options = _dict2options(options_dict) 
  args = options + defs + lines + raw_options
  rrdtool.graph(tmp, *args)
  return send_file(tmp)

def _dict2options(dictionary):
  options = []
  raw_options = []
  for key, value in dictionary.items():
    if key != 'raw_opts':
      options.append('--' + key)
      if value != '':
        options.append(str(value))
  if 'raw_opts' in dictionary.keys():
    raw_options = str(urllib.unquote(dictionary['raw_opts'])).split(' ')
  return options, raw_options
      
def _get_db_path(db_name):
  return os.path.join(DBDIR, '%s.rrd' % (db_name,)).encode()

def _deduplicate(data_list):
  data_list.sort()
  return reduce(lambda x,y: x.split(':')[-1] != y and ':'.join((x, y)) or x ,data_list).split(':')

if __name__ == "__main__":
  import sys
  app.run(debug='-d' in sys.argv)
