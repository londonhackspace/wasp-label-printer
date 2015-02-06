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

    self.fonts = {
      1 : {"width": 8, "height": 12},
      2 : {"width": 12, "height": 20},
      3 : {"width": 16, "height": 24}, # default
      4 : {"width": 24, "height": 32},
      5 : {"width": 32, "height": 48}, # big and good for titles.
      6 : {"width": 14, "height": 19}, # ocr-b
      7 : {"width": 21, "height": 27}, # ocr-b, ugly with wide spacing.
      8 : {"width": 14, "height": 25}, # ocr-a
    }
    # was 27 for the old stickers.
    # 45 for font 3
    self.width_in_chars = {
    1: 90,
    2: 59,
    3: 45,
    6: 52,
    }
    #
    # 8 dots per mm at 200dpi
    # we are at 200dpi, dunno if setting or printer model specific
  
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
    # COUNTRY 044
    # CODEPAGE BRI

    init = """SET CUTTER BATCH
SET GAP 8
SET RIBBON OFF
SIZE 101 mm, 101 mm
GAP 4 mm,0
SPEED 2
DENSITY 7
DIRECTION 1
REFERENCE 10,10
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

  def qr_code(self, qr, x=5, y=5, cell_width=4):
    qr = "QRCODE %d,%d,M,%d,M,0,M2,S7,\"B%04d%s\"" % (x, y, cell_width, len(qr), qr)
    self.s.write(qr + "\n")

  def qr_width(self, qr):
    # return the width in dots of a qr code.
    # XXX needs to work for longer qr codes now!
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
    text = text.replace('"', '\\"')
    comm = "TEXT %d,5,\"3\",0,1,1,\"%s\"\n" % (width, text)
    print comm
    self.s.write(comm)
    self.s.write("PRINT 1\n")

  def text(self, x, y, text, font=3):
    # fonts:
    # 1 8 x 12
    # 2 12 x 20
    # 3 16 x 24 <- default, 2mm wide
    # 4 24 x 32
    # 5 32 x 48
    # 6 14 x 19	ocr-b
    # 7 21 x 27 ocr-b
    # 8 14 x 25 ocr-a
    # ROMAN.TTF Roman True Type Font
    text = text.replace('"', '\\"')
    comm = "TEXT %d,%d,\"%d\",0,1,1,\"%s\"\n" % (x, y, font, text)
    self.s.write(comm)

  def name_value(self, name, value, x, y, font = 3):
    # prints
    # name: value
    # returns: the y co-ord for the next whatever.
    self.text(x, y, name, font)
    self.s.write("BAR %d,%d,%d,1\n" % (x, y + self.fonts[font]["height"], self.fonts[font]["width"] * len(name)))
    self.text(x + (self.fonts[font]["width"] * len(name)) + 5, y, value, font)
    
    return y + (self.fonts[font]["height"] * 2) + 5

  def name_para(self, name, para, x, y, font=3):
    # prints
    # name
    # wrapped paragraph
    # returns: the y co-ord for the next whatever.
    self.text(x, y, name)
    y = y + self.fonts[font]["height"]
    self.s.write("BAR %d,%d,%d,1\n" % (x, y, self.fonts[font]["width"] * len(name)))
    y = y + 5
    
    wrapper = textwrap.TextWrapper(width=self.width_in_chars[font], expand_tabs=False)
    tbits = wrapper.wrap(para)
    
    for t in tbits:
      self.text(x, y, t)
      y = y + self.fonts[font]["height"] + 5
    
    return y + self.fonts[font]["height"] + 5

  def para(self, text, x, y, font = 3):
    wrapper = textwrap.TextWrapper(width=self.width_in_chars[font], expand_tabs=False)
    tbits = wrapper.wrap(text)
    
    for t in tbits:
      self.text(x, y, t, font)
      y = y + self.fonts[font]["height"] + 5
    
    return y + self.fonts[font]["height"] + 5

  # at the top by default
  # centered
  def title(self, title, font=5, y=5):
    t_width = self.fonts[5]["width"] * len(title)
    t_pos = (((101 * 8) - 10) - t_width) / 2
    self.text(5 + t_pos, y, title, 5)

    return y + self.fonts[5]["height"] * 2

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

class lhsStickers:
  def __init__(self, wasp):
    self.wasp = wasp

  def lhs(self, id):
    try:
      oid = int(id)
      oid = "HS%05d" % (oid)
    except ValueError:
      oid = id
    self.wasp.qr_and_text(id, id)

  def profile_url(self, id):
    try:
      _ = int(id)
    except ValueError:
      raise
    # XXX hack.rs needs to have https
    return "http://hack.rs/pr/" + id
  
  def lhs_dnh(self, id, owner, email, completion, more):
    #
    # needs:
    # 
    # title: Do not hack
    #
    # Project name
    # Owner name
    # estimated completion date
    # days maximum time extention
    # qrcode: "https://london.hackspace.org.uk/storage/" + storage_id
    # more info
    #
    # email?
    # phone number?
    #
    w = self.wasp
    try:
      _ = int(id)
    except ValueError:
      # XXX logging + errors
      print "id should be a number, not " + id
      exit(1)

    w.s.write("CLS\n")

    # as we go down we will increase this
    # (0,0 is top right)
    y = 5

    # start with the title
    title = "Do Not Hack!"

    # in dots
    t_width = w.fonts[5]["width"] * len(title)
    t_pos = (((101 * 8) - 10) - t_width) / 2
    w.text(5 + t_pos, y, title, 5)

    y += w.fonts[5]["height"] + 5

    y = w.name_value("Name:", owner, 5, y)

    # profile url
    profile = self.profile_url(id)
    profile_qr = w.url_to_qr(profile, "Profile")
    w.qr_code(profile_qr, 5, y)
    width = w.qr_width(profile_qr)
    y += width + 5

    y = w.name_value("Email:", email, 5, y)

    w.qr_code(w.email_to_qr(email), 5, y)
    width = w.qr_width(w.email_to_qr(email))

    y += width + 5

    y = w.name_value("Estimated Completion Date:", completion, 5, y)
    y = w.name_value("Tell us more about it:", more, 5, y)
    
    w.s.write("PRINT 1\n")

  def lhs_dnh_new(self, storage_id, owner, name, completion, extention, more_info):
    #
    # needs:
    # 
    # title: Do not hack
    #
    # Project name
    # Owner name
    # estimated completion date
    # days maximum time extention
    # qrcode: "https://london.hackspace.org.uk/storage/" + storage_id
    w = self.wasp

    w.s.write("CLS\n")

    # as we go down we will increase this
    # (0,0 is top right)
    y = 5

    # start with the title
    y = w.title("Do Not Hack!")

    y = w.name_value("Project:", name, 5, y)
    y = w.name_value("Owner:", owner, 5, y)
    y = w.name_value("Estimated Completion Date:", completion, 5, y)
    y = w.name_value("Maximum time extension (days):", extention, 5, y)
    y = w.name_para("More info:", more_info, 5, y)
    y = w.name_value("Storage id:", storage_id, 5, y)

    storage = "https://london.hackspace.org.uk/storage/" + storage_id

    y = w.name_para("Storage url:", storage, 5, y)
        
    # storage request url
    storage_qr = w.url_to_qr(storage, "Storage")
    w.qr_code(storage_qr, 5, y)
    width = w.qr_width(storage_qr)
    y += width + 10

    w.s.write("PRINT 1\n")

  def lhs_nod(self, date, id, name, email):
    try:
      _ = int(id)
    except ValueError:
      # XXX logging + errors
      print "id should be a number, not " + id
      exit(1)

    w = self.wasp
    w.s.write("CLS\n")
    x = 5
    y = w.title("* Notice of Disposal *")

    text = ("This item is to be treated as if it is in the 3 week bin "
            "process due to not having a completed Do Not Hack "
            "sticker. See the wiki for details http://hack.rs/wiki")
    y = w.para(text, x, y, 2)
    
    text = ("Please read the rules regarding storing items in the "
            "hackspace. http://hack.rs/rules")
    y = w.para(text, x, y, 2)

    text = ("Any questions? - contact IRC: http://hack.rs/irc "
            "or the mailing list: http://hack.rs/list")
    y = w.para(text, x, y, 2)

    y = w.para("Date this sticker was applied: " + date, x, y, 2)
    y = y - w.fonts[3]["height"]
    y = w.name_value("Stuck by: ", name, x, y, 2)
    y = y - w.fonts[2]["height"]
    y = w.name_value("Email: ", email, 5, y, 2)
    y = y - w.fonts[2]["height"]

    # profile url
    profile = self.profile_url(id)
    profile_qr = w.url_to_qr(profile, "Profile")
    oy = y
    w.qr_code(profile_qr, 5, y)
    width = w.qr_width(profile_qr)
    y += width + 10

    w.qr_code(w.email_to_qr(email), 5 + width + 10, oy)
    width = w.qr_width(w.email_to_qr(email))
    
    if (oy + width + 5 > y):
      y = oy + width + 5
    else:
      y += width + 5

    w.s.write("PRINT 1\n")

  def lhs_hackme(self, donor_id, name, email, dispose, info):
    w = self.wasp
    w.s.write("CLS\n")
    y = 5
    x = 5
    y = w.title("* Hack Me *")

    y = w.name_para("Info:", info, x, y)
    y = w.name_value("Donor:", name, x, y)
    y = w.name_value("Email:", email, x, y)

    # XXX qrcode to donor profile?

    y = w.name_value("Dispose By:", dispose, x, y)
    
    w.s.write("PRINT 1\n")
    
  def lhs_fixme(self, name, reporter_id, reporter_name, reporter_email, info):
    w = self.wasp
    w.s.write("CLS\n")
    y = 5
    x = 5
    y = w.title("** Fix Me **")

    y = w.name_para("Name:", name, x, y)
    y = w.name_value("Reporter:", reporter_name, x, y)
    y = w.name_value("Email:", reporter_email, x, y)

    # XXX qrcode to reporter profile?

    y = w.name_para("Why do I need Fixing? Fault symptoms?:", info, x, y)
    
    w.s.write("PRINT 1\n")

  def lhs_box(self, owner_id, name):
    w = self.wasp
    w.s.write("CLS\n")
    y = 5
    x = 5
    y = w.title(name)

    y = w.title("HS%05d" % (int(owner_id)), 5, y)

#    y = w.name_value("Member ID:", "HS%05d" % (int(owner_id)), x, y, 4)
    
    profile_url = self.profile_url(str(owner_id))
    profile_qr = w.url_to_qr(profile_url, "Profile")

    width = w.qr_width(profile_qr)
    width = width * 2 # default qr code has cell_width 4

    x = (795 / 2) - (width / 2)

    w.qr_code(profile_qr, x, y, 8)

#    y += width + 5
#    w.text(5, y, str(width))

    w.s.write("PRINT 1\n")
    
  def text(self, text):
    w = self.wasp
    wrapper = textwrap.TextWrapper(width=w.width_in_chars[3], expand_tabs=False)
    tbits = wrapper.wrap(text)
    w.s.write("CLS\n")
    y = 5
    for t in tbits:
#      print y
      w.text(5, y, t)
      y = y + self.fonts[3]["height"] + 5
    w.s.write("PRINT 1\n")

  def twotext(self, title, text):
    w = self.wasp
    wrapper = textwrap.TextWrapper(width=w.width_in_chars, expand_tabs=False)
    tbits = wrapper.wrap(text)
    w.s.write("CLS\n")
    w.text(5, 5, title, 5)
    y = 5 + w.fonts[5]["height"] + 10

    bodyfont = 3

    for t in tbits:
#      print y
      w.text(5, y, t, bodyfont)
      y = y + w.fonts[bodyfont]["height"] + 5
    w.s.write("PRINT 1\n")

  def urlnametext(self, url, title, text):
    w = self.wasp
    qrtext = w.url_to_qr(url, title)
    qrwidth = w.qr_width(qrtext)
    
    # do something with font size to get right text width
    total_width = (101 * 8) - 10 # 101mm * 8 dots per mm, - 5dots at the edges
    text_space = total_width - (qrwidth + 5)
    text_width = text_space / 21 # for font 7, 21 dots wide
    wrapper = textwrap.TextWrapper(width=self.text_width, expand_tabs=False)
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
    type=str, nargs=5, metavar=('<membership no.>', '<name>', '<email>', '<completion>', '<more info>'),
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

  parser.add_argument('--port',
    type=str, nargs=1, metavar=('<port>'),
    help='The serial port to use')

  parser.add_argument('--fonts', action='store_true',
    help='Print a font test')

  args = parser.parse_args()

  if args.port:
    w = wasp(args.port[0])
  else:
    w = wasp()

  if args.init:
    w.setup()

  s = lhsStickers(w)

#  print args

  if args.upload:
    file = args.upload
    w.upload_file(file)
    w.list_files()
  elif args.list:
    w.list_files()
  elif args.lhs:
    s.lhs(args.lhs[0])
  elif args.lhs_dnh:
    s.lhs_dnh(lhs_dnh[0], lhs_dnh[1], lhs_dnh[2], lhs_dnh[3], lhs_dnh[4])
  elif args.text:
    s.text(args.text[0])
  elif args.twotext:
    s.twotext(args.twotext[0], args.twotext[1])
  elif args.urlnametext:
    s.urlnametext(args.urlnametext[0], args.urlnametext[1], args.urlnametext[2])
  elif args.fonts:
    t = "ABCDabcd1234?;!@"
    x = 5
    y = 5
    w.s.write("CLS\n")
    for f in w.fonts.keys():
      w.text(x, y, str(f) + " : " + t, f) 
      y = y + w.fonts[f]["height"] + 10

    f = "ROMAN.TTF"
    comm = "TEXT %d,%d,\"%s\",0,12,12,\"%s\"\n" % (x, y, "ROMAN.TTF", str(f) + " : " + t)
    w.s.write(comm)

    y += 32
    f = 0
    comm = "TEXT %d,%d,\"%s\",0,12,12,\"%s\"\n" % (x, y, str(f), str(f) + " : " + t)
    w.s.write(comm)
    
    w.s.write("PRINT 1\n")

  w.close()
