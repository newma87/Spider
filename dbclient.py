# -*- coding: UTF-8 -*-

from multiprocessing.connection import Client
import socket
from config import CommunicateConfig as CONFIG
from config import Log
from dbmodel import Socket4Pickle

import json

def get_client(addr, means = 'socket'):
	if means.lower() == 'socket':
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		#print "[info] Connecting to host: ", addr
		s.connect(addr) 
		client = Socket4Pickle(s)
	else:
		client = Client(addr, authkey = CONFIG.AUTH_KEY)

	return client

class BlackSiteList(object):
	def __init__(self, file_path = ''):
		self.blackList = {}
		self.file_path = file_path
		self.load()

	def addFaileSite(self, site):
		if site in self.blackList.keys():
			self.blackList[site] += 1
		else:
			self.blackList[site] = 1

	def getFaileSiteCount(self, site):
		if not site in self.blackList.keys():
			return 0
		return self.blackList[site]

	def save(self, file_path = None):
		if file_path == None:
			file_path = self.file_path
		try:
			with open(file_path, 'w') as fp:
				content = json.dumps(self.blackList)
				fp.write(content)
				fp.flush()
				fp.close()
				return True
		except IOError:
			Log.w("{BlackSiteList.save} save to file (%s) failed!", self.file_path)
			return False

	def load(self):
		try:
			with open(self.file_path, 'r') as fp:
				content = fp.read()
				fp.close()
				self.blackList = json.loads(content)
				return True
		except IOError:
			Log.w("{BlackSiteList.load} load file (%s) failed!", self.file_path)
			return False
