from tkinter import *
import tkinter.messagebox
from PIL import Image, ImageTk
import socket
import threading
import sys
import traceback
import os
import datetime
from RtpPacket import RtpPacket
import time

CACHE_FILE_NAME = "cache-"
CACHE_FILE_EXT = ".jpg"


class Extend:
    INIT = 0
    READY = 1
    PLAYING = 2
    state = INIT

    SETUP = 0
    PLAY = 1
    PAUSE = 2
    TEARDOWN = 3
    DESCRIBE = 4
    FORWARD = 5
    PREV = 6

    flagSocket = False
    flagTeardown = False
    lostCounter = 0

    # Initiation..
    def __init__(self, master, serveraddr, serverport, rtpport, filename):
        self.master = master
        self.master.protocol("WM_DELETE_WINDOW", self.handler)
        self.createWidgets()
        self.serverAddr = serveraddr
        self.serverPort = int(serverport)
        self.rtpPort = int(rtpport)
        self.fileName = filename
        self.rtspSeq = 0
        self.sessionId = 0
        self.requestSent = -1
        self.teardownAcked = 0
        self.connectToServer()
        self.frameNbr = 0

        # new variables
        self.totalTime = 0
        self.currentTime = 0
        self.isSkip = 0
        # statistical data
        self.countTotalPacket = 0
        self.timerBegin = 0
        self.timerEnd = 0
        self.timer = 0
        self.bytes = 0
        self.packetsLost = 0
        self.lastSequence = 0
        self.totalJitter = 0
        self.arrivalTimeofPreviousPacket = 0
        self.lastPacketSpacing = 0

    def createWidgets(self):
        """Build GUI."""
        # Create Play button
        self.start = Button(self.master, width=15, padx=3, pady=3)
        self.start["text"] = "▶️"
        self.start["fg"] = "black"
        self.start["command"] = self.playMovie
        self.start.grid(row=2, column=0, padx=2, pady=2)

        # Create Pause button
        self.pause = Button(self.master, width=15, padx=3, pady=3)
        self.pause["text"] = "⏸"
        self.pause["fg"] = "black"
        self.pause["command"] = self.pauseMovie
        self.pause.grid(row=2, column=1, padx=2, pady=2)

        # Create Teardown button
        self.stop = Button(self.master, width=15, padx=3, pady=3)
        self.stop["text"] = "⏹"
        self.stop["command"] = self.resetMovie
        self.stop["fg"] = "black"
        self.stop["state"] = "disabled"
        self.stop.grid(row=2, column=2, padx=2, pady=2)

        # Create Describe button
        self.describe = Button(self.master, width=15, padx=3, pady=3)
        self.describe["text"] = "⚙️"
        self.describe["command"] = self.describeMovie
        self.describe["fg"] = "black"
        self.describe["state"] = "disabled"
        self.describe.grid(row=2, column=3, padx=2, pady=2)

        # Create forward button
        self.forward = Button(self.master, width=15, padx=3, pady=3, fg="black")
        self.forward["text"] = "⏩"
        self.forward["command"] = self.forwardMovies
        self.forward["state"] = "disabled"
        self.forward.grid(row=1, column=2, padx=2, sticky=E + W, pady=2)

        # Create backward button
        self.backward = Button(self.master, width=15, padx=3, pady=3, fg="black")
        self.backward["text"] = "⏪"
        self.backward["command"] = self.prevMovie
        self.backward["state"] = "disabled"
        self.backward.grid(row=1, column=1, sticky=E + W, padx=2, pady=2)

        # Create a label to display the movie
        self.label = Label(self.master, height=18)
        self.label.grid(row=0, column=0, columnspan=5, sticky=W + E + N + S, padx=5, pady=5)

        # Create a label to display total time of the movie
        self.totaltimeBox = Label(
            self.master, width=16, text="Total time: 00:00", bg="#A5D2EB")
        self.totaltimeBox.grid(row=1, column=3, columnspan=1, padx=5, pady=5)

        # Create a label to display remaining time of the movie

        self.remainTimeBox = Label(
            self.master, width=16, text="Remaining time: 00:00", bg="#A5D2EB")
        self.remainTimeBox.grid(row=1, column=0, columnspan=1, padx=5, pady=5)

    def describeMovie(self):
        """Describe button handler"""
        self.sendRtspRequest(self.DESCRIBE)

    def setupMovie(self):
        """Setup button handler."""
        if self.state == self.INIT:
            self.sendRtspRequest(self.SETUP)
            self.stop["state"] = "normal"

    def resetMovie(self):
        """Teardown button handler."""
        if self.state != self.INIT:
            self.sendRtspRequest(self.TEARDOWN)
            try:
                for i in os.listdir():
                    if i.find(CACHE_FILE_NAME) == 0:
                        os.remove(i)
            except:
                pass
            time.sleep(1)
            self.forward["state"] = "disabled"
            self.backward["state"] = "disabled"
            self.stop["state"] = "disabled"

            self.rtspSeq = 0
            self.sessionId = 0
            self.requestSent = -1
            self.teardownAcked = 0
            self.frameNbr = 0
            self.lostCounter = 0

            self.isSkip = 0
            self.currentTime = 0

            self.flagTeardown = False
            self.connectToServer()
            self.rtpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.label.pack_forget()
            self.label.image = ''

    def pauseMovie(self):
        """Pause button handler."""
        if self.state == self.PLAYING:
            self.forward["state"] = "disabled"
            self.backward["state"] = "disabled"
            self.sendRtspRequest(self.PAUSE)

    def playMovie(self):
        """Play button handler."""
        if self.state == self.INIT:
            self.flagTeardown = True

            self.frameNbr = 0
            self.countTotalPacket = 0
            self.timerBegin = 0
            self.timerEnd = 0
            self.timer = 0
            self.bytes = 0
            self.packetsLost = 0
            self.lastSequence = 0
            self.totalJitter = 0
            self.arrivalTimeofPreviousPacket = 0
            self.lastPacketSpacing = 0
            self.setupMovie()
            while self.state != self.READY:
                pass

        self.forward["state"] = "normal"
        self.backward["state"] = "normal"
        self.describe["state"] = "normal"

        if self.state == self.READY:
            self.flagTeardown = True
            # Create a new thread to listen for RTP packets
            threading.Thread(target=self.listenRtp).start()
            self.playEvent = threading.Event()
            self.playEvent.clear()
            self.sendRtspRequest(self.PLAY)

    def forwardMovies(self):
        self.sendRtspRequest(self.FORWARD)
        self.isSkip = 1

    def prevMovie(self):
        self.sendRtspRequest(self.PREV)
        if self.frameNbr <= 50:
            self.frameNbr = 0
        else:
            self.frameNbr -= 50
        self.isSkip = 1

    def listenRtp(self):
        """Listen for RTP packets."""
        while True:
            try:
                data = self.rtpSocket.recv(20480)
                if data:
                    rtpPacket = RtpPacket()
                    rtpPacket.decode(data)

                    arrivalTimeOfPacket = time.perf_counter()
                    print("Current Seq Num: " + str(rtpPacket.seqNum()))
                    self.bytes += len(rtpPacket.getPacket())
                    try:
                        if (self.frameNbr + 1 != rtpPacket.seqNum()) & (not (self.isSkip)):
                            print('count: ', self.lostCounter)
                            self.lostCounter += 1
                            print('=' * 100 + "\n\nPacket Lost\n\n" + '=' * 100)

                        currFrameNbr = rtpPacket.seqNum()
                        self.currentTime = int(currFrameNbr * 0.05)

                        # Update remaining time
                        self.totaltimeBox.configure(text="Total time: %02d:%02d" % (
                            self.totalTime // 60, self.totalTime % 60))
                        self.remainTimeBox.configure(text="Remaining time: %02d:%02d" % (
                            (self.totalTime - self.currentTime) // 60, (self.totalTime - self.currentTime) % 60))

                    except:
                        print("seqNum() Error \n")
                        traceback.print_exc(file=sys.stdout)
                        print("\n")

                    if currFrameNbr > self.frameNbr:  # Discard the late packet
                        self.frameNbr = currFrameNbr
                        self.updateMovie(self.writeFrame(rtpPacket.getPayload()))
                        # statUpdate
                        self.countTotalPacket += 1
                        self.packetsLost += currFrameNbr - self.lastSequence - 1
                        # calculate total jitter
                        if self.lastSequence == currFrameNbr - 1 and currFrameNbr > 1:
                            interPacketSpacing = arrivalTimeOfPacket - self.arrivalTimeofPreviousPacket
                            jitterIncrement = abs(
                                interPacketSpacing - self.lastPacketSpacing)
                            self.totalJitter = self.totalJitter + jitterIncrement
                            self.lastPacketSpacing = interPacketSpacing

                        self.arrivalTimeofPreviousPacket = arrivalTimeOfPacket
                        self.lastSequence = currFrameNbr
            except:
                # Stop listening upon requesting PAUSE or TEARDOWN
                if self.playEvent.isSet():
                    self.statistic()
                    break

                # Upon receiving ACK for TEARDOWN request,
                # close the RTP socket
                if self.teardownAcked == 1:
                    self.statistic()
                    self.flagSocket = False
                    try:
                        self.rtpSocket.shutdown(socket.SHUT_RDWR)
                        self.rtpSocket.close()
                    except:
                        pass
                    break

    def writeFrame(self, data):
        """Write the received frame to a temp image file. Return the image file."""
        cachename = CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT
        file = open(cachename, "wb")
        file.write(data)
        file.close()
        return cachename

    def updateMovie(self, imageFile):
        """Update the image file as video frame in the GUI."""
        photo = ImageTk.PhotoImage(Image.open(imageFile))
        self.label.configure(image=photo, height=288)
        self.label.image = photo

    def connectToServer(self):
        """Connect to the Server. Start a new RTSP/TCP session."""
        self.flagSocket = True
        self.rtspSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.rtspSocket.connect((self.serverAddr, self.serverPort))
        except:
            tkinter.messagebox.showwarning(
                'Connection Failed', 'Connection to \'%s\' failed.' % self.serverAddr)

    def sendRtspRequest(self, requestCode):
        """Send RTSP request to the server."""
        # -------------
        # TO COMPLETE
        # -------------
        # Setup request
        if requestCode == self.SETUP:
            threading.Thread(target=self.recvRtspReply).start()
            # Update RTSP sequence number.
            # ...
            self.rtspSeq = self.rtspSeq + 1
            # Write the RTSP request to be sent.
            # request = ...
            request = "SETUP %s RTSP/1.0\nCSeq: %d\nTRANSPORT: RTP/UDP; Client_port= %d" % (
                self.fileName, self.rtspSeq, self.rtpPort)

            # Keep track of the sent request.
            # self.requestSent = ...
            self.requestSent = self.SETUP
        # Play request
        elif requestCode == self.PLAY:
            # Update RTSP sequence number.
            # ...
            self.rtspSeq = self.rtspSeq + 1
            # Write the RTSP request to be sent.
            # request = ...
            request = "PLAY %s RTSP/1.0\nCSeq: %d\nSESSION: %d" % (
                self.fileName, self.rtspSeq, self.sessionId)
            # Keep track of the sent request.
            # self.requestSent = ...
            self.requestSent = self.PLAY
        # Pause request
        elif requestCode == self.PAUSE:
            # Update RTSP sequence number.
            # ...
            self.rtspSeq = self.rtspSeq + 1
            # Write the RTSP request to be sent.
            # request = ...
            request = "PAUSE %s RTSP/1.0\nCSeq: %d\nSESSION: %d" % (
                self.fileName, self.rtspSeq, self.sessionId)
            # Keep track of the sent request.
            # self.requestSent = ...
            self.requestSent = self.PAUSE
        # Teardown request
        elif requestCode == self.TEARDOWN:
            # Update RTSP sequence number.
            # ...
            self.rtspSeq = self.rtspSeq + 1
            # Write the RTSP request to be sent.
            # request = ...
            request = "TEARDOWN %s RTSP/1.0\nCSeq: %d\nSESSION: %d" % (
                self.fileName, self.rtspSeq, self.sessionId)

            # Keep track of the sent request.
            # self.requestSent = ...
            self.requestSent = self.TEARDOWN
        elif requestCode == self.DESCRIBE:
            self.rtspSeq = self.rtspSeq + 1
            request = "DESCRIBE %s RTSP/1.0\nCSeq: %d\nSESSION: %d" % (
                self.fileName, self.rtspSeq, self.sessionId)
            self.requestSent = self.DESCRIBE

        elif requestCode == self.FORWARD:
            # Update RTSP sequence number.
            # ...
            self.rtspSeq = self.rtspSeq + 1
            # Write the RTSP request to be sent.
            # request = ...
            request = "FORWARD %s RTSP/1.0\nCSeq: %d\nSESSION: %d" % (
                self.fileName, self.rtspSeq, self.sessionId)
            # Keep track of the sent request.
            # self.requestSent = ...
            self.requestSent = self.FORWARD

        elif requestCode == self.PREV:
            # Update RTSP sequence number.
            # ...
            self.rtspSeq = self.rtspSeq + 1
            # Write the RTSP request to be sent.
            # request = ...
            request = "PREVIOUS %s RTSP/1.0\nCSeq: %d\nSESSION: %d" % (
                self.fileName, self.rtspSeq, self.sessionId)
            # Keep track of the sent request.
            # self.requestSent = ...
            self.requestSent = self.PREV

        else:
            return

        # Send the RTSP request using rtspSocket.
        # ...
        self.rtspSocket.send(request.encode())
        print('\nData sent:\n' + request)

    def recvRtspReply(self):
        """Receive RTSP reply from the server."""
        while True:
            reply = self.rtspSocket.recv(1024)

            if reply:
                self.parseRtspReply(reply.decode("utf-8"))

            # Close the RTSP socket upon requesting Teardown
            if self.requestSent == self.TEARDOWN:
                self.rtspSocket.shutdown(socket.SHUT_RDWR)
                self.rtspSocket.close()
                break

    def parseRtspReply(self, data):
        """Parse the RTSP reply from the server."""
        lines = data.split('\n')
        seqNum = int(lines[1].split(' ')[1])

        # Process only if the server reply's sequence number is the same as the request's
        if seqNum == self.rtspSeq:
            session = int(lines[2].split(' ')[1])
            # New RTSP session ID
            if self.sessionId == 0:
                self.sessionId = session

            # Process only if the session ID is the same
            if self.sessionId == session:
                if int(lines[0].split(' ')[1]) == 200:
                    if self.requestSent == self.SETUP:
                        # -------------
                        # TO COMPLETE
                        # -------------
                        # Update RTSP state.
                        # self.state = ...
                        self.totalTime = float(lines[3].split(' ')[1])
                        self.state = self.READY
                        # Open RTP port.
                        self.openRtpPort()
                    elif self.requestSent == self.PLAY:
                        # self.state = ...
                        self.state = self.PLAYING
                        # start timer if it is not already playing
                        if self.timerBegin == 0:
                            self.timerBegin = time.perf_counter()
                            self.arrivalTimeofPreviousPacket = time.perf_counter()
                    elif self.requestSent == self.PAUSE:
                        # self.state = ...
                        self.state = self.READY
                        # set timer when paused and playing previously
                        if self.timerBegin > 0:
                            self.timerEnd = time.perf_counter()
                            self.timer += self.timerEnd - self.timerBegin
                            self.timerBegin = 0
                        # The play thread exits. A new thread is created on resume.
                        self.playEvent.set()
                    elif self.requestSent == self.TEARDOWN:
                        # self.state = ...
                        self.state = self.INIT
                        self.timerEnd = time.perf_counter()
                        # end timer
                        self.timer += self.timerEnd - self.timerBegin
                        # Flag the teardownAcked to close the socket.
                        self.teardownAcked = 1

                    elif self.requestSent == self.DESCRIBE:
                        # self.state = ...
                        self.description(lines)

    def openRtpPort(self):
        """Open RTP socket binded to a specified port."""
        # -------------
        # TO COMPLETE
        # -------------
        # Create a new datagram socket to receive RTP packets from the server
        # self.rtpSocket = ...
        self.rtpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Set the timeout value of the socket to 0.5sec
        # ...
        self.rtpSocket.settimeout(0.5)
        try:
            # Bind the socket to the address using the RTP port given by the client user
            self.rtpSocket.bind(('', self.rtpPort))
            self.flagSocket = True
            self.state = self.READY
        except socket.error as err:
            tkinter.messagebox.showwarning(
                'Unable to Bind', 'Unable to bind PORT=%d: %s' % (self.rtpPort, err))
            self.flagSocket = False
            self.state = self.INIT

    def handler(self):
        """Handler on explicitly closing the GUI window."""
        self.pauseMovie()
        if tkinter.messagebox.askokcancel("Quit?", "Are you sure you want to quit?"):
            if self.state != self.INIT:
                self.sendRtspRequest(self.TEARDOWN)
            if (self.flagSocket):
                self.rtpSocket.shutdown(socket.SHUT_RDWR)
                self.rtpSocket.close()
            self.master.destroy()
            sys.exit(0)

    def description(self, lines):
        """Displays the description of the movie."""
        # Toplevel() will create a new window to display the description.
        top = Toplevel()
        top.title("Description")
        # The size of the description window.
        top.geometry('300x180')
        # Create a listbox to display the description.
        descrip = Listbox(top, width=50, height=30)
        # the first argument is the index of the line to be inserted, the second argument is the content of the line.
        descrip.insert(1, "Describe: ")
        descrip.insert(2, "Name Video: " + str(self.fileName))
        for i in range(3, len(lines)):
            descrip.insert(i, lines[i])
        descrip.insert(11, "Current time: " + "%02d:%02d" %
                       (self.currentTime // 60, self.currentTime % 60))
        # Pack is used to organize widgets in blocks before placing them in the parent widget.
        descrip.pack()

    def statistic(self):
        """Displays observed statistics"""
        top = Toplevel()
        top.title("Statistics")
        top.geometry('300x170')
        stats = Listbox(top, width=80, height=20)
        stats.insert(1, "Current Packets is: %d " % self.frameNbr)
        stats.insert(2, "Total Packets: %d packets" % self.countTotalPacket)
        stats.insert(3, "Packet Loss Rate: %d%%" % (((self.lostCounter) / (self.countTotalPacket)) * 100))
        stats.insert(4, "Play time: %.2f seconds" % self.timer)
        stats.insert(5, "Bytes received: %d bytes" % self.bytes)
        stats.insert(6, "Video Data Rate: %d bytes per second" % (self.bytes / self.timer))
        stats.insert(7, "Average Jitter: %.3fms" % ((self.totalJitter / self.countTotalPacket) * 1000))
        stats.pack()