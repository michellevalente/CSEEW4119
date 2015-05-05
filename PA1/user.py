from datetime import datetime

class User:

	def __init__(self, username, password):
		self.username = username
		self.password = password
		self.date = datetime.today()
		self.loginCounter = 0
		self.port = 0
		self.ip = 0
		self.blocks = []
		self.heartbeat = 0

	def wrongLogin(self):
		self.loginCounter += 1
		if( self.loginCounter == 3):
			self.date = datetime.today()

	def resetLogin(self):
		self.loginCounter = 0

	def definePort(self, port):
		self.port = port

	def defineIP(self, ip):
		self.ip = ip

	def blockUser(self, username):
		self.blocks.append(username)

	def unblockUser(self, username):
		self.blocks.remove(username)

	def resetBlockUsers(self):
		del self.blocks[:]

	def setHeartBeat(self, beat):
		self.heartbeat = beat
