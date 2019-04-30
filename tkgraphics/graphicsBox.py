
import cv2
import numpy as np
import os
import time
import tkinter as tk
import PIL.Image, PIL.ImageTk


################################################################################
class ImageBox(tk.Canvas):
    """create a frame that displays the desired image with supported effects"""
    HISTORY_SIZE = 100
    ############################################################################
    def __init__(self, parent, *images, imgMax=225, padding=0, bg="#000000",
            **effects):
        self.idx = 0
        self.images = []
        if isinstance(padding, (int, float)): # convert param into square dimensional parameters
            padding = [padding] * 2
        self.paddingX, self.paddingY = padding
        if isinstance(imgMax, (int, float)): #convert param into square dimensional parameters
            imgMax = [imgMax] * 2
        maxX, maxY = imgMax
        self.windowX = 1 # remember the previous window size to know if a resize event occurred
        self.windowY = 1
        self.bgColor = bg
        super(ImageBox, self).__init__(parent, width=maxX, height=maxY, bg=bg)
        self.pack()
        self._updateHistory = []
        self.addImgpath(*images)
        self.stopEffects()
        try:    self.update(**effects) # ensure that an image is drawn initially, even when no subsequent update() calls are made
        except IndexError: pass # can't display an image if no images are provided yet
    ############################################################################
    def __len__(self):
        return len(self.images)
    ############################################################################
    def __str__(self): return self.__repr__()
    def __repr__(self):
        if len(self) > 1:   imgStr = "%d images"%(len(self))
        elif self.images:   imgStr = list(self.images[0])[0]
        else:               imgStr = None
        if self.fps:        fpsStr = " %.1f fps"%(self.fps)
        else:               fpsStr = fpsStr = ""
        return "<%s %s%s>"%(self.__class__.__name__, imgStr, fpsStr)
    ############################################################################
    @property
    def fps(self):
        """calculate the number of updates() per second that invoked"""
        if not self._updateHistory: return 0
        start = self._updateHistory[0]
        end   = self._updateHistory[-1]
        try:    return len(self._updateHistory) / (end - start)
        except: return 0 # avoid divide-by-zero error
    ############################################################################
    @property
    def img(self):
        """apply all active effects to the raw image"""
        try:
            images = self.resize(self.idx)
        except:
            raise IndexError("There are noimages currently loaded in %s"%(self))
        imgName, cvImg = images[0]
        if self._imgPct < 1.0: # apply fade to the iamge whenever the image effect state is darkened at all
            x = [
                int(self.bgColor[1:3], 16),
                int(self.bgColor[3:5], 16),
                int(self.bgColor[5:7], 16),
            ]
            factor = sum(x) / len(x)
            # TODO -- fade to match the background color, not just black
            
            cvImg = (cvImg * self._imgPct).astype(np.uint8)
        return cvImg
    ############################################################################
    @property
    def isFading(self):
        return self._fadeInDur or self._fadeOutDur
    ############################################################################
    @property
    def isRotating(self):
        return bool(self._rotateDur)
    ############################################################################
    def addImgpath(self, *imageFilepaths):
        """add an image to the managed images within this ImageBox"""
        for name in imageFilepaths:
            absname = os.path.abspath(name)
            imgObj = cv2.imread(absname)
            imgTuple = (absname, imgObj)
            try:
                for i, (imgName, img) in enumerate(self.images):
                    if absname == imgName: # this same image was loaded previously
                        self.images[i] = imgTuple # update previously loaded image with the new image
                        raise Exception("") # don't append this image tuple because it was updated in place
            except: continue
            self.images.append(imgTuple)
    ############################################################################
    def advanceImage(self):
        """the next image in the list of managed images is selected"""
        self.idx += 1
        if self.idx >= len(self): # loop back around tothe first image
            self.idx = 0
    ############################################################################
    def removeImgpath(self, *imageFilepaths):
        """remove images from this ImageBox's managed images"""
        for name in imageFilepaths:
            absname = os.path.abspath(name)
            delIdx = None
            for i, (imgName, img) in enumerate(self.images):
                if absname == imgName: # this same image was loaded previously
                    delIdx = i
                    break
            if delIdx != None: # only succeds if img is found in managed images list
                del self.images[delIdx]
                if delIdx < self.idx:
                    self.idx -= 1 # when a previous image is removed, index is decremented to remain on the current image
    ############################################################################
    def resize(self, *idx):
        """ensure all managed images are sized appropriately to fill the """\
        """window as best as possible"""
        winX = self.winfo_width()
        winY = self.winfo_height()
        if idx: imgIter = [self.images[i] for i in idx] # select only the images that were specified
        elif self.windowX == winX and self.windowY == winY: return self.images # nothing worth doing
        else:   imgIter = self.images # select all images
        ret = []
        for imgName, img in imgIter:
            x, y, dim = img.shape
            scaleFactor = min(max(1, winX - self.paddingX) / x,
                              max(1, winY - self.paddingY) / y) # select the factor that takes the smallest scaled distnace from image edge to window edge
            newX = max(1, int(x * scaleFactor))
            newY = max(1, int(y * scaleFactor))
            #print("resize %s  %dx%d * >%.2f -> %dx%d"%(imgName, x, y, scaleFactor, newX, newY))
            newImg = cv2.resize(img, (newX, newY))
            ret.append((imgName, newImg))
        self.windowX = winX # retain for future resize comparison as well as center anchoring calculation
        self.windowY = winY
        return ret
    ############################################################################
    def startEffect(self,
            fadein      = None, # seconds until the image is fully faded in
           #fadeinout   = None, # seconds until the image is fully faded in and out
            fadeout     = None, # seconds until the image is fully faded out
           #fadeoutin   = None, # seconds until the image is fully faded out and in
            fadeCycle   = None, # seconds spent on each fade in and out cycle
            fadeDelay   = 0.0 , # seconds waiting before effect begins
            rotate      = None, # seconds until the nexst image is automatically selected (repeats)
            now         = None, # if timing is provided from elsewhere
            **kwargs          , # unhandled effects
        ):
        """force the active image to also apply specified effects"""
        if not now: now = time.time()
        if fadeCycle:
            self._fadeCycle = fadeCycle
            if self._fadeInDur: # adjust fade-in duration
                elapsed = now - self._fadeStart
                effectPct = elapsed / self._fadeInDur # the amount of effect that has completed
                self._fadeInDur = (1 - effectPct) * fadeCycle
                self._fadeStartPct = self._imgPct
                self.fadeStart = now
            elif self._fadeOutDur: # adjust fade-out duration
                elapsed = now - self._fadeStart
                effectPct = elapsed / self._fadeOutDur # the amount of the effect that has completed
                self._fadeOutDur = (1 - effectPct) * fadeCycle
                self._fadeStartPct = self._imgPct
                self._fadeStart = now
            elif not (fadein or fadeout):
                fadeout = float(fadeCycle) # ensure fadein or fadeout begin
        #elif fadeoutin: pass # TODO
        #elif fadeinout: pass # TODO
        if fadeDelay:
            self._fadeDelay = fadeDelay
        if fadein or fadeout:
            if fadein:
                if not self._fadeOutDur: # fade in starting point is the current fade percentage else fade in from black
                    self._imgPct = 0.0 # reset to black image
                self._fadeInDur  = fadein
                self._fadeOutDur = 0.0 # ensure any fadeout is stopped
            else:
                if not self._fadeInDur: # fade starting point is the current fade percentage else fade out from full image
                    self._imgPct = 1.0 # reset to full image
                self._fadeInDur  = 0.0 # ensure any fadein is stopped
                self._fadeOutDur = fadeout
            self._fadeStartPct = self._imgPct
            self._fadeStart = now + self._fadeDelay
        if rotate:
            self._rotateStart = now
            self._rotateDur = rotate
        if kwargs:
            msg  = ["received unhandled effects key/values"]
            msg += ["    %s : %s"%(k, v) for k, v in kwargs.items()]
            msg  = os.linesep.join(msg)
            raise ValueError(msg)
    ############################################################################
    def stopEffects(self):
        """immediately stop all effects"""
        self.stopFade()
        self.stopRotate()
    ############################################################################
    def stopFade(self):
        """immediately stop all fading with the image in its initial state"""
        self._fadeInDur     = 0.0 # number of seconds to fade the image in
        self._fadeOutDur    = 0.0 # number of seconds to fade the image out
        self._fadeStartPct  = 0.0 # the amount of fade that was present when the current began
        self._fadeStart     = 0.0 # when the current effect operationi began
        self._fadeCycle     = 0.0 # whether fading in/out should persist indefinitely
        self._fadeDelay     = 0.0 # the amount of time to wait before applying the fade effect
        self._imgPct        = 1.0 # the remaining percent of image after fade
    ############################################################################
    def stopRotate(self):
        """immediately stop all image rotation, resting on the current step"""
        self._rotateDur     = 0.0 # how long each image should be presented
        self._rotateStart   = 0.0 # whether the next type of fade should follow
    ############################################################################
    def update(self, **newEffects):
        """refresh the displayed image, including all desired effects"""
        now = time.time()
        self._updateHistory.append(now)
        self._updateHistory = self._updateHistory[:self.HISTORY_SIZE] # only allow a maximum HISTORY_SIZE number of entries into the history
        #print("updating %d%%"%(int(round(100*self._imgPct))))
        if newEffects:
            self.startEffect(**newEffects)
        if self._fadeInDur: # update the fade-in effect
            elapsed = now - self._fadeStart
            if elapsed > 0: # any delay has already been met
                effectPct = elapsed / self._fadeInDur # the amount of the effect that has completed
                valProgressed = (1.0 - self._fadeStartPct) * effectPct # the amount of percentage that is now covered
                self._imgPct = min(1.0, self._fadeStartPct + valProgressed) # calculate the next value in this effect's progress
                if effectPct > 1.0: # effect is now finished
                    if self._fadeCycle:
                          newNow = self._fadeStart + self._fadeCycle
                          self.startEffect(fadeout=self._fadeCycle, now=newNow) # start fade all over again
                    else: self._fadeInDur = 0.0 # ensure any fadein is stopped
        elif self._fadeOutDur: # update the fade-out effect
            elapsed = now - self._fadeStart
            if elapsed > 0: # any dleay has already been met
                effectPct = elapsed / self._fadeOutDur # the amount of the effect that has completed
                valProgressed = self._fadeStartPct * effectPct # the amount of percentage that is now covered
                self._imgPct = max(0.0, self._fadeStartPct - valProgressed) # calculate the next value in this effect
                if effectPct > 1.0: # effect is now finished
                    if self._fadeCycle:
                          newNow = self._fadeStart + self._fadeCycle
                          self.startEffect(fadein=self._fadeCycle, now=newNow) # start fade all over again
                    else: self._fadeOutDur = 0.0 # ensure any fadeout is stopped
        if self._rotateDur:
            elapsed = now - self._rotateStart
            if elapsed > self._rotateDur:
                self.advanceImage()
                self._rotateStart = self._rotateStart + self._rotateDur
        print("%.2f  %.2f  %.2f"%(self._fadeStart, self._rotateStart, self._fadeStart - self._rotateStart))
        cvImg = self.img # apply all calculated, updated effects
        self.photo = PIL.ImageTk.PhotoImage(image=PIL.Image.fromarray(cvImg))
        cx = self.winfo_width()  / 2.0
        cy = self.winfo_height() / 2.0
        self.create_image(cx, cy, image=self.photo, anchor=tk.CENTER) # update the canvas with the current image with effects applied


################################################################################
if __name__ == "__main__":
    ############################################################################
    def updateAll(*objs, rate=5):
        #start = time.time()
        for obj in objs:
            obj.update()
        #elapsed = time.time - start
        #delay = max(0, int(0.499999 + rate - elapsed)) # allow the delay to be adjusted to account for the time elapsed performing the effects
        delay = rate
        window.after(delay, updateAll, window, *objs)
    ############################################################################
    print("setup")
    window = tk.Tk()
    img = ImageBox(window,
        "C:\\Users\\jared\\code\\gitclones\\tkGraphics\\tkgraphics\\Mutagen_Sample.png",
        "C:\\Users\\jared\\code\\gitclones\\tkGraphics\\tkgraphics\\sample4_l.jpg",
        padding=(100,50), imgMax=800, fadein=1, fadeCycle=1, rotate=3, fadeDelay=0.5, bg="#FFFFFF")
    print("setup done")
    updateAll(window, img)
    window.mainloop()

