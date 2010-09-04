import os, threading, time
from midiproc import MidiProcess

class CrossFade(MidiProcess):

    def processMsg(self):
        print ' '.join(['%02X'%x for x in self.msg]),
        if 0x80 <= self.msg[0] <= 0x9F:
            self.msg = self.msg *2
            self.msg[3] += 6 # next channel
            if self.msg[2] > 0:
                self.msg[5] = 0x80 - self.msg[2]
        if self.msg[0:2] == [0xB0, 0x40]: # sustain pedal
            self.msg = self.msg * 8
            for i in range(8):
                self.msg[i*3] |= i
        print '->', ' '.join(['%02X'%x for x in self.msg])
        self.f.write(''.join([chr(x) for x in self.msg]))

mp = CrossFade()
mp.start()

try:
    while 1: time.sleep(1)
except:
    mp.running = False
