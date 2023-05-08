class VideoStream:

    def __init__(self, filename):
        self.filename = filename
        try:
            self.file = open(filename, 'rb')
        except:
            raise IOError

        self.frameNum = 0		# current frame
        self.totalFrame = 0		# total frames

        # calc total frames
        while True:
            data = self.file.read(5)
            if data:
                framelength = int(data)
                # Read the current frame
                data = self.file.read(framelength)
                self.totalFrame += 1
            else:
                self.file.seek(0)
                break

    def get_total_time(self):
        return self.totalFrame * 0.05

    def nextFrame(self, fastForward=0):
        """Get next frame, if ff=1 then fast forward FORWARD, if ff=2 then fast forward PREV"""

        # no fast forward
        if fastForward == 0:
            nFrames = 1

        # fast forward FORWARD
        elif fastForward == 1:
            # nFrames is the number of frames need to forward
            nFrames = 50
            # check if at the end of video
            if nFrames > self.totalFrame - self.frameNum:
                nFrames = self.totalFrame - self.frameNum
            print("nFrames: "+str(nFrames))
            print("totalFrame: "+str(self.totalFrame))

        # fast forward PREV
        elif fastForward == 2:
            # nFrames is the number of frames need to backward (=0 if backward to the start of video)
            nFrames = 50
            # check if at the start of video
            if self.frameNum <= nFrames:
                nFrames = 0

            # back from the start
            data = self.file.seek(0)
            nFrames = -nFrames		# set to negative
            print("nFrames: "+str(nFrames))
            print("totalFrame: "+str(self.totalFrame))

        targetFrame = self.frameNum + nFrames
        if targetFrame > self.totalFrame:
            targetFrame = self.totalFrame

        # back from the start (only if fast forward PREV)
        if nFrames <= 0 and fastForward == 2:
            self.frameNum = 0
            if nFrames == 0:
                targetFrame = 1

        # -------------------------------- #
        # 		start reading file		   #
        # -------------------------------- #
        data = bytes(0)
        for i in range(self.frameNum, targetFrame):
            data = self.file.read(5)
            if data:
                framelength = int(data)

                # Read the current frame
                data = self.file.read(framelength)
                self.frameNum += 1

        return data

    def frameNbr(self):
        """Get frame number."""
        return self.frameNum
