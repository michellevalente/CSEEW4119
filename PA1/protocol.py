import pickle
import copy

class Protocol:

	def __init__(self, message_type, message, source, destination):
		self.message_type = message_type
		self.message = message
		self.source = source
		self.destination = destination

	def dump(self):
		return pickle.dumps(self, -1 )