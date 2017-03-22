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

WEBSITE_INSERT = "INSERT IGNORE INTO website (url, request_state, from_url, priority) VALUES (%s, %s, %s, %s);"
WEBSITE_DELETE_BY_ID = "DELETE from website where id=%s;"
WEBSITE_UPDATE_BY_ID = "UPDATE website SET url=%s, request_state=%s, from_url=%s, priority=%s WHERE id=%s;"
WEBSITE_UPDATE_MUTIL = "INSERT INTO website (url, request_state, from_url, priority, id) VALUES (%s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE id=VALUES(id), url=VALUES(url), request_state=VALUES(request_state), from_url=VALUES(from_url), priority=VALUES(priority);"
WEBSITE_SELECT_BY_ID = "SELECT * FROM website WHERE id=%s ORDER BY priority DESC;"
WEBSITE_SELECT_BY_URL = "SELECT * FROM website WHERE url=%s ORDER BY priority DESC;"
WEBSITE_SELECT_BY_STATE = "SELECT * FROM website WHERE request_state=%s ORDER BY priority DESC;"
WEBSITE_UPDATE_STATE = "UPDATE website SET request_state=0 WHERE request_state=1 AND NOW() > DATE_ADD(last_modify, INTERVAL '%s' MINUTE);" % (REFRESH_STATE_INTERVAL)

IMAGE_INSERT = "INSERT IGNORE INTO image (url, request_state, name, save_path, from_website) VALUES (%s, %s, %s, %s, %s);"
IMAGE_DELETE_BY_ID = "DELETE from image where id=%s;"
IMAGE_UPDATE_BY_ID = "UPDATE image SET url=%s, request_state=%s, name=%s, save_path=%s, from_website=%s WHERE id=%s;"
IMAGE_UPDATE_MUTIL = "INSERT INTO image (url, request_state, name, save_path, from_website, id) VALUES (%s, %s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE id=VALUES(id), url=VALUES(url), request_state=VALUES(request_state), from_website=VALUES(from_website), name=VALUES(name), save_path=VALUES(save_path);"
IMAGE_SELECT_BY_ID = "SELECT * FROM image WHERE id=%s;"
IMAGE_SELECT_BY_URL = "SELECT * FROM image WHERE url=%s;"
IMAGE_SELECT_BY_STATE = "SELECT * FROM image WHERE request_state=%s;"
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
		#print "[Info]Listen on address: ", addr
		s.bind(addr)
		s.listen(1)
	else:
		s = Listener(addr, authkey = CONFIG.AUTH_KEY)
	return s

class DBOperator(object):
	def __init__(self):
		pass
		#self.conn = Mysql()

	def __enter__(self):
		self.conn = Mysql()
		return self

#====================image=======================================
	def refreshImagesState(self):
		return self.conn.update(IMAGE_UPDATE_STATE)

	def insertImage(self, image):
		image.id = self.conn.insertOne(IMAGE_INSERT, (D(image.url), D(image.request_state), D(image.name), D(image.save_path), D(image.from_website)))
		return image

	def insertMutilImage(self, images):
		vals = [(D(image.url), D(image.request_state), D(image.name), D(image.save_path), D(image.from_website)) for image in images]
		count = self.conn.insertMany(IMAGE_INSERT, vals)
		return count

	def updateMutilImage(self, images):
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
			images = []
			for row in rows:
				images.append(DBImage(dict = row))
			return images
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
			websites = []
			for row in rows:
				websites.append(DBWebsite(dict = row))
			return websites
		else:
			return None

	def insertWebsite(self, website):
		ret = self.conn.insertOne(WEBSITE_INSERT, (D(website.url), D(website.request_state), D(website.from_url), D(website.priority)))
		if ret > 0:
			website.id = ret
			return self.getWebsiteById(website.id)
		else:
			return False

	def insertMutilWebsite(self, websites):
		vals = [(D(web.url), D(web.request_state), D(web.from_url), D(web.priority)) for web in websites]
		count = self.conn.insertMany(WEBSITE_INSERT, vals)
		return count

	def updateWebsite(self, website):
		count = self.conn.update(WEBSITE_UPDATE_BY_ID, (D(website.url), D(website.request_state), D(website.from_url), D(website.priority), D(website.id)))
		return count

	def deleteWebsiteById(self, id):
		count = self.conn.delete(WEBSITE_DELETE_BY_ID, (D(id), ))
		return count

	def updateMutilWebsite(self, websites):
		vals = [(D(web.url), D(web.request_state), D(web.from_url), D(web.priority), D(web.id)) for web in websites]
		count = self.conn.insertMany(WEBSITE_UPDATE_MUTIL, vals)
		return count / 2

	def end(self, ok = True):
		self.conn.end(ok)

	def __exit__(self, type, value, traceback):
		self.conn.close()
		self.conn = None

class DBServer(object):

	__MAX_CONNECT_QUEUE__ = 1000

	def __init__(self, port = CONFIG.RPC_PORT):
		self.address = (CONFIG.HOST, port)
		self.isTerminal = False
		self.__pool = ThreadPool(maxsize = 4)

	def run(self):
		print "[Info]DBServer started!"
		self.isTerminal = False
		server = get_server(self.address, means = 'Socket')

		while not self.isTerminal:
			conn = server.accept()
			if type(conn) is tuple: # server must be a socket, not a multiprocessing.connection.Listener
				conn = Socket4Pickle(conn[0])
			self.__pool.runTaskAsync(callback = self.handleConnection, params = [conn])

		self.isTerminal = True
		server.close()
		print "[Info]DBserver close!"

	def queryValidateWebsites(self):
		with DBOperator() as db:
			websites = db.getWebsiteByState(REQUEST_STATE.NONE, maxNum = CONFIG.MAX_FETCH_NUM)
			if websites:
				flag = True
				for web in websites:
					web.request_state = REQUEST_STATE.DOING
					if db.updateWebsite(web) == 0:
						print "[Error]DBServer.queryValidateWebsite: update website[%d] state to 1 failed" % (web.id)
						flag = False
						break
				db.end(flag)
				if flag:
					return websites
			else:
				print "[Warn]DBServer.queryValidateWebsite: Can't found unvisited website, so refresh request_state"
				db.refreshWebsitesState()
		return None

	def uploadWebsites(self, websites):
		ret = True
		with DBOperator() as db:
			count = db.insertMutilWebsite(websites)
			print "[Info] Inserted web urls count{%d}" % count

		return ret

	def updateAllWebsites(self, websites):
		ret = True
		with DBOperator() as db:
			count = db.updateMutilWebsite(websites)
			print "[Info] Updated websites count{%d}" % count

		return ret

	def queryValidateImages(self):
		with DBOperator() as db:
			images = db.getImageByState(REQUEST_STATE.NONE, maxNum = CONFIG.MAX_FETCH_NUM)
			if images:
				flag = True
				for img in images:
					img.request_state = REQUEST_STATE.DOING
					if db.updateImage(img) == 0:
						print "[Error]DBServer.queryValidateImage: update image[%d] state to 1 failed" % (img.id)
						flag = False
						break
				db.end(flag)
				if flag:
					return images
			else:
				print "[Warn]DBServer.queryValidateImage: Can't found undownload image, so refresh the request_state"
				db.refreshImagesState()
		return None	

	def uploadImages(self, images):
		ret = True
		with DBOperator() as db:
			count = db.insertMutilImage(images)
			print "[Info] Inserted image urls count{%d}" % count

		return ret
				
	def updateAllImages(self, images):
		ret = True
		with DBOperator() as db:
			count = db.updateMutilImage(images)
			print "[Info] Updated images count{%d}" % count
		return ret

	def handleConnection(self, conn):
		try:
			data = conn.recv()
			if data == CONFIG.FETCH_WEBSITE:
				print "[Info] Fetching unvisited websites ..."
				websites = self.queryValidateWebsites()
				if websites:
					conn.send(CONFIG.ACTION_SUCCESS)
					conn.send(websites)
					print "[Info] Fetched websites(%d)" % len(websites)
				else:
					conn.send(CONFIG.ACTION_FAILED)
					print "[Info] Fetched websites failed!"
			
			elif data == CONFIG.UPDATE_WESITE_STATE:
				websites = conn.recv()
				print "[Info] Updating websites's states(%d) ..." % len(websites)
				if self.updateAllWebsites(websites):
					conn.send(CONFIG.ACTION_SUCCESS)
					print "[Info] Updated websites!"
				else:
					conn.send(CONFIG.ACTION_FAILED)
					print "[Info] Updated websites's states failed!"
			elif data == CONFIG.UPLOAD_WEBSITE:
				websites = conn.recv()
				print "[Info] Uploading websites(%d) ..." % len(websites)
				if self.uploadWebsites(websites):
					print "[Info] Uploaded websites"
					conn.send(CONFIG.ACTION_SUCCESS)
				else:
					print "[Info] Uploaded websites failed!"
					conn.send(CONFIG.ACTION_FAILED)
			elif data == CONFIG.UPLOAD_IMAGE:
				images = conn.recv()
				print "[Info] Uploading images(%d) ..." % len(images)
				if self.uploadImages(images):
					conn.send(CONFIG.ACTION_SUCCESS)
					print "[Info] Uploaded images"
				else:
					conn.send(CONFIG.ACTION_FAILED)	
					print "[Info] Uploaded images failed"
			elif data == CONFIG.FETCH_IMAGE:
				print "[Info] Fetching undownload images ..."
				images = self.queryValidateImages()
				if images:
					conn.send(CONFIG.ACTION_SUCCESS)
					conn.send(images)
					print "[Info] Fetched images(%d)" % len(images)
				else:
					conn.send(CONFIG.ACTION_FAILED)
					print "[Info] Fetched images failed!"
			elif data == CONFIG.UPDATE_IMAGE_STATE:
				images = conn.recv()
				print "[Info] Updating images's state(%d) ..." % len(images)  
				if self.updateAllImages(images):
					conn.send(CONFIG.ACTION_SUCCESS)
					print "[Info] Updated images's state"
				else:
					conn.send(CONFIG.ACTION_FAILED)
					print "[Info] Updated images's state failed!"
		
		except EOFError : #client has been closed
			print "[Warn]handleConnection: Client closed the connection"
		#except Exception as e:
		#	print "[Error]handleConnection: Raise Exception%s {%s}" % (type(e), str(e))

		conn.close()


def procMain(pid, states):
	server = DBServer()
	states[pid] = STATE_BUSY
	server.run()
	states[pid] = STATE_TERMINATE

if __name__ == '__main__':
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
