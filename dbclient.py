# -*- coding: UTF-8 -*-

#from multiprocessing.connection import Client
import socket
from config import CommunicateConfig as CONFIG
from dbmodel import Socket4Pickle

def get_client(addr):
	
	"""
	client = Client(addr, authkey = CONFIG.AUTH_KEY)
	"""
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	#print "[info] Connecting to host: ", addr
	s.connect(addr) 
	client = Socket4Pickle(s)

	return client