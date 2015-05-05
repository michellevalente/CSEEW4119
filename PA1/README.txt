Programming Assingment 1 - Computer Networks

Michelle Andrade Valente da Silva
UNI: ma3360

------------------------------- Description -----------------------------------

My chat server was separte in 4 files. 

credentials.txt: has all the credentials to access the chat.

protocol.py: class that deals with all the messages exchanged in the chat. 
			 It defines a protocol that has a type, message, source and 
			 destination.

user.py: class for every user of the chat.
		 It defines a user that has a username, password, how many times the 
		 user tried unsucessful to login, the date that that the user tried 
		 to login, port number, ip number, blocked users and the user's last 
		 heartbeat.

client.py: file with the Chat Client. It has functions for authentication, chat, 
		   notifications, finding online users and to send heartbeat. It also 
		   implements the peer-to-peer chat. 

server.py: file with the Message Center. It has functions for user authentication, 
		   user message fowarding, timeout, blacklisting, presence broadcast, 
		   offline messages and to send users address.

------------------------------- How to use it ---------------------------------

To run the program:
	1. Start the server with the port number that you want to user. 
		python server.py port_number
	2. Start the client with the ip number provided by the server and the same 
	   port number.
		python client.py ip_number port_number

Implemented commands:
	message <user> <message> 		Sends <message> to <user> through ​the server

	broadcast <message> 			Sends <message> to all the online users 
									(except those users who have blocked A)
	online 							Print the list of users currently online. 

	block <user> 					This blocks <user> from being able to send 
									a message to A through the server. 
									<user> should get a notification about being 
									blocked

	unblock <user> 					This reverses the block command. 

	logout 							This notifies the server that user A is no longer online. 

	getaddress <user> 				This returns the IP address and PORT of <user>. 

	private <user> <message> 		Sends <message> to <user> directly. 

