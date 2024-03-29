from random import randint
import sys
import traceback
import threading
import socket
from tkinter import *
from VideoStream import VideoStream
from RtpPacket import RtpPacket

MJPEG_PAYLOAD_TYPE = 26


class ServerWorker:
    SETUP = 'SETUP'
    PLAY = 'PLAY'
    PAUSE = 'PAUSE'
    TEARDOWN = 'TEARDOWN'

    DESCRIBE = 'DESCRIBE'
    FORWARD = 'FORWARD'
    PREV = 'PREVIOUS'

    INIT = 0
    READY = 1
    PLAYING = 2
    state = INIT

    OK_200 = 0
    FILE_NOT_FOUND_404 = 1
    CON_ERR_500 = 2

    clientInfo = {}

    def __init__(self, clientInfo):
        self.clientInfo = clientInfo

        # 0 when not choosing to ff
        # 1 when ff FORWARD
        # 2 when ff BACKWARD
        self.fastForward = 0

    def run(self):
        threading.Thread(target=self.recvRtspRequest).start()

    def recvRtspRequest(self):
        """Receive RTSP request from the client."""
        connSocket = self.clientInfo['rtspSocket'][0]
        while True:
            data = connSocket.recv(256)
            if data:
                print("Data received:\n" + data.decode("utf-8"))
                self.processRtspRequest(data.decode("utf-8"))

    def processRtspRequest(self, data):
        """Process RTSP request sent from the client."""
        # Get the request type
        request = data.split('\n')
        line1 = request[0].split(' ')
        requestType = line1[0]

        # Get the media file name
        filename = line1[1]

        # Get the RTSP sequence number
        seq = request[1].split(' ')

        # Process SETUP request
        if requestType == self.SETUP:
            if self.state == self.INIT:
                # Update state
                print("processing SETUP\n")

                try:
                    self.clientInfo['videoStream'] = VideoStream(filename)
                    self.state = self.READY
                except IOError:
                    self.replyRtsp(self.FILE_NOT_FOUND_404, seq[1])

                # Generate a randomized RTSP session ID
                self.clientInfo['session'] = randint(100000, 999999)

                # Send RTSP reply
                self.replySetup(self.OK_200, seq[1])

                # Get the RTP/UDP port from the last line
                self.clientInfo['rtpPort'] = request[2].split(' ')[3]

                print(request[2].split(' '))
                print('End SETUP')

        # Process PLAY request
        elif requestType == self.PLAY:
            if self.state == self.READY:
                print("processing PLAY\n")
                self.state = self.PLAYING

                # Create a new socket for RTP/UDP
                self.clientInfo["rtpSocket"] = socket.socket(
                    socket.AF_INET, socket.SOCK_DGRAM)
                self.replyRtsp(self.OK_200, seq[1])

                # Create a new thread and start sending RTP packets
                self.clientInfo['event'] = threading.Event()
                self.clientInfo['worker'] = threading.Thread(
                    target=self.sendRtp)
                self.clientInfo['worker'].start()

        # Process PAUSE request
        elif requestType == self.PAUSE:
            if self.state == self.PLAYING:
                print("processing PAUSE\n")
                self.state = self.READY

                self.clientInfo['event'].set()

                self.replyRtsp(self.OK_200, seq[1])

        # Process TEARDOWN request
        elif requestType == self.TEARDOWN:
            print("processing TEARDOWN\n")

            self.clientInfo['event'].set()

            self.replyRtsp(self.OK_200, seq[1])

            # Close the RTP socket
            self.clientInfo['rtpSocket'].close()

        elif requestType == self.FORWARD:
            if self.state == self.PLAYING:
                print("processing FORWARD\n")
                self.fastForward = 1
                self.replyRtsp(self.OK_200, seq[1])

        elif requestType == self.PREV:
            if self.state == self.PLAYING:
                print("processing PREV\n")
                self.fastForward = 2
                self.replyRtsp(self.OK_200, seq[1])

        elif requestType == self.DESCRIBE:
            if self.state != self.INIT:
                print("processing DESCRIBE\n")
                # try :
                # 	self.clientInfo['event'].set()
                # except: pass
                self.replyDescribe(self.OK_200, seq[1], filename)

    def sendRtp(self):
        """Send RTP packets over UDP."""
        while True:
            self.clientInfo['event'].wait(0.05)

            # Stop sending if request is PAUSE or TEARDOWN
            if self.clientInfo['event'].isSet():
                break

            data = self.clientInfo['videoStream'].nextFrame(self.fastForward)
            self.fastForward = 0

            if data:
                frameNumber = self.clientInfo['videoStream'].frameNbr()
                try:
                    address = self.clientInfo['rtspSocket'][1][0]
                    port = int(self.clientInfo['rtpPort'])
                    self.clientInfo['rtpSocket'].sendto(
                        self.makeRtp(data, frameNumber), (address, port))
                except:
                    print("Connection Error")

    def makeRtp(self, payload, frameNbr):
        """RTP-packetize the video data."""
        version = 2 			# curr version of rtp packet
        padding = 0 			# normaly set to 0
        extension = 0
        cc = 0
        marker = 0
        pt = MJPEG_PAYLOAD_TYPE
        seqnum = frameNbr
        ssrc = 0

        rtpPacket = RtpPacket()
        rtpPacket.encode(version, padding, extension, cc,
                         seqnum, marker, pt, ssrc, payload)
        return rtpPacket.getPacket()

    def replyRtsp(self, code, seq):
        """Send RTSP reply to the client."""
        if code == self.OK_200:
            reply = 'RTSP/1.0 200 OK\nCSeq: ' + seq + \
                '\nSession: ' + str(self.clientInfo['session'])
            connSocket = self.clientInfo['rtspSocket'][0]
            connSocket.send(reply.encode())
        # Error messages
        elif code == self.FILE_NOT_FOUND_404:
            print("404 NOT FOUND")
        elif code == self.CON_ERR_500:
            print("500 CONNECTION ERROR")

    def replyDescribe(self, code, seq, filename):
        """Send RTSP Describe reply to the client."""
        if code == self.OK_200:
            # print("200 OK")
            myreply = 'RTSP/1.0 200 OK\nCSeq: ' + seq + \
                '\nSession: ' + str(self.clientInfo['session'])

            descriptionBody = "\nVersion = 2"
            descriptionBody += "\nVideo " + \
                self.clientInfo['rtpPort'] + \
                " RTP/AVP " + str(MJPEG_PAYLOAD_TYPE)
            descriptionBody += "\nControl: streamid =" + \
                str(self.clientInfo['session'])
            descriptionBody += "\nMimetype: video/MJPEG\""

            myreply += "\nContent-Base: " + filename
            myreply += "\nContent-Type: " + "application/sdp"
            myreply += descriptionBody
            connSocket = self.clientInfo['rtspSocket'][0]
            connSocket.send(myreply.encode())

    def replySetup(self, code, seq):
        """Send RTSP reply to the client."""
        if code == self.OK_200:
            totalTime = self.clientInfo['videoStream'].get_total_time()
            reply = 'RTSP/1.0 200 OK\nCSeq: ' + seq + '\nSession: ' + \
                str(self.clientInfo['session']) + \
                '\nTotalTime: ' + str(totalTime)
            connSocket = self.clientInfo['rtspSocket'][0]
            connSocket.send(reply.encode())
        # Error messages
        elif code == self.FILE_NOT_FOUND_404:
            print("404 NOT FOUND")
        elif code == self.CON_ERR_500:
            print("500 CONNECTION ERROR")
