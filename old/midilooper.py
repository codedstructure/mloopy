
mev = heap()

thread write():
  mf.write(q.get())

thread read():
  mf.read()
  offset = time.time() % 10





import os, threading, time
from Tkinter import *


class MidiProcess(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.daemon = True

        self.rstat=0
        self.origbytecount = 0
        self.bytecount = 0
        self.msg = []
        self.insysex = False
        self.updated = False
        self.running = True

    def processMsg(self):
        pass
        print ' '.join(['%02X'%x for x in self.msg]),
        print '->', ' '.join(['%02X'%x for x in self.msg])
        self.f.write(''.join([chr(x) for x in self.msg]))


    def run(self):
        while not self.updated:
            time.sleep(0.1)
        self.f = open('/dev/midi1', 'wb+', 0) # unbuffered
        self.f.write('\xB0\x7A\x00')

        self.f.write('\xC0\x00')
        self.f.write('\xC1\x01')
        self.f.write('\xC2\x04')
        self.f.write('\xC3\x13')
        self.f.write('\xC4\x06')
        self.f.write('\xC5\x0B')
        self.f.write('\xC6\x30')
        self.f.write('\xC7\x34')
        while self.running:
            rx = ord(self.f.read(1))
            if (self.insysex and rx != 0xF7) or rx >= 0xF8:
                 # sysex or system realtime - ignore
                 continue
            elif rx == 0xF7:
                # end of sysex
                self.insysex = False
            elif rx == 0xF0:
                # start of sysex
                self.insysex = True
            elif rx >= 0xF0:
                # system common - clear running status
                self.rstat = 0
            elif rx >= 0x80:
                self.rstat = rx
                self.bytecount = 2
                if 0xC0 <= rx <= 0xDF:
                     self.bytecount = 1
                self.origbytecount = self.bytecount
                self.msg = [self.rstat]
            else: # databyte
                if self.rstat:
                    self.msg.append(rx)
                    self.bytecount -= 1                    
                    if self.bytecount == 0:
                        self.bytecount = self.origbytecount # reset counter for new databytes with rstat
                        self.processMsg()
                        self.msg = []
                # otherwise no running status - ignore databyte

class MidiWriter(threading.Thread):
    def __init__(self):
      pass
    def run(self):
      nextevent = heapq.popheap(mev)

class MainWindow(Frame):
    def __init__(self,parent,mp):
        Frame.__init__(self,parent)
        self.mp = mp
        self.parent = parent
        self.grid(row=0, column=0)
        self.volume = IntVar()
        self.volume.set(64)
        self.options = [("Volume", "volume", IntVar, 64, 0, 127, 1),
                        ("VolumeMul", "volmul", DoubleVar, 1.05, 1.0, 1.2, 0.01),
                        ("VolumeSlope", "volslope", DoubleVar, 0, -1.0, 1.0, 0.05)]
        for idx, opt in enumerate(self.options):
            label = Label(self, text=opt[0])
            var = opt[2]()
            var.set(opt[3])
            setattr(self, opt[1], var)
            scale = Scale(self, variable=getattr(self,opt[1]),
                          command=self.update,
                          resolution=opt[6],from_=opt[4],to=opt[5],
                          orient=HORIZONTAL)
            label.grid(row=idx, column=0, padx=2, pady=2, sticky=E)
            scale.grid(row=idx, column=1, padx=2, pady=2, sticky=EW)

    def update(self, *ignore):
        for opt in self.options:
            setattr(self.mp, opt[1], getattr(self, opt[1]).get())
        self.mp.updated = True

mp = MidiProcess()
mp.start()

app = Tk()      
window = MainWindow(app, mp)
try:
    app.mainloop()
except:
    mp.running = False

