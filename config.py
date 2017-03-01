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
	RPC_PORT = 8080
	AUTH_KEY = "my secret password"
	
	MAX_FETCH_NUM = 10

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
	HOST = "localhost"

class DownloadConfig(CommunicateConfig):
	HOST = "127.0.0.1"
	MAX_PROC_NUM = 10
	
class SpiderConfig(CommunicateConfig):
	HOST = "127.0.0.1"
	MAX_PROC_NUM = 10


REFRESH_STATE_INTERVAL = "0:30:0" # {hours}:{minutes}:{seconds} update interval -- current is half hours  
