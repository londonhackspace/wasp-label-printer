#!/usr/bin/env python

import serial,os,sys,hexdump,argparse

#
# ~!A for free space.
# 

class wasp:
  def __init__(self, dev="/dev/ttyUSB0"):
    self.dev = dev
    self.s = serial.Serial(dev, 9600)
    self.setup()
    self.status()
  
  def setup(self):
    # starts at 9600 8 n 1
    # 56k
    # SET COM1 56,N,8,1
    # we might want to change reference
    # CODEPAGE 850 is
    # 8 BIT MODE, MULTILINGUAL
    init = """
SET CUTTER BATCH
SET GAP 16
SIZE 57 mm, 19 mm
GAP 3 mm,0
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
    init = init.split()
    for i in init:
      self.s.write(i + "\n")


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

  def close(self):
    self.s.close()

if __name__ == "__main__":
#  parser = 

  w = wasp()

  action = 'list'

  if len(sys.argv) == 2:
    file = sys.argv[1]
    action = 'upload'

  if action == 'list':
    w.list_files()
  elif action == 'upload':
    w.upload_file(file)
    w.list_files()
  
  w.close()

