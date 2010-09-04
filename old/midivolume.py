import os, time
from Tkinter import *
from midiproc import *

class MidiVolume(MidiProcess):
    vellist = []

    def processMsg(self):
        print ' '.join(['%02X'%x for x in self.msgbytes]),
        if 0x80 <= self.msgbytes[0] <= 0x9F:
            # map low 16 notes to different channels
            # all on middle C
            #if self.msgbytes[1] < 0x15+16:
            #    self.msgbytes[0] |= (self.msgbytes[1] - 0x15)
            #    self.msgbytes[1] = 64 # middle C?
            # scale velocity
            if self.msgbytes[2] != 0:
                self.vellist.insert(0,self.msgbytes[2])
                self.vellist = self.vellist[0:10]
                avg = sum(self.vellist)/10.0
                print '->', ' '.join(['%02X'%x for x in [0xB0, 7, 2*int(avg)]])
                for i in range(16):
                    self.f.write(''.join([chr(x) for x in [0xB0 + i, 7, 2*int(avg)]]))
            self.msgbytes[2] **= self.volmul
            self.msgbytes[2] *= ((1+self.volslope)-self.msgbytes[1]/64.0)
            self.msgbytes[2] = max(0, min(127, self.msgbytes[2]))
        if self.msgbytes[0:2] == [0xB0, 0x40]: # sustain pedal
            self.msgbytes = self.msgbytes * 8
            for i in range(8):
                self.msgbytes[i*3] |= i
        print '->', ' '.join(['%02X'%x for x in self.msgbytes])
        self.f.write(''.join([chr(x) for x in self.msgbytes]))

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

mp = MidiVolume()
mp.start()

app = Tk()      
window = MainWindow(app, mp)
try:
    app.mainloop()
except:
    mp.running = False
