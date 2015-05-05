#!/usr/bin/python          

import socket               # Import socket module
import sys
import user as u
from datetime import datetime
import protocol as p
import pickle
import threading
import time

BUFFERSIZE = 128
blockTime = 20 
MAX_USERS = 30
HEART_BEAT = 30

onlineUsers = {} 
offlineMessages = {}
ev = threading.Event()

def heartBeat():
	# Send the HeartBeat for the server
	while not ev.isSet():
		usersTimout = []
		time.sleep(HEART_BEAT + 1)
		for username in onlineUsers:
			user = onlineUsers[username]
			t = user.heartbeat
			t_now = datetime.now()
			s = (t_now - t)
			s = s.seconds
			if(s > HEART_BEAT):
				usersTimout.append(username)
		for username in usersTimout:
			onlineUsers.pop(username)

# Dump object  
def dump(data):
	return pickle.dumps(data, -1 )

# Load object
def loads(data):
	return pickle.loads(data)

def login(credentials, socketClient, socketServer):

	ipServer = socket.gethostbyname(socket.gethostname())
	ipClient = socketClient.getsockname()[0]

	# Ask the username
	pUsername = p.Protocol(1, "username: ", ipServer, ipClient )
	socketClient.send(pUsername.dump())
	username = socketClient.recv(BUFFERSIZE)

	while(True):
		try:
			# Ask the password
			pPassword = p.Protocol(2, "password: ", ipServer , ipClient )
			socketClient.send(pPassword.dump())
			password = socketClient.recv(BUFFERSIZE)

			# if username exists
			if(credentials.has_key(username)):

				# Create object user
				user = credentials[username]
				# if this user tried to acces uncessfully more than 3 times
				if(user.loginCounter >= 3):
					dateNow = datetime.now()
					time = dateNow - user.date
					# check if user is still blocked
					if(time.seconds < blockTime):
						pBlocked = p.Protocol(3, "Your account has been blocked. Please try again after sometime." , \
							ipServer , ipClient )
						socketClient.send(pBlocked.dump())
						return False
					else:
						# reset login counter
						user.resetLogin()

				# Login Successfull
				if( password == user.password ):
					pLogged = p.Protocol(4, "Welcome!", ipServer , ipClient )
					socketClient.send(pLogged.dump())
					if(username in onlineUsers.keys()):
						user = onlineUsers[username]
						message = p.Protocol(15, "Another user logged into your account. You are going to be disconected.", ipServer, ipClient)
						d = socket.socket()
						d.connect((user.ip, user.port))
						d.send(message.dump())
						d.close()
						onlineUsers.pop(username)
					portClient = int(socketClient.recv(BUFFERSIZE))
					ip = socketClient.getpeername()[0]
					user.definePort(portClient)
					user.defineIP(ip)
					user.resetBlockUsers()
					onlineUsers.update([(username, user)])
					send_offline_messages(user)

					return user

				else:

					# Wrong password
					user.wrongLogin()

					#Block account
					if(user.loginCounter == 3):
						pBlocked = p.Protocol(3, "Your account has been blocked. Please try again after sometime. "\
							, ipServer , ipClient )
						socketClient.send(pBlocked.dump())
						return False

					# Inform wrong password
					else:
						pInvalidPassword = p.Protocol(5, "Invalid password.", ipServer , ipClient )
						socketClient.send(pInvalidPassword.dump())

			# Username doesnt exist
			else:
				pInvalidUsername = p.Protocol(6, "Username invalid.", ipServer , ipClient )
				socketClient.send(pInvalidUsername.dump())
				return False
		except KeyboardInterrupt:
			return False


def readFile():

    # Dictionary 
    credentials = {}

    # open file
    infile = open("credentials.txt", 'r')

    while(1):
    	# Read line from file
    	line = infile.readline()

    	# If it is not a line end it
        if(not line):
            break

        username, password = line.split(' ')
        size = len(password)
        password = password[:size - 1]
        
        newUser = u.User(username, password)
        credentials.update([(username, newUser)])

    return credentials

def send_offline_messages(user):
	# Send offline messages to the users after they logged in
	if(user in offlineMessages.keys()):

		firstMessage = p.Protocol(1, "offline messages: ", 1, 2)
		s = socket.socket()
		s.connect((user.ip, user.port))
		s.send(firstMessage.dump())
		s.close()

		messagelist = offlineMessages[user]

		for message in messagelist:
			s = socket.socket()
			s.connect((user.ip, user.port))
			s.send(message.dump())
			s.close()

		offlineMessages.pop(user, None)

def messageCenter(argv, test):
	s = socket.socket()         # Create a socket object
	host = socket.gethostname() # Get local machine name
	print "Chat address: " + socket.gethostbyname(host)
	port = int(argv[1])         # Reserve a port for the chat
	s.bind((host, port))        # Bind to the port
	s.listen(MAX_USERS)         # Wait for client connection.
	credentials = readFile()	# Read credentials and save in a dictionary

	while True:
		try:
			broadcastOnline = 0
			broadcastLogout = 0
			# Establish connection with client.
			c, addr = s.accept()    
			# Get message from user
			message = loads(c.recv(BUFFERSIZE))
			source = message.source
			destination = message.destination

			# User wants to login
			if(message.message_type == 1):
				userOn = login(credentials, c, s)
				if(userOn != False): 
					broadcastOnline = 1

			# Command "online"
			if(message.message_type == 7):
				c.send(str(onlineUsers.keys()).strip('[]'))

			# Command "logout"
			if(message.message_type == 8):
				userLogout = onlineUsers[message.message]
				onlineUsers.pop(message.message)
				sLogout = socket.socket()
				sLogout.connect((userLogout.ip, userLogout.port))
				pLogout = p.Protocol(8, "logout", 1 , 2 )
				sLogout.send(pLogout.dump())
				sLogout.close()
				broadcastLogout = 1

			# Command "broadcast"
			if(message.message_type == 9 or broadcastOnline == 1 or broadcastLogout == 1 ):
				if(broadcastOnline == 1):
					userSource = userOn
					source = userSource.username
					messageOn = userSource.username + " is online."
					pBroadcast = p.Protocol(1, messageOn, source , 2 )
				elif(broadcastLogout == 1):
					userSource = userLogout
					source = userSource.username
					messageOff = userSource.username + " logout."
					pBroadcast = p.Protocol(1, messageOff, source , 2 )
				else:
					userSource = onlineUsers[source]
					pBroadcast = p.Protocol(9, message.message, source , 2 )
				for user in onlineUsers.itervalues():
					if(user.username != source and (userSource.username not in user.blocks)):
						sBroadcast = socket.socket()
						sBroadcast.connect((user.ip, user.port))
						sBroadcast.send(pBroadcast.dump())
						sBroadcast.close()
					if(userSource.username in user.blocks and broadcastOnline != 1 and broadcastLogout == 0):
						sBroadcast = socket.socket()
						sBroadcast.connect((userSource.ip, userSource.port))
						pMessage =  p.Protocol(11, "Your message could not be delivered to some recipients", source , 2 )
						sBroadcast.send(pMessage.dump())
						sBroadcast.close()

			# Command "message"
			if(message.message_type == 10):
				pMessage = p.Protocol(10, message.message, source , destination )
				for user in credentials.itervalues():
					if(user in onlineUsers.itervalues()):
						if(user.username == destination and (userSource.username not in user.blocks)):
							sBroadcast = socket.socket()
							sBroadcast.connect((user.ip, user.port))
							sBroadcast.send(pMessage.dump())
							sBroadcast.close()
						if(userSource.username in user.blocks and user.username == destination):
							sBroadcast = socket.socket()
							sBroadcast.connect((userSource.ip, userSource.port))
							pMessage =  p.Protocol(11, "Your message could not be delivered as the recipient has blocked you", source , 2 )
							sBroadcast.send(pMessage.dump())
							sBroadcast.close()
					else:
						if(user.username == destination):
							if(user not in offlineMessages.keys() ):
								messageList = []
								messageList.append(pMessage)
								offlineMessages.update([(user, messageList)])

							else:
								messageList = offlineMessages[user]
								messageList.append(pMessage)
								offlineMessages[user] = messageList

			# Command "block"
			if(message.message_type == 11):
				user = onlineUsers[message.source]
				user.blockUser(message.message)

			# Command "unblock"
			if(message.message_type == 12):
				user = onlineUsers[message.source]
				user.unblockUser(message.message)

			# Update heartbeat
			if(message.message_type == 14):
				user = onlineUsers[message.source]
				now = datetime.now()
				user.setHeartBeat(now)

			# Command "getaddress"
			if(message.message_type == 16):
				userSource = onlineUsers[source]
				if(message.message in onlineUsers.keys() ):
					userDestination = onlineUsers[message.message]
					if(userSource.username not in userDestination.blocks ):
						portDestination = userDestination.port
						ipDestination = userDestination.ip
						pmessage = p.Protocol(16, ipDestination, message.message, portDestination)
					else:
						pmessage = p.Protocol(10, "This user has blocked you.", "Server ", 2)
					sAddress = socket.socket()
					sAddress.connect((userSource.ip, userSource.port))
					sAddress.send(pmessage.dump())
					sAddress.close()
				else:
					pmessage = p.Protocol(10, "This user is offline.", "Server ", 2)
					sAddress = socket.socket()
					sAddress.connect((userSource.ip, userSource.port))
					sAddress.send(pmessage.dump())
					sAddress.close()

			# See if a user is online
			if(message.message_type == 18):
				user = onlineUsers[message.source]
				portPrivate = c.recv(BUFFERSIZE)
				ipPrivate = c.recv(BUFFERSIZE)
				if(message.message in onlineUsers.keys()):
					userDestination = onlineUsers[message.message]
					if(portPrivate == str(userDestination.port) and ipPrivate == str(userDestination.ip)):
						c.send("online")
					else:
						c.send("offline")
				else:
					c.send("offline")
									
		except KeyboardInterrupt:
			ev.set()
			return 

def main(argv):

	t1 = threading.Thread(target = messageCenter, args = (argv, 1) )
	t1.daemon = True
	t2 = threading.Thread(target = heartBeat)
	t2.daemon = True
	t1.start()
	t2.start()

	while True:
		try:
			time.sleep(.1)
		except KeyboardInterrupt:
			print "\nchat closed"
			return

main(sys.argv)