# -*- coding: UTF-8 -*-

from dbhelper import Mysql

from multiprocessing.connection import Listener
import socket
from threading import Thread
from Queue import Queue
from config import DBServerConfig as CONFIG
from config import *
from threadpool import *
from dbmodel import *
import datetime
import os
import re

from processmanager import *

WEBSITE_INSERT = "INSERT IGNORE INTO website (url, title, request_state, from_url, priority) VALUES (%s, %s, %s, %s, %s);"
WEBSITE_DELETE_BY_ID = "DELETE from website where id=%s;"
WEBSITE_UPDATE_BY_ID = "UPDATE website SET url=%s, title = %s, request_state=%s, from_url=%s, priority=%s WHERE id=%s;"
WEBSITE_UPDATE_MUTIL = "INSERT INTO website (url, title, request_state, from_url, priority, id) VALUES (%s, %s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE id=VALUES(id), url=VALUES(url), title = VALUES(title), request_state=VALUES(request_state), from_url=VALUES(from_url), priority=VALUES(priority);"
WEBSITE_SELECT_BY_ID = "SELECT * FROM website WHERE id=%s ORDER BY priority DESC;"
WEBSITE_SELECT_BY_URL = "SELECT * FROM website WHERE url=%s ORDER BY priority DESC;"
WEBSITE_SELECT_BY_STATE = "SELECT * FROM website WHERE request_state=%s ORDER BY priority DESC FOR UPDATE;"
WEBSITE_UPDATE_STATE = "UPDATE website SET request_state=0 WHERE request_state=1 AND NOW() > DATE_ADD(last_modify, INTERVAL '%s' MINUTE);" % (REFRESH_STATE_INTERVAL)

IMAGE_INSERT = "INSERT IGNORE INTO image (url, request_state, name, save_path, from_website) VALUES (%s, %s, %s, %s, %s);"
IMAGE_DELETE_BY_ID = "DELETE from image where id=%s;"
IMAGE_UPDATE_BY_ID = "UPDATE image SET url=%s, request_state=%s, name=%s, save_path=%s, from_website=%s WHERE id=%s;"
IMAGE_UPDATE_MUTIL = "INSERT INTO image (url, request_state, name, save_path, from_website, id) VALUES (%s, %s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE id=VALUES(id), url=VALUES(url), request_state=VALUES(request_state), from_website=VALUES(from_website), name=VALUES(name), save_path=VALUES(save_path);"
IMAGE_SELECT_BY_ID = "SELECT * FROM image WHERE id=%s;"
IMAGE_SELECT_BY_URL = "SELECT * FROM image WHERE url=%s;"
IMAGE_SELECT_BY_STATE = "SELECT * FROM image WHERE request_state=%s FOR UPDATE;"
IMAGE_UPDATE_STATE = "UPDATE image SET request_state=0 WHERE request_state=1 AND NOW() > DATE_ADD(last_modify, INTERVAL '%s' MINUTE);" % (REFRESH_STATE_INTERVAL)

def D(value):
	if type(value) is not str:
		if type(value) == unicode:
			return value.encode('utf-8')
		else:
			return str(value)
	else:
		return value

def get_server(addr, means = 'socket'):
	if means.lower() == 'socket':
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		Log.d("{get_server} server listen on address (%s)", addr)
		s.bind(addr)
		s.listen(1)
	else:
		s = Listener(addr, authkey = CONFIG.AUTH_KEY)
	return s

class DBOperator(object):

	def __enter__(self):
		self.conn = Mysql()
		self.conn.autocommit(False)
		self.__needRollback = False
		return self

	def rollback(self):
		self.__needRollback = True

#====================image=======================================
	def refreshImagesState(self):
		return self.conn.update(IMAGE_UPDATE_STATE)

	def insertImage(self, image):
		image.id = self.conn.insertOne(IMAGE_INSERT, (D(image.url), D(image.request_state), D(image.name), D(image.save_path), D(image.from_website)))
		return image

	def insertMutilImage(self, images):
		if not images or len(images) == 0:
			return 0

		vals = [(D(image.url), D(image.request_state), D(image.name), D(image.save_path), D(image.from_website)) for image in images]
		count = self.conn.insertMany(IMAGE_INSERT, vals)
		return count

	def updateMutilImage(self, images):
		if not images or len(images) == 0:
			return 0
		vals = [(D(image.url), D(image.request_state), D(image.name), D(image.save_path), D(image.from_website), D(image.id)) for image in images]
		count = self.conn.insertMany(IMAGE_UPDATE_MUTIL, vals)
		return count / 2
	
	def updateImage(self, image):
		count = self.conn.update(IMAGE_UPDATE_BY_ID, (D(image.url), D(image.request_state), D(image.name), D(image.save_path), D(image.from_website), D(image.id)))
		return count

	def deleteImageById(self, id):
		count = self.conn.delete(IMAGE_DELETE_BY_ID, (D(id), ))
		return count

	def getImageById(self, id):
		obj = self.conn.getOne(IMAGE_SELECT_BY_ID, (D(id), ))
		if obj:
			return DBImage(dict = obj)
		else:
			return None

	def getImageByUrl(self, url):
		obj = self.conn.getOne(IMAGE_SELECT_BY_URL, (D(url), ))
		if obj:
			return DBImage(dict = obj)
		else:
			return None

	def getImageByState(self, value = 0, maxNum = 20):
		rows = self.conn.getMany(IMAGE_SELECT_BY_STATE, maxNum, (D(value), ))
		if rows:	
			return [DBImage(dict = row) for row in rows]
		else:
			return None

	#=================website=======================
	def refreshWebsitesState(self):
		return self.conn.update(WEBSITE_UPDATE_STATE)

	def getWebsiteByUrl(self, url):
		obj = self.conn.getOne(WEBSITE_SELECT_BY_URL, (D(url), ))
		if obj:
			return DBWebsite(dict = obj)
		else:
			return None

	def getWebsiteById(self, id):
		obj = self.conn.getOne(WEBSITE_SELECT_BY_ID, (D(id), ))
		if obj:
			return DBWebsite(dict = obj)
		else:
			return None

	def getWebsiteByState(self, value = 0, maxNum = 20):
		rows = self.conn.getMany(WEBSITE_SELECT_BY_STATE, maxNum, (D(value), ))
		if rows:
			return [DBWebsite(dict = row) for row in rows]
		else:
			return None

	def insertWebsite(self, website):
		ret = self.conn.insertOne(WEBSITE_INSERT, (D(website.url), D(website.title), D(website.request_state), D(website.from_url), D(website.priority)))
		if ret > 0:
			website.id = ret
			return self.getWebsiteById(website.id)
		else:
			return False

	def insertMutilWebsite(self, websites):
		if not websites or len(websites) == 0:
			return 0
		vals = [(D(web.url), D(web.title), D(web.request_state), D(web.from_url), D(web.priority)) for web in websites]
		count = self.conn.insertMany(WEBSITE_INSERT, vals)
		return count

	def updateWebsite(self, website):
		if not website:
			return 0
		count = self.conn.update(WEBSITE_UPDATE_BY_ID, (D(website.url), D(website.title), D(website.request_state), D(website.from_url), D(website.priority), D(website.id)))
		return count

	def deleteWebsiteById(self, id):
		count = self.conn.delete(WEBSITE_DELETE_BY_ID, (D(id), ))
		return count

	def updateMutilWebsite(self, websites):
		if not websites or len(websites) == 0:
			return 0
		vals = [(D(web.url), D(web.title), D(web.request_state), D(web.from_url), D(web.priority), D(web.id)) for web in websites]
		count = self.conn.insertMany(WEBSITE_UPDATE_MUTIL, vals)
		return count / 2

	def __exit__(self, type, value, traceback):
		if self.__needRollback:
			self.conn.end(False)
		else:
			self.conn.end(True)
		self.conn.close()
		self.conn = None

class DBServer(object):

	__MAX_CONNECT_QUEUE__ = 1000

	def __init__(self, port = CONFIG.RPC_PORT):
		self.address = (CONFIG.HOST, port)
		self.isTerminal = False
		self.__pool = ThreadPool(maxsize = 4)

	def run(self):
		Log.i("{DBServer.run} DBServer started!")
		self.isTerminal = False
		server = get_server(self.address, means = CONFIG.COMMUNICATE_MEANS)

		try:
			while not self.isTerminal:
				conn = server.accept()
				if type(conn) is tuple: # server must be a socket, not a multiprocessing.connection.Listener
					conn = Socket4Pickle(conn[0])
				self.__pool.runTaskAsync(callback = self.handleConnection, params = [conn])
		except KeyboardInterrupt:
			Log.i("{DBServer.run} sever process terminate for a KeyboardInterrupt!")

		self.isTerminal = True
		server.close()
		Log.i("{DBServer.run} DBserver closed!")

	def queryValidateWebsites(self):
		ret = None
		with DBOperator() as db:
			websites = db.getWebsiteByState(REQUEST_STATE.NONE, maxNum = CONFIG.MAX_FETCH_NUM)
			if websites:
				for web in websites:
					web.request_state = REQUEST_STATE.DOING
				count = db.updateMutilWebsite(websites)
				if count != len(websites):
					Log.e("{DBServer.queryValidateWebsites} update unvisited websites to state 1 failed do nothing: expect(%d) - actually(%d)", len(websites), count)
					db.rollback()
				else:
					#print "[Info]DBServer.queryValidateImages: websites count[%d] set state to be visiting" % count
					ret = websites
			else:
				Log.w("{DBServer.queryValidateWebsite} can't found unvisited website, so refresh request_state")
				db.refreshWebsitesState()
		return ret

	def uploadWebsites(self, websites):
		ret = True
		with DBOperator() as db:
			count = db.insertMutilWebsite(websites)
			Log.i("{DBServer.uploadWebsites} add website urls counts(%d)", count)

		return ret

	def updateAllWebsites(self, websites):
		ret = True
		with DBOperator() as db:
			count = db.updateMutilWebsite(websites)
			Log.i("{DBServer.updateAllWebsites} updated websites counts(%d)", count)

		return ret

	def queryValidateImages(self):
		ret = None
		with DBOperator() as db:
			images = db.getImageByState(REQUEST_STATE.NONE, maxNum = CONFIG.MAX_FETCH_NUM)
			if images:
				for img in images:
					img.request_state = REQUEST_STATE.DOING
				count = db.updateMutilImage(images)
				if count != len(images):
					Log.e("{DBServer.queryValidateImages} update undownload images state to 1 failed, do nothing: expect(%d) - actually(%d)", len(images), count)
					db.rollback()
				else:
					#print "[Info]DBServer.queryValidateImage: images count[%d] set state to be visiting" % (count)
					ret = images
			else:
				Log.w("{DBServer.queryValidateImage} can't found undownload image, so refresh the request_state")
				db.refreshImagesState()
		return ret	

	def uploadImages(self, images):
		ret = True
		with DBOperator() as db:
			count = db.insertMutilImage(images)
			Log.i("{DBServer.uploadImages} add image urls count(%d)", count)

		return ret
				
	def updateAllImages(self, images):
		ret = True
		with DBOperator() as db:
			count = db.updateMutilImage(images)
			Log.i("{DBServer.updateAllImages} updated images count{%d}", count)
		return ret

	def handleConnection(self, conn):
		try:
			data = conn.recv()
			if data == CONFIG.FETCH_WEBSITE:
				Log.d("{DBServer.handleConnection} fetching unvisited websites ...")
				websites = self.queryValidateWebsites()
				if websites:
					conn.send(CONFIG.ACTION_SUCCESS)
					conn.send(websites)
					Log.i("{DBServer.handleConnection} fetched websites(%d)", len(websites))
				else:
					conn.send(CONFIG.ACTION_FAILED)
					Log.w("{DBServer.handleConnection} fetched websites failed!")
			
			elif data == CONFIG.UPDATE_WESITE_STATE:
				websites = conn.recv()
				Log.i("{DBServer.handleConnection} updating websites's(%d) states ...", len(websites))
				if self.updateAllWebsites(websites):
					conn.send(CONFIG.ACTION_SUCCESS)
					Log.d("{DBServer.handleConnection} updated websites states")
				else:
					conn.send(CONFIG.ACTION_FAILED)
					Log.w("{DBServer.handleConnection} updated websites's states failed!")
			elif data == CONFIG.UPLOAD_WEBSITE:
				websites = conn.recv()
				Log.i("{DBServer.handleConnection} uploading websites(%d) ...", len(websites))
				if self.uploadWebsites(websites):
					Log.d("{DBServer.handleConnection} uploaded websites")
					conn.send(CONFIG.ACTION_SUCCESS)
				else:
					Log.w("{DBServer.handleConnection} uploaded websites failed!")
					conn.send(CONFIG.ACTION_FAILED)
			elif data == CONFIG.UPLOAD_IMAGE:
				images = conn.recv()
				Log.i("{DBServer.handleConnection} uploading images(%d) ...", len(images))
				if self.uploadImages(images):
					conn.send(CONFIG.ACTION_SUCCESS)
					Log.d("{DBServer.handleConnection} uploaded images")
				else:
					conn.send(CONFIG.ACTION_FAILED)	
					Log.w("{DBServer.handleConnection} uploaded images failed")
			elif data == CONFIG.FETCH_IMAGE:
				Log.d("{DBServer.handleConnection} fetching undownload images ...")
				images = self.queryValidateImages()
				if images:
					conn.send(CONFIG.ACTION_SUCCESS)
					conn.send(images)
					Log.i("{DBServer.handleConnection} fetched images(%d)", len(images))
				else:
					conn.send(CONFIG.ACTION_FAILED)
					Log.w("{DBServer.handleConnection} fetched images failed!")
			elif data == CONFIG.UPDATE_IMAGE_STATE:
				images = conn.recv()
				Log.i("{DBServer.handleConnection} updating images's state(%d) ...", len(images))
				if self.updateAllImages(images):
					conn.send(CONFIG.ACTION_SUCCESS)
					Log.d("{DBServer.handleConnection} updated images's state")
				else:
					conn.send(CONFIG.ACTION_FAILED)
					Log.w("{DBServer.handleConnection} updated images's state failed!")
		
		except EOFError : #client has been closed
			Log.w("{DBServer.handleConnection} client closed the connection")
		#except Exception as e:
		#	print "[Error]handleConnection: Raise Exception%s {%s}" % (type(e), str(e))

		conn.close()


def procMain(pid, states):
	server = DBServer()
	states[pid] = STATE_BUSY
	server.run()

if __name__ == '__main__':
	Log.setup('server')

	"""
	url = raw_input("please input need to insert url: ")
	with DBOperator() as db:
		web = DBWebsite(url = url)
		print 'insert new website "%s" record result: %s' % (url, db.insertWebsite(web))
	"""
	num = 1
	if len(os.sys.argv) > 1:
		num = int(os.sys.argv[1])
		if num < 1:
			num = 1
			
	pm = ProcessManager(procMain, maxWorker = num)
	pm.run()
	

