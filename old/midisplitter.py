import os
f = open('/dev/midi1', 'wb+', 0) # unbuffered

rstat=0
origbytecount = 0
bytecount = 0
msg = []
insysex = False

def processMsg():
  global msg
  print ' '.join(['%02X'%x for x in msg]),
  if 0x80 <= msg[0] <= 0x9F:
    if msg[1] < 0x15+16:
      msg[0] |= (msg[1] - 0x15)
      msg[1] = 64 # middle C?
    # scale velocity
    msg[2] **= 1.05
    msg[2] *= (1.0-msg[1]/128.0)
    msg[2] = min(127, msg[2])
  if msg[0:2] == [0xB0, 0x40]: # sustain pedal
    msg = msg * 8
    for i in range(8):
      msg[i*3] |= i
  print '->', ' '.join(['%02X'%x for x in msg])
  f.write(''.join([chr(x) for x in msg]))

f.write('\xB0\x7A\x00')

f.write('\xC0\x00')
f.write('\xC1\x01')
f.write('\xC2\x04')
f.write('\xC3\x13')
f.write('\xC4\x06')
f.write('\xC5\x0B')
f.write('\xC6\x30')
f.write('\xC7\x34')


while 1:
  rx = ord(f.read(1))
  if (insysex and rx != 0xF7) or rx >= 0xF8:
     # sysex or system realtime - ignore
     continue
  elif rx == 0xF7:
    # end of sysex
    insysex = False
  elif rx == 0xF0:
    # start of sysex
    insysex = True
  elif rx >= 0xF0:
    # system common - clear running status
    rstat = 0
  elif rx >= 0x80:
    rstat = rx
    bytecount = 2
    if 0xC0 <= rx <= 0xDF:
       bytecount = 1
    origbytecount = bytecount
    msg = [rstat]
  else: # databyte
    if rstat:
      msg.append(rx)
      bytecount -= 1          
      if bytecount == 0:
        bytecount = origbytecount # reset counter for new databytes with rstat
        processMsg()
        msg = []
    # otherwise no running status - ignore databyte
  