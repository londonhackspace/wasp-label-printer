#!/usr/bin/env python
import sys, time, os, json, logging, argparse
import BaseHTTPServer, urlparse, urllib, socket

from logging.handlers import SysLogHandler
from wasp import wasp, lhsStickers

class WaspD:
  def __init__(self):
    pass
    
  def run(self):
    logging.info("waspd starting up")
    while True:
      time.sleep(1)

# from
# http://trac.itek.norut.no/svn/n4c/trunk/HikerDaemon/WebServer.py
class MyWebServer(BaseHTTPServer.HTTPServer):
  """
  Non-blocking, multi-threaded IPv6 enabled web server
  """

  if socket.has_ipv6:
    address_family = socket.AF_INET6

  # Override in case python has IPv6 but system does not
  def __init__(self, server_address, RequestHandlerClass):
    try:
      BaseHTTPServer.HTTPServer.__init__(self,
                                        server_address,
                                        RequestHandlerClass)
    except:
      log.exception("Failed to use IPv6, using IPv4 instead")
      self.address_family = socket.AF_INET
      BaseHTTPServer.HTTPServer.__init__(self,
                                        server_address,
                                        RequestHandlerClass)

class Handler(BaseHTTPServer.BaseHTTPRequestHandler):
  # Disable logging DNS lookups
  def address_string(self):
    return str(self.client_address[0])
  
  def log_message(self, fmt, *args):
    logging.info(fmt % args)
  
  def do_GET(self):
    url = urlparse.urlparse(self.path)
    params = urlparse.parse_qs(url.query)
    path = url.path

    path = path.lstrip('/')
    message = urllib.unquote(path).decode('utf8')

    self.send_error(404)
    self.end_headers()
    self.wfile.write('hello not there: %s' % message)

  def do_POST(self):
    url = urlparse.urlparse(self.path)
    params = urlparse.parse_qs(url.query)
    path = url.path

#    logging.info(url)
    logging.info( "Command: %s Path: %s Headers: %r"
                    % ( self.command, self.path, self.headers.items() ) )

    data = None
#    if self.headers.has_key('content-type') and self.headers['content-type'] == "application/json":
    if self.headers.has_key('content-length'):
      data = self.rfile.read(int(self.headers['content-length']))
      try:
        data = json.loads(data)
      except ValueError, e:
        self.send_error(400)
        self.end_headers()
        self.wfile.write('Bad request: %s' % e)
        return
    else:
      self.send_error(400)
      self.end_headers()
      self.wfile.write('No Content-Length header')
      return

    ok = True
    logging.info(data)

    def check_keys(data, keys):
      for k in keys:
        if k not in data:
          self.send_error(400)
          self.end_headers()
          self.wfile.write('Bad request: missing key %s' % k)
          return
      # the printer only does code page 850
      # so re-encode all the data just in case
      for k in data.keys():
        if type(data[k]) == type(u"string"):
          data[k] = data[k].encode('cp850', 'replace')
      return data

    if path == "/print/dnh":
      keys = ('storage_id', 'name', 'ownername', 'completion_date', 'max_extention', 'more_info')
      data = check_keys(data, keys)
      id = False
      try:
        id = int(data['storage_id'])
      except ValueError, e:
        self.send_error(400)
        self.end_headers()
        self.wfile.write('Bad request: %s' % e)
        return

        
      # actually print it.
      s.lhs_dnh_new(str(data['storage_id']), data['ownername'], data['name'], data['completion_date'], data['max_extention'], data['more_info'])
      
    elif path == '/print/nod':
      # don't actually need any keys
      data = check_keys(data, ('id','name','email'))

      date = time.strftime('%a %d/%m/%y', time.localtime(time.time())).encode('cp850', 'replace')
      s.lhs_nod(date, data['id'], data['name'], data['email'])

    elif path == '/print/hackme':
      data = check_keys(data, ('donor_name', 'donor_id', 'donor_email', 'dispose_date', 'more_info'))
      s.lhs_hackme(data['donor_id'], data['donor_name'], data['donor_email'], data['dispose_date'], data['more_info'])
      
    elif path == '/print/fixme':
      data = check_keys(data, ('name', 'reporter_id', 'reporter_name', 'reporter_email', 'more_info'))
      s.lhs_fixme(data['name'], data['reporter_id'], data['reporter_name'], data['reporter_email'], data['more_info'])

    elif path == '/print/box':
      data = check_keys(data, ('owner_id', 'owner_name'))
      s.lhs_box(data['owner_id'], data['owner_name'])

    elif path == '/print/badge':
      data = check_keys(data, ('name', 'items'))

      things = data['items']
      if len(things) > 0:
        # cp850 the individual contact items
        for k in things.keys():
          if type(things[k]) == type(u"string"):
            things[k] = things[k].encode('cp850', 'replace')

      s.lhs_badge(data['name'], things)

    else:
      self.send_error(404)
      self.end_headers()
      self.wfile.write('hello not there: %s' % url.path)
      return

    if ok:
      self.send_response(200)
      self.send_header('Content-type', 'text/plain')
      self.end_headers()
      self.wfile.write("OK\n")
      return
    else:
      self.send_response(400)
      self.send_header('Content-type', 'text/plain')
      self.end_headers()
      self.wfile.write("something broke\n")
      return

def parse_args():
  parser = argparse.ArgumentParser()
  parser.add_argument('-f', '--foreground', action='store_true')
  parser.add_argument('--port',
      type=str, nargs=1, metavar=('<port>'),
          help='The serial port to use')

  args = parser.parse_args()
  return args

def set_logger():
  if args.foreground:
    logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s', level=logging.DEBUG)
  else:
    logfac = "daemon"
    logfac = SysLogHandler.facility_names[logfac]
    logger = logging.root
    logger.setLevel(logging.DEBUG)
    syslog = SysLogHandler(address='/dev/log', facility=logfac)
    formatter = logging.Formatter('waspd[%(process)d]: %(levelname)-8s %(message)s')
    syslog.setFormatter(formatter)
    logger.addHandler(syslog)

def daemonise():
  from daemon import DaemonContext
  from pidfile import PidFile
  daemon = DaemonContext(pidfile=PidFile("/var/run/waspd.pid"))
  daemon.open()

  logging.info('Daemonised waspd')

if __name__ == "__main__":
  args = parse_args()

  set_logger()
  logging.info("waspd starting up")

  if args.port:
    w = wasp(args.port[0])
  else:
    w = wasp()

  s = lhsStickers(w)
  
  httpd = MyWebServer(('', 12345), Handler)
#  BaseHTTPServer.HTTPServer(("::", 12345), Handler)
  httpd.serve_forever()

#  if not args.foreground:
#    daemonise()

#

#  wd = WaspD()
#  try:
#    wd.run()

  # Top-level handlers because we're daemonised
#  except Exception, e:
#    logging.exception("Exception in main loop: %s" % e)
#  except:
#    logging.exception("Non-Exception caught")

