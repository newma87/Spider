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
from config import REQUEST_STATE, PROXY_CONFIG, MAX_REQUEST_RETRY_TIME, Log
	
CONN_TIME_OUT = 15 #second
 
class Spider(HTMLParser):
	def __init__(self):
		HTMLParser.__init__(self)
		self.imgs = set()
		self.hrefs = set()
		self.title = None
		self.findTitle = False
		self.canGetTitle = False
		self.__feedingUrl = None

	def __adjustUrl(self, src_url):
		if not self.__feedingUrl:
			Log.e("{Spider.__adjustUrl} self.__feedingUrl is None")
			return src_url

		if src_url == '#':
			return self.__feedingUrl

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

		if url == self.__feedingUrl:
			return False

		if not target[0].startswith('http') or src[2] != target[2]:
			return False
		
		#special task
		if ('htm_data' in target[3]) or ('index' in target[3]):
			return True

		if re.search('thread\d+\.php', url):
			return True

		return False

	def __isValidateImage(self, image_url):
		strs = image_url.split('/')
		file_name = strs[-1]
		if file_name.find('.') == -1:
			return False
		return True

	def handle_starttag(self, tag, attrs):
		if tag == 'img':
			attrs = dict(attrs)
			if attrs.has_key('src'):
				url = self.__adjustUrl(attrs['src'])
				if self.__isValidateImage(url):
					Log.d("image: %s", url)
					self.imgs.add(url)

		if tag == 'input':
			attrs = dict(attrs)
			if attrs.has_key('type') and attrs['type'] == 'image' and attrs.has_key('src'):
				url = self.__adjustUrl(attrs['src'])
				if self.__isValidateImage(url):
					Log.d("image: %s", url)
					self.imgs.add(url)

		if tag == 'a':
			attrs = dict(attrs)
			if attrs.has_key('href'):
				url = self.__adjustUrl(attrs['href'])
				if self.__isValidateUrl(url):
					Log.d("link: %s", url)
					self.hrefs.add(url)
					
		if self.title == None:
			if self.findTitle == False:
				if tag == 'div':
					attrs = dict(attrs);
					if attrs.has_key('class') and attrs['class'] == 't t2':
						self.findTitle = True;
			elif tag == 'h4':
				self.canGetTitle = True

	def handle_data(self, data):
		if self.title == None and self.findTitle == True and self.canGetTitle == True:
			self.title = data
			Log.d("title: %s", self.title);

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
			Log.d("{Spider.fetchForUrl} requesting url(%s)", url)
			rs = requests.session()
			resp = rs.get(url, timeout = CONN_TIME_OUT, proxies = PROXY_CONFIG)
			if resp.status_code == 200:
				self.__feedingUrl = url
				resp.encoding = self.__getHtmlEncode(resp.text)
				#print '[Debug]Using encoding{%s} for HTML {%s}' % (resp.encoding, url)
				#print resp.text

				self.feed(resp.text)
				ret = True
			else:
				Log.e("{Spider.fetchForUrl} address(%s) can't be reached!", url)

		except requests.exceptions.ConnectionError as err:
			Log.e("{Spider.fetchForUrl} connect to address(%s) failed, exception<%s>", url, str(err),)
		except requests.exceptions.ReadTimeout as ex:
			Log.e("{Spider.fetchForUrl} connect to address(%s) time out", url)
		finally:
			self.__feedingUrl = None

		return ret

def fetchWebsite():
	addr = (CONFIG.DB_HOST, CONFIG.RPC_PORT)
	websites = []
	try:
		client = get_client(addr, means = CONFIG.COMMUNICATE_MEANS)
		client.send(CONFIG.FETCH_WEBSITE)
		result = client.recv()
		if result == CONFIG.ACTION_FAILED:
			Log.e("{Spider.fetchWebsite} get validate website failed")
		else:
			websites = client.recv()
		client.close()
	except EOFError:
		Log.e("{Spider.fetchWebsite} server has been closed")
	except Exception as e:
		Log.e("{Spider.fetchWebsite} raise exceptions<%s>", str(e))

	return websites

def updateWebsiteStates(websites):
	Log.d("{updateWebsiteStates} updating websites ...")
	addr = (CONFIG.DB_HOST, CONFIG.RPC_PORT)
	try:
		client = get_client(addr)
		if websites and len(websites) > 0:
			client.send(CONFIG.UPDATE_WESITE_STATE)
			client.send(websites)
			if client.recv() == CONFIG.ACTION_FAILED:
				Log.e("{updateWebsiteStates} tell server to update website state failed!")
			Log.d("{updateWebsiteStates} updating websites done!")
		client.close()
	except EOFError:
		Log.e("{updateWebsiteStates} server has been closed")

def uploadWesites(websites):
	Log.d("{uploadWesites} uploading websites(%d) ...", len(websites))
	addr = (CONFIG.DB_HOST, CONFIG.RPC_PORT)
	try:
		client = get_client(addr)
		client.send(CONFIG.UPLOAD_WEBSITE)
		client.send(websites)
		if client.recv() == CONFIG.ACTION_FAILED:
			Log.e("{uploadWesites} upload fetched websites failed!")
		Log.d("{uploadWesites} upload websites done!")
		client.close()
	except EOFError:
		Log.e("{uploadWesites} server has been closed")

def uploadImages(images):
	Log.d("{uploadImages} uploading images(%d) ...", len(images))
	addr = (CONFIG.DB_HOST, CONFIG.RPC_PORT)
	try:
		client = get_client(addr)
		client.send(CONFIG.UPLOAD_IMAGE)
		client.send(images)
		if client.recv() == CONFIG.ACTION_FAILED:
			Log.e("{uploadImages} upload fetched images failed!")
		Log.d("{uploadImages} upload images done!")
		client.close()
	except EOFError:
		Log.e("{uploadImages} server has been closed")

def calcPriority(dist_url, src_url):
	dist = dist_url.split('/')
	src = src_url.split('/')
    
	dist_len = len(dist)
	src_len = len(src)
	priority = dist_len

	addition = 0
	for d in dist:
		if addition >= src_len or not (d == src[addition]):
			break
		addition = addition + 1

	priority += addition

	return priority

def procMain(pid, states):
	states[pid] = STATE_IDLE

	try:
		while True:
			states[pid] = STATE_CONNECTING
			Log.d("{procMain} fetching unvisited websites ...")
			websites = fetchWebsite()
			Log.d("{procMain} fetched websites(%d)", len(websites))
			if websites:
				states[pid] = STATE_BUSY
				wbs = set()
				images = set()

				for web in websites:
					spider = Spider()
					if spider.fetchForUrl(web.url):
						web.request_state = REQUEST_STATE.SUCC
						for url in spider.hrefs:
							wbs.add(DBWebsite(url = url, from_url = web.id, priority = calcPriority(url, web.url)))
						for img in spider.imgs:
							images.add(DBImage(url = img, from_website = web.id, save_path = spider.title))
						web.title = spider.title
					else:
						web.request_state = REQUEST_STATE.FAIL
						retry_times = MAX_REQUEST_RETRY_TIME

						while retry_times > 0:
							Log.i("{procMain} retry fetch url(%s) id(%d) times(%d)", web.url, web.id, retry_times)
							retry_times = retry_times - 1
							if spider.fetchForUrl(web.url):
								web.request_state = REQUEST_STATE.SUCC
								for url in spider.hrefs:
									wbs.add(DBWebsite(url = url, from_url = web.id))
								for img in spider.imgs:
									images.add(DBImage(url = img, from_website = web.id, save_path = spider.title))
								web.title = spider.title
								break
						if web.request_state != REQUEST_STATE.SUCC:
							Log.e("{procMain} fetch url(%s) id(%d) failed!", web.url, web.id)
				
				updateWebsiteStates(websites)
				uploadWesites(wbs)
				uploadImages(images)
			else:
				sleep(3) # sleep for a while to wait for the database update
	except KeyboardInterrupt:
		Log.i("{procMain} spider process exit for a KeyboardInterrupt")

if __name__ == '__main__':
	Log.setup('spider')

	#procMain(1, {})
	
	num = 1
	if len(os.sys.argv) > 1:
		num = int(os.sys.argv[1])
		if num < 1:
			num = 1

	pm = ProcessManager(procMain, maxWorker = num)
	pm.run()
