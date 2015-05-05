import sys
import socket
import cPickle as pickle
import threading
import time

routingTable = {}
neighborDV = {}
distanceVector = {}
neighbors = []
myAddr = []

# def updateTable(new_table, sender):
# 	for node in new_table:
# 		nodeAddr, nodePort = node.split(':')
# 		if(nodeAddr != myAddr[0] && nodePort != myAddr[1]):
# 			if(node not in routingTable):
# 				routingTable[node] = (float('inf'), "")

# 			for old_node in routingTable:
# 				cost = routingTable[old_node][0]
# 				newCost = routingTable[sender][0] + new_table


def ReadFile(config_file):
	''' Reads configuration file '''

	firstLine = config_file.readline()
	myconfig = firstLine.split()

	port = int(myconfig[0])
	timeout = int(myconfig[1])

	for line in config_file:
		info = line.split()
		neighbor = info[0]
		neighbor_distance = float(info[1])
		distanceVector[neighbor] = neighbor_distance
		neighbors.append(neighbor)

		# Initialize routing table (tuple with distance and next hop)
		routingTable[neighbor] = (neighbor_distance, "")

	return (port, timeout)

def sendRT(s):
	''' Sends Routing table to neighbors '''
	for client in neighbors:
		clientAddr, clientPort = client.split(':')
		#s.sendto("update", (clientAddr,int(clientPort)))
		s.sendto(pickle.dumps(routingTable), (clientAddr,int(clientPort)))

def executeTimeout(timeout, s):
	while(True):
		time.sleep(timeout)
		sendRT(s)

def getRT(s):
	while(True):
		data, addr = s.recvfrom(1024)
		new_rt = pickle.loads(data)
		updateTable(new_rt)

def getCommand():
	while(True):
		print (">"),
		commandLine = sys.stdin.readline()

		command_s = commandLine.split(' ')

		command = command_s[0].rstrip()

		if(len(command_s) == 1):
			parameters = ''
		
		else:
			parameters = command_s[1]
		

		if (command == "SHOWRT"):
			for destination in routingTable:
				print "Destination: " + destination + ", Cost: " + str(routingTable[destination][0]) + ", Link: " + routingTable[destination][1] + "\n",

		if(command == "exit"):
			return

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

	t1 = threading.Thread(target = getRT, args = (s, ))
	t1.daemon = True

	t2 = threading.Thread(target = executeTimeout, args = (timeout, s))
	t2.daemon = True
	
	t3 = threading.Thread(target = getCommand)
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
			print "\nGoodbye :)"
			return

main(sys.argv)