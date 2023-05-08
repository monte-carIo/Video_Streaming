import sys
from tkinter import Tk
from Client import Client
from Extend import Extend
if __name__ == "__main__":
	try:
		serverAddr = sys.argv[1]
		serverPort = sys.argv[2]
		rtpPort = sys.argv[3]
		fileName = sys.argv[4]	
	except:
		print("[Usage: ClientLauncher.py Server_name Server_port RTP_port Video_file]\n")	
	

	# Create a new client
	print('Version 1')
	print('Version 2 (Extend)')
	while True:
		INPUT = int(input('Your choice (1) or (2): '))
		if(INPUT == 1 ):
			root = Tk()
			app = Client(root, serverAddr, serverPort, rtpPort, fileName)
			break
		elif(INPUT == 2):
			root = Tk()
			app = Extend(root, serverAddr, serverPort, rtpPort, fileName)
			break

		else:
			print('Enter again (1) or (2):')
	app.master.title("RTPClient")
	app.master.configure(bg="#A5D2EB")
	root.mainloop()
	