#!/usr/bin/env python

import serial,os,sys,hexdump,argparse,textwrap,time

#
# ~!A for free space.
# 

class wasp:
  def __init__(self, dev="/dev/ttyUSB0"):
    self.dev = dev
    self.s = serial.Serial(dev, 9600)
    self.status()
    if self.s.inWaiting() > 0:
      s = ''
      while self.s.inWaiting() > 0:
        s += self.s.read(1)
        time.sleep(0.1)
      print s
  
  def setup(self):
    # starts at 9600 8 n 1
    # 56k
    # SET COM1 56,N,8,1
    # we might want to change reference
    # CODEPAGE 850 is
    # 8 BIT MODE, MULTILINGUAL
    #
    # old stickers: 
    #
    # SIZE 57 mm, 19 mm
    # GAP 3 mm,0
    #
    init = """SET CUTTER BATCH
SET GAP 8
SET RIBBON OFF
SIZE 101 mm, 101 mm
GAP 4 mm,0
SPEED 2
DENSITY 7
DIRECTION 1
REFERENCE 10,10
COUNTRY 044
CODEPAGE BRI
CODEPAGE 850
HOME
CLS
"""
    init = init.split("\n")
    for i in init:
      self.s.write(i + "\n")
      print i
      time.sleep(0.01)
      if self.s.inWaiting() > 0:
        s = ''
        while self.s.inWaiting() > 0:
          s += self.s.read(1)
        print s

    if self.s.inWaiting() > 0:
      s = ''
      while self.s.inWaiting() > 0:
        s += self.s.read(1)
      print s

  def status(self):
    self.s.write('\x1b!?')
    r = ord(self.s.read(1))
    print "%x : %s" % (r, hexdump.tobin(r))
    sbits = """
0
1
2
3
4
5
6
7
Head opened
Paper jam
Out of paper
Out of ribbon
Pause
Printing
Cover opened (option)
Environment Temperature over range (option)
"""

  def list_files(self):
    s = self.s
    s.write("~!F")
    data = ''
    while True:
      c = s.read(1)
      if ord(c) == 0x1a:
        break
      data += c
    hexdump.hexdump(data)
    data = data.split(chr(0x0d))
    print data

  def delete_file(self, filename):
    comm = "KILL \"%s\"\n" % (filename)
    print comm
    self.s.write(comm)

  def upload_file(self, file):
    filename = os.path.basename(file).upper()
    fh = open(file, "rb")
    data = fh.read()
    comm =  "DOWNLOAD \"%s\",%d," % (filename, len(data))
    print comm
    data = comm + data
    print len(data)
    hexdump.hexdump(data)
    self.s.write(comm + data)
#  s.flush()
    print "wait: ", self.s.inWaiting()
#  hexdump.hexdump(s.read())
    self.status()

#  s.flush()
#  s.write("DOWNLOAD \"DATA2\",10,ABCDEFGHIJ")

  def qr_code(self,qr):
    if len(qr) > 60:
      raise RuntimeError, "qr code too long"
    qr = "QRCODE 5,5,M,4,M,0,M2,S7,\"B%04d%s\"" % (len(qr), qr)
    self.s.write(qr + "\n")

  def qr_width(self, qr):
    # return the width in dots of a qr code.
    width = 11
    if len(qr) >= 16:
      width = 13
    if len(qr) >= 28:
      width = 15
    if len(qr) >= 44:
      width = 17
    if len(qr) >= 64:
      width = 19
    
    print "for qr len %d, width %d : %d" % (len(qr), width, width * 8)
    
    return (width * 8)

  def qr_and_text(self, qr, text):
    self.s.write("CLS\n")
    self.qr_code(qr)
    width = self.qr_width(qr)
#    comm = "TEXT %d,5,\"8\",0,2,2,\"%s\"\n" % (width, text)
    comm = "TEXT %d,5,\"3\",0,1,1,\"%s\"\n" % (width, text)
    print comm
    self.s.write(comm)
    self.s.write("PRINT 1\n")

  def text(self, x, y, text, font=3):
    # fonts:
    # 1 8 x 12
    # 2 12 x 20
    # 3 16 x 24 <- default
    # 4 24 x 32
    # 5 32 x 48
    # 6 14 x 19	ocr-b
    # 7 21 x 27 ocr-b
    # 8 14 x 25 ocr-a
    # ROMAN.TTF Roman True Type Font
    comm = "TEXT %d,%d,\"%d\",0,1,1,\"%s\"\n" % (x, y, font, text)
    self.s.write(comm)

  def close(self):
    print "bye!"
    if self.s.inWaiting() > 0:
      hexdump.hexdump(self.s.read(self.s.inWaiting()))
    self.status()
    self.s.close()
  
  def email_to_qr(self, email):
    return "MATMSG:TO:%s;;" % (email)

  def url_to_qr(self, url, title):
    return "MEBKM:TITLE:%s;URL:%s;;" % (title, url)

if __name__ == "__main__":
  parser = argparse.ArgumentParser(description='Talk to a WASP WPL305 label printer.')
  
  parser.add_argument('--upload', type=str, nargs=1, metavar=('<filename>'),
    help='a bitmap (.bmp or .pcx, 1bpp) to upload')

  parser.add_argument('--list', action='store_true',
    help='list files')

  parser.add_argument('--init', action='store_true',
    help='Initialise the printer, use after power cycle or ink/paper change')

  parser.add_argument('--lhs',
    type=str, nargs=1, metavar=('<membership no.>'),
    help='an lhs membership number, produces a sticker with a qr code')

#  parser.add_argument('--lhs-long',
#    type=str, nargs=3, metavar=('<membership no.>', '<name>', '<url>'),
#    help='an lhs membership number, name, and url, produces a sticker with a 2 qr codes')

  parser.add_argument('--lhs-dnh',
    type=str, nargs=3, metavar=('<membership no.>', '<name>', '<email>'),
    help='a Do Not Hack Sticker: lhs membership number, name, and email.')

  parser.add_argument('--text',
    type=str, nargs=1, metavar=('<text>'),
    help='just some text, don\'t forget to quote it!')

  parser.add_argument('--twotext',
    type=str, nargs=2, metavar=('<title>', '<text>'),
    help='a title and some text, don\'t forget to quote them!')

  parser.add_argument('--urlnametext',
    type=str, nargs=3, metavar=('<url>', '<title>', '<text>'),
    help='a url (will be a qrcode), a title and some text, don\'t forget to quote them!')

  args = parser.parse_args()

  w = wasp()

  if args.init:
    w.setup()

  print args

  if args.upload:
    file = args.upload
    w.upload_file(file)
    w.list_files()
  elif args.list:
    w.list_files()
  elif args.lhs:
    id = None
    try:
      id = int(args.lhs[0])
      id = "HS%05d" % (id)
    except ValueError:
      id = args.lhs[0]
    w.qr_and_text(id, id)
  elif args.lhs_dnh:
    id = None
    try:
      id = int(args.lhs_dnh[0])
      id = "HS%05d" % (id)
    except ValueError:
      id = args.lhs_dnh[0]
    name = args.lhs_dnh[1]
    email = args.lhs_dnh[2]

    w.s.write("CLS\n")
    w.qr_code(w.email_to_qr(email))
    width = w.qr_width(w.email_to_qr(email))
    print width, len(w.email_to_qr(email))
    width += 2
    # with this font max width is ~ 20 chars.
    # XXX zoom font if more room
    w.text(width, 5, "Do Not Hack.")
    w.text(width, 5 + 24 + 4, name)
    w.text(width, 5 + ((24 + 4) * 2), email)
    w.s.write("PRINT 1\n")
  elif args.text:
    text = args.text[0]
    wrapper = textwrap.TextWrapper(width=27, expand_tabs=False)
    tbits = wrapper.wrap(text)
    w.s.write("CLS\n")
    x = 5
    for t in tbits:
      print x
      w.text(5, x, t)
      x = x + 22
    w.s.write("PRINT 1\n")
  elif args.twotext:
    title = args.twotext[0]
    text = args.twotext[1]
    wrapper = textwrap.TextWrapper(width=27, expand_tabs=False)
    tbits = wrapper.wrap(text)
    w.s.write("CLS\n")
    w.text(5, 5, title, 5)
    x = 5 + 48 +10
    for t in tbits:
      print x
      w.text(5, x, t, 7)
      x = x + 22
    w.s.write("PRINT 1\n")
  elif args.urlnametext:
    url = args.urlnametext[0]
    title = args.urlnametext[1]
    text = args.urlnametext[2]
    qrtext = w.url_to_qr(url, title)
    qrwidth = w.qr_width(qrtext)
    
    # do something with font size to get right text width
    wrapper = textwrap.TextWrapper(width=20, expand_tabs=False)
    tbits = wrapper.wrap(text)

    w.s.write("CLS\n")
    w.qr_code(qrtext)
    w.text(5 + qrwidth + 5, 5, title, 5)
    x = 5 + 48 +10
    for t in tbits:
      print x
      w.text(5 + qrwidth + 5, x, t, 7)
      x = x + 22
    w.s.write("PRINT 1\n")
    
  w.close()
