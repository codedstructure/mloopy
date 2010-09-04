#!/usr/bin/env python2.5

import threading, time, sys, copy, pprint, Queue, struct
import hexdump

EOX = '\xF7'  # end of sysex
SOX = '\xF0'  # start of sysex
SYS_COM_BASE = '\xF0'
SYS_RT_BASE = '\xF8'

class MidiObj(object):
    def __mul__(self, other):
        res = MidiSeq()
        for _ in range(other):
            res.append(copy.copy(self))
        return res

    def __repr__(self):
        return "<%s:%s>"%(self.__class__.__name__,
                          pprint.pformat(dict((i,getattr(self,i)) for i in self.__slots__)))

    def __eq__(self, other):
        return ([(i,getattr(self,i)) for i in self.__slots__] ==
                [(i,getattr(other,i)) for i in other.__slots__])

class MidiSeq(list): pass

class NoteOn(MidiObj):
    format = struct.Struct('BBB')
    __slots__ = ['channel', 'note', 'vel']
    def __init__(self, note=64, vel=64, chan=0):
        self.note = note
        self.vel = vel
        self.channel = chan

    def tostring(self):
        return NoteOn.format.pack((self.channel | 0x90),
                                   self.note,
                                   self.vel)

    def fromstring(self, s):
        status, self.note, self.vel = NoteOn.format.unpack(s)
        self.channel = status & 0x0F
        return self

class NoteOff(MidiObj):
    format = struct.Struct('BBB')
    __slots__ = ['channel', 'note', 'vel']
    def __init__(self, note=64, vel=0, chan=0):
        self.note = note
        self.vel = vel
        self.channel = chan

    def tostring(self):
        return NoteOff.format.pack((self.channel | 0x80),
                                   self.note,
                                   self.vel)

    def fromstring(self, s):
        status, self.note, self.vel = NoteOff.format.unpack(s)
        self.channel = status & 0x0F
        return self


class PC(MidiObj):
    format = struct.Struct('BB')
    __slots__ = ['channel', 'prog']
    def __init__(self, prog=0, chan=0):
        self.prog = prog
        self.channel = chan

    def tostring(self):
        return PC.format.pack((self.channel | 0xC0),
                              self.prog)
    def fromstring(self, s):
        status, self.prog = PC.format.unpack(s)
        self.channel = status & 0x0F
        return self

class PAT(MidiObj):
    format = struct.Struct('BBB')
    __slots__ = ['channel', 'note', 'pressure']
    def __init__(self, note=64, pressure=0, chan=0):
        self.note = note
        self.pressure = pressure
        self.channel = chan

    def tostring(self):
        return PAT.format.pack((self.channel | 0xA0),
                                self.note,
                                self.pressure)

    def fromstring(self, s):
        status, self.note, self.pressure = PAT.format.unpack(s)
        self.channel = status & 0x0F
        return self

class CAT(MidiObj):
    format = struct.Struct('BB')
    __slots__ = ['channel', 'pressure']
    def __init__(self, pressure=0, chan=0):
        self.pressure = pressure
        self.channel = chan

    def tostring(self):
        return CAT.format.pack((self.channel | 0xD0),
                               self.pressure)
    def fromstring(self, s):
        status, self.pressure = CAT.format.unpack(s)
        self.channel = status & 0x0F
        return self

class CC(MidiObj):
    format = struct.Struct('BBB')
    __slots__ = ['channel', 'ctrl', 'value']
    def __init__(self, ctrl=0, value=0, chan=0):
        self.ctrl = ctrl
        self.value = value
        self.channel = chan

    def tostring(self):
        return CC.format.pack((self.channel | 0xB0),
                              self.ctrl,
                              self.value)
    def fromstring(self, s):
        status, self.ctrl, self.value = CC.format.unpack(s)
        self.channel = status & 0x0F
        return self

class PB(MidiObj):
    format = struct.Struct('BBB')
    __slots__ = ['channel', 'value']
    # TODO: make value signed +/- 8192
    def __init__(self, value=0x2000, chan=0):
        self.channel = chan
        self.value = value

    def tostring(self):
        return PB.format.pack((self.channel | 0xE0),
                              self.value & 0x7F,
                              self.value >> 7)
    def fromstring(self, s):
        status, b1,b2 = PB.format.unpack(s)
        self.channel = status & 0x0F
        self.value = (b2<<7)+b1
        return self

class MidiOutStream(object):
    def __init__(self, mf):
        self.mf = mf
        self.rstat = None
        self.insysex = False

    def put(self, msg):
        if isinstance(msg, MidiSeq):
            for x in msg:
                self.put(x)
            return

        #print "out:", msg
        data = msg.tostring()
        
        if not self.insysex:
            rx = data[0]
            if rx == EOX: self.insysex = False
            elif rx == SOX: self.insysex = True
            elif rx >= SYS_COM_BASE:
                # system common - clear running status
                self.rstat = 0
            elif rx >= '\x80':
                if self.rstat == rx:
                    data = data[1:]
                else:
                    self.rstat = rx
        self.mf.write(data)


class MidiLoad(object):
    def __init__(self, smf):
        try:
            self.f = file(smf+'', 'rb')
        except TypeError: # smf not a string
            self.f = smf 
    # TODO: port from MidiFileOutput

class MidiProcess(threading.Thread):
    daemon = True
    def __init__(self, f=None):
        threading.Thread.__init__(self)
        if f is None:
            self.f = open('/dev/midi1', 'wb+', 0) # unbuffered
        else:
            self.f = f
        self.mout = MidiOutStream(self.f)

        self.rstat=0
        self.origbytecount = 0
        self.bytecount = 0
        self.msg = ''
        self.insysex = False
        self.updated = False
        self.running = True

    def init(self):
        pass
#        while not self.updated:
#            time.sleep(0.1)
        #self.f = open('/dev/null', 'wb+', 0) #midi1', 'wb+', 0) # unbuffered
      #  self.f.write('\xB0\x7A\x00')

      #  for chan, prog in enumerate([0, 1, 4, 0x13, 0x06, 0x0B, 0x30, 0x34]):
      #      self.mout.put(PC(prog, chan))        

    def processMsg(self):
        print ' '.join(['%02X'%ord(x) for x in self.msg]),
        print '->', ' '.join(['%02X'%ord(x) for x in self.msg])
        self.f.write(self.msg)

    def run(self):
        self.init()
        while self.running:
            rx = self.f.read(1)
            if (self.insysex and rx != EOX) or rx >= SYS_RT_BASE:
                 # sysex or system realtime - ignore
                 continue
            elif rx == EOX: self.insysex = False
            elif rx == SOX: self.insysex = True
            elif rx >= SYS_COM_BASE:
                # system common - clear running status
                self.rstat = 0
            elif rx >= '\x80':
                self.rstat = rx
                self.bytecount = 2
                if '\xC0' <= rx <= '\xDF':
                     self.bytecount = 1
                self.origbytecount = self.bytecount
                self.msg = self.rstat
            else: # databyte
                if self.rstat:
                    self.msg += rx
                    self.bytecount -= 1                    
                    if self.bytecount == 0:
                        self.bytecount = self.origbytecount # reset counter for new databytes with rstat
                        self.msgbytes = map(ord, self.msg)
                        self.processMsg()
                        self.msg = self.rstat
                # otherwise no running status - ignore databyte


class FileQueue(Queue.Queue):
    def read(self, count):
        return self.get()
    def write(self, data):
        for i in data:
            self.put(i)

class MidiProc(threading.Thread):
    daemon = True
    def __init__(self, mis,mos):
        threading.Thread.__init__(self)
        self.mis = mis
        self.mos = mos
        self.__x = 0
    def run(self):
        for msg in self.mis:
            self.process(msg)
    def process(self, msg):
        import random, math
        self.__x += 0.02
        #if isinstance(msg, NoteOn) and msg.vel != 0:
        #    msg.vel = 70 + 50*math.sin(self.__x)#random.randint(30,110)
        if isinstance(msg, NoteOn):
            msglist = msg*6
            msglist[1].note -= 12
            msglist[2].note += 12
            msglist[3].note += 16
            msglist[4].note += 4
            msglist[5].note += 9
            if msg.vel != 0:
                for mm in msglist[1:]:
                    mm.vel += random.randint(-10,10)
                    mm.vel = max(1, min(mm.vel, 127))
            self.mos.put(msglist)
        else:
            self.mos.put(msg)

class MidiInStream(MidiProcess):
    def __init__(self, f):
        MidiProcess.__init__(self, f)
        self.q = Queue.Queue()
        self.start()

    def __iter__(self):
        while 1:
            yield self.q.get()
        #return self

    def processMsg(self):
        msg = self.msg
        status = ord(msg[0]) & 0xF0
        mm = None
        if status == 0x90:
            mm = NoteOn().fromstring(msg)
        elif status == 0x80:
            mm = NoteOff().fromstring(msg)
        elif status == 0xA0:
            mm = PAT().fromstring(msg)
        elif status == 0xB0:
            mm = CC().fromstring(msg)
        elif status == 0xC0:
            mm = PC().fromstring(msg)
        elif status == 0xD0:
            mm = CAT().fromstring(msg)
        elif status == 0xE0:
            mm = PB().fromstring(msg)
        if mm is not None:
            print "in:",mm
            self.q.put(mm)

    #def next(self):
    #    yield self.q.get()

if __name__ == '__main__':
    import MidiFileOutput
    mq = FileQueue()
    t = threading.Thread(target=MidiFileOutput.main, args = (mq,))
    t.daemon = True
    #t.start()
    #mis = MidiInStream(mq)
    mis = MidiInStream(file('/dev/midi1', 'rb', 0)) # mq)
    #mos = MidiOutStream(file('/dev/null', 'wb', 0))
    mos = MidiOutStream(file('/dev/midi1', 'wb', 0))
    mp = MidiProc(mis, mos)
    mp.start()

    mp.join()
