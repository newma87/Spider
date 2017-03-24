#-*- encoding: utf8 -*-

from Queue import Queue
from threading import Thread
from threading import Lock
from config import Log

class Task(object):
	def __init__(self):
		self.callback = None
		self.param = None
		self.done = False
		self.value = False

class Worker(object):
	"""docstring for Worker"""
	THREAD_IDEL_TIME = 60 # seconds
	def __init__(self, threadpool):
		super(Worker, self).__init__()
		self.isTerminate = False
		self.__thread = Thread(target = self.run)
		self.__threadpool = threadpool
		self.__threadpool.addThread(self)
		self.__thread.start()

	def forceTerminate(self):
		if self.__thread is not None:
			self.isTerminate = True
			self.__thread.join()
			self.__thread = None

	def run(self):
		while not self.isTerminate:
			try:				
				task = self.__threadpool.tasks.get(block = True, timeout = Worker.THREAD_IDEL_TIME)
			except Exception as e:
				#print "[Debug]None task founded, worker done"
				break;

			task.value = task.callback(*task.param)
			task.done = True
			if self.__threadpool.returns is not None:
				self.__threadpool.returns.put(task)
			#print "[Debug]Task done!"

		self.isTerminate = True
		self.__thread = None
		self.__threadpool.removeThread(self)
		Log.d("{Worker.run} work thread terminated!")

class ThreadPool(object):

	def __init__(self, maxsize = 1):
		self.maxCount = maxsize
		self.tasks = Queue()
		self.returns = Queue()
		self.threads = []
		self.lockObj = Lock()

	def addThread(self, thread):
		self.lockObj.acquire()
		self.threads.append(thread)
		self.lockObj.release()
		Log.d("{Worker.addThread} pool thread count(%d)", len(self.threads))

	def removeThread(self, thread):
		self.lockObj.acquire()
		self.threads.remove(thread)
		self.lockObj.release()
		Log.d("{Worker.removeThread} pool thread count(%d)", len(self.threads))

	def runTaskAsync(self, task = None, callback = None, params = []):
		if task is None:
			task = Task()
			task.callback = callback
			task.param = params

		self.tasks.put(task)
		if len(self.threads) < self.maxCount: # create thread until match max count
			worker = Worker(self)

	def forceTerminateAll(self):
		self.lockObj.acquire
		for th in self.threads:
			th.isTerminate = True  # Should not use forceTerminate(), or it will dead lock!!! 
		self.lockObj.release()
