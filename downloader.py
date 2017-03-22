#-*- encoding:utf-8 -*-

import requests
import hashlib
import re
import os
import shutil
import time
#from multiprocessing.connection import Client
import socket
from processmanager import *

from dbmodel import DBImage
from dbclient import *
from config import DownloadConfig as CONFIG
from config import REQUEST_STATE, PROXY_CONFIG, MAX_REQUEST_RETRY_TIME

IMGREG = re.compile("\.([^/^\.]+)$")
CONNECT_TIME_OUT = 15 #second
BLACK_SITE_FILE = './image_black_site.json'

DIR_PATH = os.path.dirname(os.path.realpath(__file__))

class Downloader(object):
	@staticmethod
	def download(src, save_dir = DIR_PATH, file_name = None):
		ext = ""
		reg = IMGREG.search(src)
		if reg:
			ext = '.' + reg.group(1)
		if file_name is None:	
			sha = hashlib.sha1()
			sha.update(src)
			file_name = sha.hexdigest()
		path = os.path.join(save_dir, file_name + ext)

		ret = False
		try:
			response = requests.get(src, stream = True, verify = False, timeout = CONNECT_TIME_OUT, proxies = PROXY_CONFIG)
			try:
				fp = open(path, 'wb')
				try:
					if response.raw.status == 200:
						shutil.copyfileobj(response.raw, fp)
						ret = True
					else:
						print "[Warn] HTML response state{%d} while downloading '%s'" % (response.raw.status, src)
				except requests.packages.urllib3.exceptions.ReadTimeoutError as e:
					print "[Warn]Download file '%s' failed! Exception<%s>" % (src, str(e))
				finally:
					fp.close()
			except IOError:
				print "[Warn]Can't write file to path '%s'" % path
		except requests.exceptions.ConnectionError as err:
			print "[Warn]Connect error: Exception<%s>" % str(err)
		except Exception as ex:
			print "[Warn]Downloader.download {%s}: Raise exception<%s>" % (src, str(ex))
	
		if not ret and os.path.exists(path):
			os.remove(path) #delete failed image
		return ret

def getDir():
	dir_path = os.path.join(DIR_PATH, time.strftime("%Y_%m_%d"))
	if not os.path.exists(dir_path):
		os.makedirs(dir_path)
	return dir_path

def fetchImages():
	addr = (CONFIG.DB_HOST, CONFIG.RPC_PORT)
	images = None
	try:
		client = get_client(addr)
		client.send(CONFIG.FETCH_IMAGE)
		result = client.recv()
		if result == CONFIG.ACTION_FAILED:
			print "[Warn]get download images failed"
		else:
			images = client.recv()

		client.close()
	except EOFError:
		print "[Warn]fetchImages: Server side has been closed"
	except Exception as e:
		print "[Error]fetchImages raise exceptions: %s" % str(e)

	return images

def updateImages(images):
	print "[Info]Updating images"
	addr = (CONFIG.DB_HOST, CONFIG.RPC_PORT)
	try:
		client = get_client(addr, means = 'Socket')
		client.send(CONFIG.UPDATE_IMAGE_STATE)
		client.send(images)
		if client.recv() == CONFIG.ACTION_FAILED:
			print "[Error] Tell server to update images state failed!"
		client.close()
	except EOFError:
		print "[Warn] Server has been closed"

	print "[Info] Update images done"

def procMain(pid, states):
	states[pid] = STATE_IDLE

	# init black site list
	bSite = BlackSiteList(BLACK_SITE_FILE)

	while True:
		states[pid] = STATE_CONNECTING
		images = fetchImages()
		if images:
			states[pid] = STATE_BUSY
			for img in images:
				save_dir = getDir()
				file_name = None
				if img.name != "":
					file_name = img.name 

				print "[Info]Downloading image {%s} " % img.url

				if Downloader.download(img.url, save_dir, file_name):
					img.request_state = REQUEST_STATE.SUCC
					img.save_path = save_dir
				else:
					site = img.url.split('/')[2]
					fail_count = bSite.getFaileSiteCount(site)

					img.request_state = REQUEST_STATE.FAIL
					# retry download
					retry_times = MAX_REQUEST_RETRY_TIME - fail_count
					if retry_times < 0:
						retry_times = 0

					while retry_times > 0:
						print "[Warn]Retry download image {%s} %d times" % (img.url, retry_times)
						retry_times = retry_times - 1
						if Downloader.download(img.url, save_dir, file_name):
							img.request_state = REQUEST_STATE.SUCC
							img.save_path = save_dir
							break
					if img.request_state != REQUEST_STATE.SUCC:
						bSite.addFaileSite(site)
						bSite.save()
						print "[Error]Download image{%s} failed!" % img.url

			updateImages(images)
		else:
			time.sleep(3) # sleep for a while to wait for the database update

	states[pid] = STATE_TERMINATE

if __name__ == '__main__':	
	"""
	procMain(1, {})
	"""
	num = 1
	if len(os.sys.argv) > 1:
		num = int(os.sys.argv[1])
		if num < 1:
			num = 1
			
	pm = ProcessManager(procMain, maxWorker = num)
	pm.run()
	

