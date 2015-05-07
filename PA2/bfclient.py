import sys
import socket
import cPickle as pickle
import threading
import time

routingTable = {}
neighborRT = {}
distanceVector = {}
neighbors = {}
myAddr = []

class Message:
	def __init__(self, message_type, message):
		self.message_type = message_type
		self.message = message

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

	for node in new_table:
		myNode = str(myAddr[0]) + ":" + str(myAddr[1])
		if(node != myNode):
			if(node not in routingTable):
				routingTable[node] = (routingTable[sender][0] + new_table[node][0], sender)

			else:
				cost = routingTable[node][0]
				newCost = routingTable[sender][0] + new_table[node][0]
				if(newCost == float('inf') and node not in neighbors):
					routingTable[node] = (float('inf'), "")
				elif(newCost < cost):
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
		time.sleep(timeout)
		sendRT(s)

def getMessage(s):
	''' Get the routing table from other nodes '''
	while(True):
		data, addr = s.recvfrom(1024)

		sender = str(addr[0]) + ":" + str(addr[1])
		messageRcv = pickle.loads(data)
		if(messageRcv.message_type == "update"):
			updateTable(messageRcv.message, sender)

		elif(messageRcv.message_type == "linkdown"):
			routingTable[sender] = (float('inf'), "")

		elif(messageRcv.message_type == "linkup"):
			cost = neighbors[sender]
			routingTable[sender] = (cost, sender)


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
		print("Invalid parameters for LINKDOWN")

def getCommand(s):
	''' Get commands from user '''
	while(True):
		print (">"),
		commandLine = sys.stdin.readline()

		command_s = commandLine.split(' ')

		command = command_s[0].rstrip()
		

		if (command == "SHOWRT"):
			for destination in routingTable:
				print "Destination: " + destination + ", Cost: " + str(routingTable[destination][0]) + ", Link: " + routingTable[destination][1] + "\n",
		
		elif (command == "LINKDOWN"):
			if(len(command_s) == 3):
				addr  = command_s[1]
				port = command_s[2].rstrip()
				linkDown(s, addr, port)
			else:
				print("Missing parameters to LINKDOWN")

		elif( command == "LINKUP"):
			if(len(command_s) == 3):
				addr  = command_s[1]
				port = command_s[2].rstrip()
				linkUp(s, addr, port)
			else:
				print("Missing parameters to LINKUP")

		elif(command == "CLOSE"):
			return
		
		else:
			print ("Invalid command")

def defineDistanceVector(client):
	''' update Distance Vector for Poison reverse functionality '''
	for node in routingTable:
		if(node != client and routingTable[node][1] == client):
			distanceVector[node] = (float('inf'), "")
		else:
			distanceVector[node] = routingTable[node]

def main(argv):

	distanceVector = {}

	host = socket.gethostbyname(socket.gethostname())

	# Read the config file
	nameFile = sys.argv[1]
	config = open(nameFile)
	resultsFile = ReadFile(config)
	port = resultsFile[0]
	timeout = resultsFile[1]

	myAddr.append(host)
	myAddr.append(port)
	# Create a socket
	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	s.bind((host, port))
	
	print "Host: " + host + " Port: " + str(port)

	t1 = threading.Thread(target = getMessage, args = (s, ))
	t1.daemon = True

	t2 = threading.Thread(target = executeTimeout, args = (timeout, s))
	t2.daemon = True
	
	t3 = threading.Thread(target = getCommand, args = (s, ))
	t3.daemon = True
	
	t3.start()

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