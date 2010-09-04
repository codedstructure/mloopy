import sys
import heapq
import threading
import time
import Queue

#scheduler = sched.scheduler(time.time, time.sleep)
#end = scheduler.enterabs(time.time() + 24*3600, None, None, ())
# Start a thread to run the events
#t = threading.Thread(target=scheduler.run)
#t.start()


#todo: use a weakref in the sched, and do a cancel on __del__...?

class Event(object):

    time = 0
    priority = 1
    func = None
    repeat = None
    args = ()
    def __init__(self, **k):
        self.__dict__.update(k)

    def __le__(self, other):
        if self.time == other.time: # unlikely, but...
            return self.priority <= other.priority
        return self.time <= other.time

    def __repr__(self):
        return "event:%x@%.2f"%(id(self),self.time)

class Scheduler(object):

    def __init__(self, *o, **k):
        self.schedheap = []
        self.schedqueue = Queue.Queue()
        self.running = True
        self._thread = threading.Thread(target = self.sched)
        self._thread.setDaemon(True)
        self._thread.start()

    def join(self):
        self._thread.join()

    def sched(self):
        loop_count = 0
        self.timeout = None
        while self.running:
            if self.schedheap:
                event = self.schedheap[0]
                now = time.time()
                if now >= event.time:
                    event = self.do_event(event) or event
                self.timeout = max(0, event.time - now)
            try:
                item = self.schedqueue.get(timeout=self.timeout)
            except Queue.Empty:
                pass
            else:
                heapq.heappush(self.schedheap, item)

    def do_event(self, event):
        if event.func is not None:
            event.func(*event.args)

        if event.repeat is not None:
            self.schedheap[0].time += self.schedheap[0].repeat
            heapq.heapify(self.schedheap)
            return self.schedheap[0]
        else:
            heapq.heappop(self.schedheap)

    def enterabs(self, t, p, f, args, r=None):
        item = Event(time=t, priority=p, func=f, args=args, repeat=r)
        self.schedqueue.put(item)
        return item

    def enter(self, delay, priority, f, args, r=None):
        return self.enterabs(time.time() + delay, priority, f, args, r)

    def endin(self, delay):
        def _(): self.running=False
        return self.enter(delay, 0, _, ())

    def cancel(self, item):
        item.repeat = None
        item.func = None

class LoopSched(object):
    def __init__(self, length = 16, bpm = 120):
        self.bpm = bpm
        self.length = length
        self.active_schedheap = []
        self.next_schedheap = []
        self.schedqueue = Queue.Queue()
        self.running = True
        self._thread = threading.Thread(target = self.sched)
        self._thread.setDaemon(True)
        self._thread.start()

    def set_bpm(self, bpm):
        self.bps = bpm/60.0
    def get_bpm(self):
        return self.bps*60.0
    bpm = property(get_bpm, set_bpm)

    def instant(self):
        x = (time.time()*self.bps) % self.length
        #print x
        return x

    def join(self):
        self._thread.join()

    def sched(self):
        loop_count = 0
        self.timeout = 1
        prev_now = -1
        while self.running:
            now = self.instant()
            if self.active_schedheap:
                event = self.active_schedheap[0]            
                if now >= event.time:
                    self.do_event(event)
                
            if now <= prev_now:
                self.active_schedheap, self.next_schedheap = self.next_schedheap, []
            try:
                item = self.schedqueue.get(timeout=self.timeout)
            except Queue.Empty:
                pass
            else:
                heapq.heappush(self.next_schedheap, item)
            time.sleep(0.001)
            prev_now = now
    def do_event(self, event):
        if event.func is not None:
            event.func(*event.args)

        self.schedqueue.put(heapq.heappop(self.active_schedheap))

    def enterabs(self, t, p, f, args, r=None):
        item = Event(time=t, priority=p, func=f, args=args, repeat=r)
        self.schedqueue.put(item)
        return item

    def enter(self, delay, priority, f, args, r=None):
        return self.enterabs(time.time() + delay, priority, f, args, r)

    def endin(self, delay):
        def _(): self.running=False
        return self.enter(delay, 0, _, ())

    def cancel(self, item):
        item.repeat = None
        item.func = None


scheduler = LoopSched()

def at(t, f, args):
    return scheduler.enterabs(t, 1, f, args)

def then(t, f, args):
    return scheduler.enterabs(t, 1, f, args)

def repeat(prf, f, args=(), predelay = 0):
    return scheduler.enter(predelay, 2, f, args, r=prf)

def cancel(item):
    scheduler.cancel(item)

from midiproc import *

def setup():
    global mos
    mos = MidiOutStream(file('/dev/midi1', 'wb', 0))

setup()

def repnote(t, n, p=0):
    def _():
        try:
            for nn in n:
                mos.put(NoteOn(nn))
        except TypeError:
            mos.put(NoteOn(n))
    return repeat(t, _, (), p)

def noteat(t, n):
    return then(t, mos.put, (NoteOn(n),))

def notein(d, n):
    return noteat(time.time()+d, n)

if __name__ == '__main__':

    setup()

#    repeat(0.05, note, (60,))
    repnote(2, 64)
    #repeat(0.3333333333, note, (75,))
    repnote(1, 45)
    #repeat(0.25, note, (50,))
    repnote(5, 76)
    repnote(5, 80, 0.2)

    time.sleep(20)
