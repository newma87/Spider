#-*- encoding:utf-8 -*-

from multiprocessing import Process, Manager

STATE_READY = 0x01
STATE_IDLE = 0x02
STATE_CONNECTING = 0x03
STATE_BUSY = 0x04
STATE_UPLOADING = 0x05
STATE_TERMINATE = 0x06

STRING_STATE = ['null', 'ready', 'idle', 'connecting', 'busy', 'uploading', 'terminate']

class ProcessManager(object):
	CMD_PROMP = "Please input command: \n"

	def __init__(self, worker, maxWorker = 1):
		self.worker = worker
		self.maxProc = maxWorker
		self.manager = Manager()
		self.processes = {}
		self.procStates = self.manager.dict()

	def setupAll(self):
		index = 0
		while (index < self.maxProc):
			index += 1
			self.setupProccesse(index)

	def setupProccesse(self, index):
		proc = Process(target = self.worker, args = (index, self.procStates))
		self.processes[index] = proc
		self.procStates[index] = STATE_READY

	def startAll(self):
		for i, _ in self.processes.iteritems():
			self.startProcess(i)

	def startProcess(self, index):
		if self.procStates[index] != STATE_READY:
			print "[Warn]processe{%d} is not ready, please call setupProccesse() before" % index			
			return False
		self.processes[index].start()
		return True

	def terminateProcess(self, index):
		if self.procStates[index] == STATE_TERMINATE:
			print "[Warn]processe{%d} has been terminated!" % index
			return False

		self.processes[index].terminate()
		self.procStates[index] = STATE_TERMINATE
		return True

	def terminateAll(self):
		for pid, _ in self.processes.iteritems():
			if self.procStates[pid] > STATE_READY:
				self.terminateProcess(pid)

	def showState(self):
		print "# pIndex\tpState\n"
		for pid, state in self.procStates.items():
			print "  %d\t%s" % (pid, STRING_STATE[state])

	def help(self):
		print """
Manage multiprocess spider, use below command(press key before the command):
    "s, start [pNo.]":   start all process. If pNo. is sepcified, then terminate the responsed process
    "r, restart [pNo.]": restart all. If pNo. is sepcified, then terminate the responsed process
    "t, stop [pNo.]":    terminate all. If pNo. is sepcified, then terminate the responsed process
    "i, state":   show all process state
    "e, exit":    exit this application
    "h, help":    print this text

"""
	def run(self, *args, **kwargs):
		print self.maxProc
		self.setupAll()

		self.help()
		self.showState()
		cmd = ""
		while True:
			cmd = raw_input(ProcessManager.CMD_PROMP)

			if cmd == 'e':
				break
			elif cmd == "i":
				print "Show all process state:"
				self.showState()
			elif cmd.startswith("s"):
				arr = cmd.split(' ')
				if len(arr) > 1:
					print "Start processes[%d]" % int(arr[1])
					self.startProcess(int(arr[1]))
				else:
					print "Start all processes"
					self.startAll()
			elif cmd.startswith("t"):
				arr = cmd.split(' ')
				if len(arr) > 1:
					print "Terminate processes[%d]" % int(arr[1])
					self.terminateProcess(int(arr[1]))
					self.setupProccesse(int(arr[1]))
				else:
					print "Terminate all processes"
					self.terminateAll()
					self.setupAll()
			elif cmd.startswith("r"):
				arr = cmd.split(' ')
				if len(arr) > 1:
					print "Restart processes[%d]" % int(arr[1])
					self.terminateProcess(int(arr[1]))
					self.setupProccesse(int(arr[1]))
					self.startProcess(int(arr[1]))
				else:
					print "Restart all processes"
					self.terminateAll()
					self.setupAll()
					self.startAll()
			elif cmd == "raw":
				print self.processes
				print self.procStates
			elif cmd == "h":
				self.help()

		self.terminateAll()

if __name__ == '__main__':

	def worker(pid, states):
		from time import sleep
		states[pid] = STATE_IDLE
		sleep(3)
		states[pid] = STATE_BUSY
		sleep(30)
		states[pid] = STATE_TERMINATE

	spm = ProcessManager(worker)
	spm.run()
