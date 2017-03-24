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
from config import REQUEST_STATE, PROXY_CONFIG, MAX_REQUEST_RETRY_TIME, Log

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
						Log.e("{Downloader.download} HTML response state(%d) while downloading (%s)", response.raw.status, src)
				except requests.packages.urllib3.exceptions.ReadTimeoutError as e:
					Log.e("{Downloader.download} download file (%s) failed! Exception(%s)", src, str(e))
				finally:
					fp.close()
			except IOError:
				Log.e("{Downloader.download} can't write file to path (%s)", path)
		except requests.exceptions.ConnectionError as err:
			Log.e("{Downloader.download} connect error: Exception<%s>", str(err))
		except Exception as ex:
			Log.e("{Downloader.download} download (%s): Raise exception<%s>", src, str(ex))
	
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
		client = get_client(addr, means = CONFIG.COMMUNICATE_MEANS)
		client.send(CONFIG.FETCH_IMAGE)
		result = client.recv()
		if result == CONFIG.ACTION_FAILED:
			Log.e("{fetchImages} get download images failed")
		else:
			images = client.recv()

		client.close()
	except EOFError:
		Log.e("{fetchImages} server side has been closed")
	except Exception as e:
		Log.e("{fetchImages} raise exceptions: %s", str(e))

	return images

def updateImages(images):
	Log.d("{updateImages} updating images ...")
	addr = (CONFIG.DB_HOST, CONFIG.RPC_PORT)
	try:
		client = get_client(addr, means = 'Socket')
		client.send(CONFIG.UPDATE_IMAGE_STATE)
		client.send(images)
		if client.recv() == CONFIG.ACTION_FAILED:
			Log.e("{updateImages} tell server to update images state failed!")
		client.close()
	except EOFError:
		Log.e("{updateImages} server has been closed")

	Log.d("{updateImages} update images done")

def procMain(pid, states):
	states[pid] = STATE_IDLE

	# init black site list
	bSite = BlackSiteList(BLACK_SITE_FILE)
	try:
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

					Log.d("{procMain} downloading image (%s) ", img.url)

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
							Log.i("{procMain} retry download image(%s) times(%d)", img.url, retry_times)
							retry_times = retry_times - 1
							if Downloader.download(img.url, save_dir, file_name):
								img.request_state = REQUEST_STATE.SUCC
								img.save_path = save_dir
								break
						if img.request_state != REQUEST_STATE.SUCC:
							bSite.addFaileSite(site)
							bSite.save()
							#Log.e("{procMain} download image(%s) failed!", img.url)

				updateImages(images)
			else:
				time.sleep(3) # sleep for a while to wait for the database update
	except KeyboardInterrupt:
		Log.i("{procMain} downloader process exit for a KeyboardInterrupt")

if __name__ == '__main__':
	Log.setup("download")

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
	

