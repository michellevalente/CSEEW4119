import sys
import socket
import cPickle as pickle
import threading
import time
import copy
import datetime

routingTable = {}
neighborRT = {}
distanceVector = {}
neighbors = {}
times = {}
myAddr = []

class Message:
	def __init__(self, message_type, message):
		self.message_type = message_type
		self.message = message

class transferFile:
	def __init__(self, sender, destination, data_file, seqnum, filename):
		self.sender = sender
		self.destination = destination
		self.data_file = data_file
		self.seqnum = seqnum
		self.filename = filename

def printRoutingTable():
	''' For debugging '''
	time.sleep(2)
	for neighbor in neighborRT:
		table = neighborRT[neighbor]
		for node in table:
			print("Node: "),
			print(node)
			print("Cost: "),
			print(table[node][0])
			print("Next hop: "),
			print(table[node][1])

def updateTable(new_table, sender):
	''' Update routing tables '''
	myNode = str(myAddr[0]) + ":" + str(myAddr[1])
	if( sender in neighborRT ):
		dictSender = neighborRT[sender]
		for node in new_table:
			if(node not in dictSender ):
				dictSender[node] = new_table[node]
			else:
				if(dictSender[node][0] != new_table[node][0] or dictSender[node][1] != new_table[node][1] ):
					dictSender[node] = (new_table[node][0], new_table[node][1])
	else:
		neighborRT[sender] = new_table

	if(sender not in neighbors):
		neighbors[sender] = new_table[myNode][0]
		routingTable[sender] = (new_table[myNode][0], sender)

	for node in new_table:
		myNode = str(myAddr[0]) + ":" + str(myAddr[1])
		if(node != myNode):
			if(node not in routingTable):
				routingTable[node] = (routingTable[sender][0] + new_table[node][0], sender)

			else:
				cost = routingTable[node][0]
				newCost = routingTable[sender][0] + new_table[node][0]
				if(newCost == float('inf') and node not in neighbors and routingTable[node][1] == sender):
					routingTable[node] = (float('inf'), "")
				elif(newCost < cost):
					routingTable[node] = (newCost, sender)
				elif(routingTable[node][1] == sender):
					routingTable[node] = (newCost, sender)

def ReadFile(config_file):
	''' Read configuration file '''

	firstLine = config_file.readline()
	myconfig = firstLine.split()

	port = int(myconfig[0])
	timeout = int(myconfig[1])

	for line in config_file:
		info = line.split()
		neighbor = info[0]
		neighbor_distance = float(info[1])
		neighbors[neighbor] = neighbor_distance

		# Initialize routing table (tuple with distance and next hop)
		routingTable[neighbor] = (neighbor_distance, neighbor)

	return (port, timeout)

def sendRT(s):
	''' Send distance vector to neighbors '''

	for client in neighbors:
		clientAddr, clientPort = client.split(':')
		defineDistanceVector(client)
		messageSnd = Message("update", distanceVector)
		s.sendto(pickle.dumps(messageSnd), (clientAddr,int(clientPort)))

def sendMessage(s, message_type, message, client):
	''' Send a message to a client ''' 
	clientAddr, clientPort = client.split(':')
	messageSnd = Message(message_type, message)
	s.sendto(pickle.dumps(messageSnd), (clientAddr,int(clientPort)))


def executeTimeout(timeout, s):
	''' Send routing table after every timeout'''
	while(True):
		sendRT(s)
		time.sleep(timeout)

def getMessage(s):
	myNode = str(myAddr[0]) + ":" + str(myAddr[1])
	''' Get the routing table from other nodes '''
	while(True):
		data, addr = s.recvfrom(1024)

		sender = str(addr[0]) + ":" + str(addr[1])
		times[sender] = int(round(time.time() * 1000))

		messageRcv = pickle.loads(data)
		if(messageRcv.message_type == "update"):
			updateTable(messageRcv.message, sender)

		elif(messageRcv.message_type == "linkdown"):
			routingTable[sender] = (float('inf'), "")

		elif(messageRcv.message_type == "linkup"):
			cost = neighbors[sender]
			routingTable[sender] = (cost, sender)

		elif(messageRcv.message_type == "changecost"):
			neighbors[sender] = messageRcv.message
			routingTable[sender] = (messageRcv.message, sender)
		elif(messageRcv.message_type == "close"):
			if(messageRcv.message in neighbors):
				del neighbors[messageRcv.message]
				routingTable[messageRcv.message] = (float('inf'), "")

		elif(messageRcv.message_type == "file"):
			chunk = messageRcv.message
			if(chunk.data_file == "eof" ):
				if(chunk.destination == myNode):
					print("File received successfully")
				else:
					next_hop = routingTable[chunk.destination][1]
					nextHop_addr, nextHop_port = next_hop.split(':')
					s.sendto(pickle.dumps(messageRcv), (nextHop_addr, int(nextHop_port)))
			else:
				getFile(s, chunk)

def linkDown(s, Addr, Port):
	''' execute command LINKDOWN ''' 
	node = str(Addr) + ":" + str(Port)
	if(node in neighbors):
		routingTable[node] = (float('inf'), "")
		sendMessage(s, "linkdown", "linkdown", node)
		sendRT(s)
	else:
		print("Invalid parameters for LINKDOWN")

def linkUp(s, Addr, Port):
	''' execute command LINKUP '''
	node = str(Addr) + ":" + str(Port)
	if(node in neighbors):
		cost = neighbors[node]
		routingTable[node] = (cost, node)
		sendMessage(s, "linkup", "linkup", node)
		sendRT(s)
	else:
		print("Invalid parameters for LINKUP")

def changeCost(s, Addr, Port, new_cost):
	''' execute command CHANGECOST '''
	node = str(Addr) + ":" + str(Port)
	if(node in neighbors):
		neighbors[node] = new_cost
		routingTable[node] = (new_cost, node)
		sendMessage(s, "changecost", new_cost, node)
		sendRT(s)
	else:
		print("Invalid parameters for CHANGECOST")

def sendFile(s, sender, Addr, Port, filename):
	''' send file to another user'''
	node = str(Addr) + ":" + str(Port)
	inFile = open(filename,'rb')
	next_hop = routingTable[node][1]
	nextHop_addr, nextHop_port = next_hop.split(':')
	chunk_data = inFile.read(200)
	seqnum = 0
	print("Next hop = " + next_hop)
	while(chunk_data != ""):
		chunk = transferFile(sender, node, chunk_data, seqnum, filename)
		message = Message("file", chunk)
		s.sendto(pickle.dumps(message), (nextHop_addr, int(nextHop_port)))
		chunk_data = inFile.read(200)
		seqnum += 1
		time.sleep(.00001)
	time.sleep(1)
	chunk = transferFile(sender, node, "eof", seqnum, filename)
	message = Message("file", chunk)
	s.sendto(pickle.dumps(message), (nextHop_addr, int(nextHop_port)))
	print("File sent successfully")

def getFile(s, chunk):
	''' receive file from another user'''
	myNode = str(myAddr[0]) + ":" + str(myAddr[1])
	if(chunk.destination != myNode):
		next_hop = routingTable[chunk.destination][1]
		nextHop_addr, nextHop_port = next_hop.split(':')
		message = Message("file", chunk)
		s.sendto(pickle.dumps(message), (nextHop_addr, int(nextHop_port)))
		print("Packet received")
		print("Source = " + chunk.sender)
		print("Destination = " + chunk.destination)
		print("Next hop = " + next_hop)

	else:
		if(chunk.seqnum == 0):
			outfile = open("output", 'wb')
		else:
			outfile = open("output", 'a')
		outfile.write(chunk.data_file)
		print("Packet received")
		print("Source = " + chunk.sender)
		print("Destination = " + chunk.destination)


def getCommand(s):
	''' Get commands from user '''
	myNode = str(myAddr[0]) + ":" + str(myAddr[1])
	while(True):

		commandLine = raw_input(">")

		command_s = commandLine.split(' ')

		command = command_s[0].rstrip()
		
		if (command == "SHOWRT"):
			testDisconnected()
			print(datetime.datetime.now()),
			print(" Distance vector list is: ")
			for destination in routingTable:
				print "Destination: " + destination + ", Cost: " + str(routingTable[destination][0]) + ", Link: " + routingTable[destination][1]
		
		elif (command == "LINKDOWN"):
			if(len(command_s) == 3):
				addr  = command_s[1]
				port = command_s[2].rstrip()
				linkDown(s, addr, port)
			else:
				print("Missing parameters to LINKDOWN")

		elif(command == "LINKUP"):
			if(len(command_s) == 3):
				addr  = command_s[1]
				port = command_s[2].rstrip()
				linkUp(s, addr, port)
			else:
				print("Missing parameters to LINKUP")

		elif(command == "CHANGECOST"):
			if(len(command_s) == 4):
				addr = command_s[1]
				port = command_s[2]
				new_cost = float(command_s[3].rstrip())
				changeCost(s, addr, port, new_cost)
			else:
				print("Missing parameters to CHANGECOST")

		elif(command == "CLOSE"):
			return

		elif(command == "TRANSFER"):
			if(len(command_s) == 4):
				filename = command_s[1]
				addr = command_s[2]
				port = command_s[3].rstrip()
				sendFile(s, myNode, addr, port, filename)
			else:
				print("Missing parameters to TRANSFER")
		else:
			print ("Invalid command")

def defineDistanceVector(client):
	''' update Distance Vector for Poison reverse functionality '''
	myNode = str(myAddr[0]) + ":" + str(myAddr[1])
	for node in routingTable:
		if(node == myNode):
			del routingTable[node]
		if(node != client and routingTable[node][1] == client):
			distanceVector[node] = (float('inf'), "")
		else:
			distanceVector[node] = routingTable[node]

def isAlive(timeout, s):
	time.sleep(5)
	while(True):
		try:
			neighbors_copy = copy.deepcopy(neighbors)
			for node in neighbors_copy:
				if times[node] + timeout*3000 <  int(round(time.time() * 1000)):
					Addr, Port = node.split(':')
					linkDown(s, Addr, Port)
					del neighbors[node]
		except:
			pass

def initTimes():
	for node in neighbors:
		times[node] = int(round(time.time() * 1000))

def testDisconnected():
	for node in routingTable:
		if(routingTable[node][0] == float('inf')):
			routingTable[node] = (float('inf'), "")
def main(argv):

	distanceVector = {}

	host = socket.gethostbyname(socket.gethostname())

	# Read the config file
	nameFile = sys.argv[1]
	config = open(nameFile)
	resultsFile = ReadFile(config)
	port = resultsFile[0]
	timeout = int(resultsFile[1])

	myAddr.append(host)
	myAddr.append(port)

	# Create a socket
	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	s.bind((host, port))

	initTimes()
	
	print "Host: " + host + " Port: " + str(port)

	t1 = threading.Thread(target = getMessage, args = (s, ))
	t1.daemon = True

	t2 = threading.Thread(target = executeTimeout, args = (timeout, s))
	t2.daemon = True
	
	t3 = threading.Thread(target = getCommand, args = (s, ))
	t3.daemon = True
	
	t4 = threading.Thread(target = isAlive, args = (timeout,s ))
	t4.daemon = True
	t3.start()
	t4.start()
	t1.start()
	t2.start()

	while True and t3.is_alive():
		try:
			time.sleep(.1)
			if(not t3.is_alive()):
				return
		except KeyboardInterrupt:
			print "\nClosed :)"
			return

main(sys.argv)