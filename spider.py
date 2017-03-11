# -*- encoding:utf-8 -*-

from HTMLParser import HTMLParser
import requests
from dbclient import *
from processmanager import *
import re
from time import sleep
import os

from dbmodel import DBWebsite, DBImage
from config import SpiderConfig as CONFIG
from config import REQUEST_STATE
	
CONN_TIME_OUT = 2 #second
 
class Spider(HTMLParser):
	def __init__(self):
		HTMLParser.__init__(self)
		self.imgs = set()
		self.hrefs = set()
		self.__feedingUrl = None

	def __adjustUrl(self, src_url):
		if src_url[-1] == '#':
			src_url = src_url[:-1]

		if not self.__feedingUrl:
			print "[Warn]Spider.adjustUrl: Not __feedingUrl"
			return src_url

		#if not (self.__feedingUrl.startswith('http://') or self.__feedingUrl.startswith("https://")):
		#	print "[Error]Spider.adjustUrl: argument from_url{%s} is not a http request url" % self.__feedingUrl
		#	return None

		if src_url.startswith('//'):
			src_url = "http:" + src_url
			return src_url

		if src_url.startswith('http://') or src_url.startswith('https://'):
			return src_url

		if src_url.startswith('javascript:'):
			return src_url

		elems = src_url.split('/')
		feeding = self.__feedingUrl.split('/')

		for e in elems:
			if e == '.':
				elems.remove(e)

		while True:
			feeding.pop()
			if elems[0] != '..':
				break;
			elems.pop(0)

		url = feeding + elems
		return '/'.join(url)

	def __isValidateUrl(self, url):
		src = self.__feedingUrl.split('/')
		target = url.split('/')
		if target[0].startswith('http'):
			return src[2] == target[2]
		else:
			return False

	def handle_starttag(self, tag, attrs):
		if tag == 'img':
			attrs = dict(attrs)
			if attrs.has_key('src'):
				url = self.__adjustUrl(attrs['src'])
				print "[Info] image: %s" % url
				self.imgs.add(url)

		if tag == 'input':
			attrs = dict(attrs)
			if attrs.has_key('type') and attrs['type'] == 'image' and attrs.has_key('src'):
				url = self.__adjustUrl(attrs['src'])
				print "[Info] image: %s" % url
				self.imgs.add(url)

		if tag == 'a':
			attrs = dict(attrs)
			if attrs.has_key('href'):
				url = self.__adjustUrl(attrs['href'])
				if self.__isValidateUrl(url):
					print "[Info] link: %s" % url
					self.hrefs.add(url)

	def __getHtmlEncode(self, text, default = 'unicode'):
		reg = re.compile("<meta.*?charset=([^\s\"'/>;]+)")
		res = reg.search(text)
		if res and res.group(1):
			if res.group(1).startswith('gb'):
				return 'gbk'
		return default

	def fetchForUrl(self, url):
		ret = False
		self.__feedingUrl = url
		try:
			print "[Info] Requesting url {%s}" % url
			resp = requests.get(url, timeout = CONN_TIME_OUT)
			if resp.status_code == 200:
				self.__feedingUrl = url
				resp.encoding = self.__getHtmlEncode(resp.text)
				#print '[Debug]Using encoding{%s} for HTML {%s}' % (resp.encoding, url)
				#print resp.text
				self.hrefs.add(url)
				self.feed(resp.text)
				self.hrefs.remove(url)
				ret = True
			else:
				print "[Warn] '%s' address can't be reached!"			

		except requests.exceptions.ConnectionError as err:
			print "[Warn] Connect to %s failed: Exception%s" % (url, str(err),)
		except requests.exceptions.ReadTimeout as ex:
			print "[Warn] Connect to %s time out" % url
		finally:
			self.__feedingUrl = None

		return ret

def fetchWebsite():
	addr = (CONFIG.DB_HOST, CONFIG.RPC_PORT)
	websites = []
	try:
		client = get_client(addr)
		client.send(CONFIG.FETCH_WEBSITE)
		result = client.recv()
		if result == CONFIG.ACTION_FAILED:
			print "[Warn] Get validate website failed"
		else:
			websites = client.recv()
		client.close()
	except EOFError:
		print "[Warn] Server has been closed"
	except Exception as e:
		print "[Error] FetchWebsite raise exceptions: %s" % str(e)

	return websites

def updateWebsiteStates(websites):
	print "[Info] Updating websites ..."
	addr = (CONFIG.DB_HOST, CONFIG.RPC_PORT)
	try:
		client = get_client(addr)
		if websites and len(websites) > 0:
			client.send(CONFIG.UPDATE_WESITE_STATE)
			client.send(websites)
			if client.recv() == CONFIG.ACTION_FAILED:
				print "[Error] tell server to update website state failed!"
			print "[Info] Updating websites done!"
		client.close()
	except EOFError:
		print "[Warn] Server has been closed"

def uploadWesites(websites):
	print "[Info] Uploading websites(%d) ..." % len(websites)
	addr = (CONFIG.DB_HOST, CONFIG.RPC_PORT)
	try:
		client = get_client(addr)
		client.send(CONFIG.UPLOAD_WEBSITE)
		client.send(websites)
		if client.recv() == CONFIG.ACTION_FAILED:
			print "[Error] upload fetched websites failed!"
		print "[Info] Upload websites done!"
		client.close()
	except EOFError:
		print "[Warn] Server has been closed"

def uploadImages(images):
	print "[Info] Uploading images(%d) ..." % len(images)
	addr = (CONFIG.DB_HOST, CONFIG.RPC_PORT)
	try:
		client = get_client(addr)
		client.send(CONFIG.UPLOAD_IMAGE)
		client.send(images)
		if client.recv() == CONFIG.ACTION_FAILED:
			print "[Error] Upload fetched images failed!"
		print "[Info] Upload images done!"
		client.close()
	except EOFError:
		print "[Warn] Server has been closed"

def procMain(pid, states):
	states[pid] = STATE_IDLE

	while True:
		states[pid] = STATE_CONNECTING
		print "[Info] Fetching unvisited websites ..."
		websites = fetchWebsite()
		print "[Info] Fetched websites(%d)" % len(websites)
		if websites:
			states[pid] = STATE_BUSY
			spider = Spider()
			wbs = set()
			images = set()
			for web in websites:
				if spider.fetchForUrl(web.url):
					web.request_state = REQUEST_STATE.SUCC
					for url in spider.hrefs:
						wbs.add(DBWebsite(url = url, from_url = web.id))
					for img in spider.imgs:
						images.add(DBImage(url = img, from_website = web.id))
				else:
					web.request_state = REQUEST_STATE.FAIL
					print "[Debug] Fetch url{%d: %s} failed!" % (web.id, web.url)
			
			updateWebsiteStates(websites)
			uploadWesites(wbs)
			uploadImages(images)
		else:
			sleep(3) # sleep for a while to wait for the database update

	states[pid] = STATE_TERMINATE

if __name__ == '__main__':
	#procMain(1, {})
	
	num = 1
	if len(os.sys.argv) > 1:
		num = int(os.sys.argv[1])
		if num < 1:
			num = 1

	pm = ProcessManager(procMain, maxWorker = num)
	pm.run()
