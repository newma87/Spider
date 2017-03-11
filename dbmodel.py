#-*- encoding:utf-8 -*-
import hashlib
import pickle

def hashUrl(url):
	h = hashlib.sha1()
	h.update(url.encode('utf-8'))
	return h.hexdigest()

class DBImage(object):
	def __init__(self, id = -1, url = "", request_state = 0, save_path = "", from_website = 0, dict = None):
		self.last_modify = None

		if dict != None:
			self.__dict__.update(dict)
			return

		self.id = id
		self.url = url
		self.request_state = request_state
		if self.url != "":
			self.name = hashUrl(self.url)
		else:
			self.name = ""
		self.save_path = save_path
		self.from_website = from_website

	def __getstate__(self):
		obj = self.__dict__.copy()
		del obj['name']
		return obj

	def __setstate__(self, dict):
		if dict['url'] != "":
			dict['name'] = hashUrl(dict['url'])
		else:
			dict['name'] = ""
		self.__dict__.update(dict)

	def  __hash__(self):
		return hash(self.url.encode('utf-8'))

	def __str__(self):
		return "{ id:%d, url:%s, request_state:%d, name:%s, save_path:%s, from_website:%s, last_modify:%s }" % (self.id, self.url, self.request_state, self.name, self.save_path, str(self.from_website), str(self.last_modify))

class DBWebsite(object):
	def __init__(self, id = -1	, url = "", request_state = 0, from_url = 0, dict = None):
		self.last_modify = None
		if dict != None:
			self.__dict__.update(dict)
			return

		self.id = id
		self.url = url
		self.request_state = request_state
		self.from_url = from_url

	def __getstate__(self):
		obj = self.__dict__.copy()
		return obj

	def __setstate__(self, dict):
		self.__dict__.update(dict)

	def  __hash__(self):
		return hash(self.url.encode('utf-8'))

	def __str__(self):
		return "{ id:%d, url:%s, request_state:%d, from_url:%s, last_modify:%s }" % (self.id, self.url, self.request_state, str(self.from_url), str(self.last_modify))

class Socket4Pickle(object):
	def __init__(self, socket):
		self.__socket = socket

	def recv(self):
		fobj = self.__socket.makefile('rb')
   		obj = pickle.load(fobj)
   		fobj.close()
		return obj

	def send(self, obj):
		fobj = self.__socket.makefile('wb')
   		pickle.dump(obj, fobj, pickle.HIGHEST_PROTOCOL)
   		fobj.close()

   	def close(self):
   		self.__socket.close()
