#-*- encoding:utf-8 -*-

"""
一些数据库的配置
"""
class DBConfig(object):
	DBHost = "localhost"
	DBPort = 3030
	DBUser = "root"
	DBPasswd = "toyota"
	DBName = "spider"

# for visited and download state
class REQUEST_STATE(object):
	NONE = 0x00
	DOING = 0x01
	FAIL = 0x02
	SUCC = 0x03

class CommunicateConfig(object):
	RPC_PORT = 6580
	AUTH_KEY = "my secret password"

	COMMUNICATE_MEANS = 'socket' # socket or pipe

	# protocol
	FETCH_IMAGE = 0xef01
	FETCH_WEBSITE = 0xef02

	UPDATE_WESITE_STATE = 0xef03
	UPDATE_IMAGE_STATE = 0xef04

	UPLOAD_IMAGE = 0xef05
	UPLOAD_WEBSITE = 0xef06

	ACTION_FAILED = 0x0000
	ACTION_SUCCESS = 0x0001

class DBServerConfig(CommunicateConfig):
	HOST = ""
	MAX_IMAGE_FETCH_NUM = 30
	MAX_WEB_FETCH_NUM = 10

class DownloadConfig(CommunicateConfig):
	DB_HOST = "localhost"
	
class SpiderConfig(CommunicateConfig):
	DB_HOST = "localhost"


PROXY_CONFIG = {
	'http' : 'socks5://127.0.0.1:1080',
	'https': 'socks5://127.0.0.1:1080'
}

REFRESH_STATE_INTERVAL = "30" # minute -- current is half hours

MAX_REQUEST_RETRY_TIME = 3 # max retry times when request failed

import os
import json
import logging.config

class Log(object):
	logger = None

	@staticmethod
	def setup(name, default_path='log_conf.json', default_level=logging.INFO, env_key='LOG_CFG'):
		path = default_path
		value = os.getenv(env_key, None)
		if value:
			path = value
		if os.path.exists(path):
			with open(path, 'rt') as f:
				config = json.load(f)
			logging.config.dictConfig(config)
		else:
			logging.basicConfig(level=default_level)
		Log.logger = logging.getLogger(name = name)

	@staticmethod
	def e(fmt, *args):
		Log.logger.error(fmt, *args)

	@staticmethod
	def i(fmt, *args):
		Log.logger.info(fmt, *args)

	@staticmethod
	def w(fmt, *args):
		Log.logger.warn(fmt, *args)

	@staticmethod
	def d(fmt, *args):
		Log.logger.debug(fmt, *args)
