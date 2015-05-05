#!/usr/bin/python           # This is client.py file

import socket               # Import socket module
import sys
import protocol as p 
import pickle
import string
import time
import threading

HEART_BEAT = 30

BUFFER = 1024

ev = threading.Event()

addressUsers = {}

def heartBeat(ipServer, port, username):

	while not ev.isSet():
		try:
			beat = p.Protocol(14, "beat", username , "server")
			s = socket.socket()   
			s.connect((ipServer, port))
			s.send(beat.dump())
			s.close()
			time.sleep(HEART_BEAT)

		except KeyboardInterrupt:
			return 


def loads(data):
	return pickle.loads(data)

def login(socketServer, ipServer, ipSource):

	# Send a message to start login
	pLogin = p.Protocol(1, "login", (ipSource), (ipServer))
	socketServer.send(pLogin.dump())

	# Get a message from server
	message = loads(socketServer.recv(BUFFER))

	# Get username
	if(message.message_type == 1):
		username = raw_input(message.message)
		socketServer.send(username)

	# Message type not expected
	else:
		print "Invalid message"
		socketServer.close
		return False

	while(message.message_type != 4):

		# Get password
		message = loads(socketServer.recv(BUFFER))
		socketServer.send(raw_input(message.message))

		message = loads(socketServer.recv(BUFFER))

		# user not found
		if(message.message_type == 6):
			print message.message

			# kill conexion
			socketServer.close
			return False

		# Login Successful
		elif(message.message_type == 4):
			print message.message
			return username

		# invalid password
		elif(message.message_type == 5):
			# receive "try again" message
			print message.message

		# user blocked
		elif(message.message_type == 3):
			print message.message
			socketServer.close
			return False

def user_commands(s, port, username, ipSource, ipServer):
	try:

		# Get the command and the message
		message = raw_input()
		message = message.split(' ')
		command = message[0]
		message = string.join(message[1:])
		s = socket.socket()

		# See who is also online
		if(command == "online"):
			pOnline = p.Protocol(7, "online", ipSource, ipServer)
			s.connect((ipServer, port))
			s.send(pOnline.dump())
			print s.recv(BUFFER)


		# Logout of the chat 
		if(command == "logout"):
			pLogout = p.Protocol(8, username, ipSource, ipServer)
			s.connect((ipServer, int(port)))
			s.send(pLogout.dump())

			print "Goodbye! :)"
			return 1

		# Broadcast a message 
		if(command == "broadcast"):
			pBroadcast = p.Protocol(9, message, username, "all")
			s.connect((ipServer, port))
			s.send(pBroadcast.dump())


		# Broadcast a message 
		if(command == "block"):
			pBlock = p.Protocol(11, message, username, "server")
			s.connect((ipServer, port))
			s.send(pBlock.dump())
			print "User "  + message + " is blocked"


		# Broadcast a message 
		if(command == "unblock"):
			pBlock = p.Protocol(12, message, username, "server")
			s.connect((ipServer, port))
			s.send(pBlock.dump())
			print "User "  + message + " is unblocked"



		# Messsage an user
		if(command == "message"):
			message = message.split(' ')
			destination = message[0]
			message = string.join(message[1:])

			pMessage = p.Protocol(10, message, username, destination)

			s.connect((ipServer, port))

			s.send(pMessage.dump())


		# Get the user address
		if(command == "getaddress"):
			pMessage = p.Protocol(16, message, username, "server")
			s.connect((ipServer, port))
			s.send(pMessage.dump())


		# Private message
		if(command == "private"):
			message = message.split(' ')
			destination = message[0]
			message = string.join(message[1:])
			if(destination in addressUsers.keys() ):
				portDestination = addressUsers[destination][0]
				ip = addressUsers[destination][1]

				# See if the user is still at the same address
				pOnline = p.Protocol(18, destination, username, destination)
				socketServ = socket.socket()
				socketServ.connect((ipServer, port))
				socketServ.send(pOnline.dump())
				socketServ.send(str(portDestination))
				time.sleep(1)
				socketServ.send(str(ip))
				online = socketServ.recv(BUFFER)
				socketServ.close()

				# Get the message from the server if the user is online at this address
				if(online == "online"):
					pMessage = p.Protocol(10, message, username, destination)
					s.connect((ip, port))
					s.send(pMessage.dump())
				else:
					print "This user is not at the same address anymore."
			else:
				print "You don't have this user addresss."

		s.close()

		return 0

		
	except KeyboardInterrupt:
		return 1

def print_message(sClient, t1):
	sClient.listen(1)  
	messageType = 0

	while messageType != 8 and not ev.isSet():
		try:
			c, addr = sClient.accept()   
			message = loads(c.recv(BUFFER))
			messageType = message.message_type
			if(messageType == 16):
				ip = message.message
				port = message.destination
				destinationName = message.source
				addressUsers.update([(destinationName, (port, ip))])
			elif(messageType != 8):
				if(messageType == 15):
					print message.message
					ev.set()
					return
				elif(messageType != 11 and messageType != 1):
					print message.source + ": " + message.message
				else:
					print message.message
		except KeyboardInterrupt:
			return

def command_thread(s, port, username, ipSource, ipServer):

	while s != 1 and not ev.isSet():
		# returns 1 when the user logout
		s = user_commands(s, port, username, ipSource, ipServer)
	ev.set()
	return s

def main(argv):
	s = socket.socket()         	
	ipServer = argv[1]

	ipSource = socket.gethostbyname(socket.gethostname())
	ipSource = 2

	port = int(argv[2])         

	s.connect((ipServer, port))

	username = login(s, ipServer, ipSource) 

	sClient = socket.socket()

	sClient.bind((socket.gethostname(), 0))

	portListen = sClient.getsockname()[1]

	s.send(str(portListen))

	s.close()

	# Login failed
	if(username == False):
		return

	s = socket.socket()

	t1 = threading.Thread(target = command_thread, args = (s, port, username, ipSource, ipServer))
	t1.daemon = True
	t2 = threading.Thread(target = print_message, args = (sClient, t1) )
	t2.daemon = True
	t3 = threading.Thread(target = heartBeat, args = (ipServer, port, username))
	t3.daemon = True
	t2.start()
	t1.start()
	t3.start()

	while True and t1.is_alive():
		try:
			time.sleep(.1)
			if(not t2.is_alive()):
				return
		except KeyboardInterrupt:
			print "\nGoodbye :)"
			return

main(sys.argv)