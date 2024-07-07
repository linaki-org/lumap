import tkinter as tk
from PIL import ImageTk, Image
import cv2
from time import sleep
import pygame
import pickle
from tkinter.simpledialog import askinteger
from tkinter.filedialog import askopenfilename, asksaveasfilename
from tkinter.messagebox import askokcancel, showerror
from bottle import route, run, error
import pyautogui as gui
import threading
import copy

# import player
WIDTH = 1920
HEIGHT = 1080
VIDEO = "vid"
AUDIO = "aud"
IMG = "img"
STOP = "stp"
FADEIN = "fin"
FADEOUT = "fou"
MASK = -1
DEFAULTPREFS = {VIDEO: {"surface": 0, "file": None},
                AUDIO: {"interface": 0, "file": None},
                IMG: {"surface": 0, "file": None},
                STOP: {"target": None},
                FADEIN: {"target": None, "duration": 2},
                FADEOUT: {"target": None, "duration": 2}}

DEFAULTNAMES = {VIDEO: "Undefined video file",
                AUDIO: "Undefined audio file",
                IMG: "Undefined image file",
                STOP: "Stop (undefined target)",
                FADEIN: "Fade in (undefined target)",
                FADEOUT: "Fade out (undefined target)"}
pygame.init()
playerTimer = None
isReading = False
cueCaps = []
surfaces = [(0, 0, WIDTH, HEIGHT, "Full screen")]
players = []
mask = None


class Server(threading.Thread):
    def __init__(self, host):
        threading.Thread.__init__(self)
        self.host = host

    def run(self):
        run(host=self.host, port="8080")


class Video:
    def __init__(self, file, pos):
        print(file)
        self.capture = cv2.VideoCapture(file)
        self.pos = pos
        _, frame = self.capture.read()
        cv2image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
        img = Image.fromarray(cv2image)
        img = img.resize((pos[2], pos[3]))
        self.img = ImageTk.PhotoImage(image=img)
        self.frame = playCan.create_image(pos[0], pos[1], anchor="nw", image=self.img)

    def update(self):
        _, frame = self.capture.read()
        cv2image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
        img = Image.fromarray(cv2image)
        img = img.resize((self.pos[2], self.pos[3]))
        self.img = ImageTk.PhotoImage(image=img)
        playCan.itemconfig(self.frame, image=self.img)


class Img:
    def __init__(self, file, pos, isMask=0):
        img = Image.open(file)
        img = img.resize((pos[2], pos[3]))
        self.img = ImageTk.PhotoImage(image=img)
        self.pos = pos
        self.frame = playCan.create_image(pos[0], pos[1], anchor="nw", image=self.img)
        self.isMask = isMask
        self.players = copy.copy(players)

    def update(self):
        if self.isMask:
            if players != self.players:
                print("Updating video mask")
                self.players = copy.copy(players)
                playCan.delete(self.frame)
                self.frame = playCan.create_image(self.pos[0], self.pos[1], anchor="nw", image=self.img)


def goToCue(id):
    global actualCue
    actualCue = id


def saveList():
    filename = asksaveasfilename(initialdir="./projects", filetypes=[("Lumap cue lists", "*.luq")])
    if not filename.endswith(".luq"):
        filename += ".luq"
    file = open(filename, "wb")
    pickle.dump(cueList, file)
    file.close()


def loadList():
    global cueList, actualCue
    if askokcancel("Load cue list - Lumap",
                   "You are about to load a cue list. All unsaved work in the actual cue list will be lost. Are you sure you want to continue ?"):
        filename = askopenfilename(initialdir="./projects", filetypes=[("Lumap cue lists", "*.luq")])
        file = open(filename, "rb")
        cueList = pickle.load(file)
        file.close()
        drawCueList()
        actualCue = -1


def drawCueList():
    cueBox.delete(0, tk.END)
    if not cueList:
        cueBox.insert(0, "No elements in cue list.")
    for pos, cue in enumerate(cueList):
        cueBox.insert(pos, str(pos) + " - " + cue[2])


def newFileCue():
    pos = askinteger("New cue - Lumap", "Enter position for new cue (cue will created above)")
    file = askopenfilename()
    if file.endswith(".mp4") or file.endswith(".avi") or file.endswith(".mkv"):
        cueList.insert(pos, (VIDEO, (file, 0), file.split("/")[-1],))
    if file.endswith(".wav") or file.endswith(".mp3") or file.endswith(".ogg"):
        cueList.insert(pos, (AUDIO, (file, 0), file.split("/")[-1]))
    if file.endswith(".jpg") or file.endswith(".png") or file.endswith(".gif"):
        cueList.insert(pos, (IMG, (file, MASK), file.split("/")[-1]))
    drawCueList()


def newCue(type):
    pos = askinteger("New cue - Lumap", "Enter position for new cue (cue will created above)")
    cueList.insert(pos, (type, DEFAULTPREFS[type], DEFAULTNAMES[type]))
    drawCueList()


def startServer(e=None):
    @error(500)
    def serverError(e=None):
        return "<h1>Error 500</h1>" + serverIndex()

    @route("/")
    def serverIndex():
        return "<h1>" + str(actualCue) + " : " + str(cueList[actualCue][1]) + "</h1><br><h1>" + str(
            cueList[actualCue + 1][
                1]) + ("<a href='/next'><button style='height: 1000px;width:1000px;font-size:5em'>Go "
                       "!</button></a><br><a href='/repeat'><button style='height: "
                       "300px;width:300px;font-size:2em'>Repeat cue</button></a><a href='/goto0'><button "
                       "style='height: 300px;width:300px;font-size:2em'>Go to cue -1</button></a>"
                       "<a href='/last'><button style='height: 300px;width:300px;font-size:2em'>Last cue</button></a>")

    @route("/next")
    def serverNextCue():
        gui.press("space")
        return serverIndex()

    @route("/repeat")
    def serverRepeatCue():
        global actualCue
        actualCue -= 1
        gui.press("space")
        return serverIndex()

    @route("/goto0")
    def serverGoToCue0():
        global actualCue
        actualCue = -1
        return serverIndex()

    @route("/last")
    def serverLastCue():
        global actualCue
        actualCue -= 2
        gui.press("space")
        return serverIndex()

    server = Server("192.168.1.26")
    server.start()


def fullscreen():
    playWin.attributes("-fullscreen", True)


def play(file):
    # videoplayer.pause()
    videoplayer.load(r"videos\\" + file)
    sleep(0.1)
    print("loaded !")
    videoplayer.play()
    print("played !")

    if actualCue == 0:
        playWin.mainloop()
        pass


def video_stream():
    global playTimer
    mask = None
    for player in players:
        if type(player) == Image and player.isMask:
            mask = player
        else:
            player.update()
        # playCan.itemconfig(playerId, image=imgtk)
    if mask:
        mask.update()
    try:
        playCan.update()
    except NameError:
        showerror("Error - Lumap", "Video environnement is not running")
    playTimer = playCan.after(1, video_stream)


def execCue(cue):
    global isReading, videoMainloop
    """if videoEnv and not videoMainloop:
        playWin.mainloop()
        videoMainloop=True"""
    if cue[0] == VIDEO:
        if not isReading:
            video_stream()
            isReading = True
        video = Video(cue[1]["file"], surfaces[cue[1]["surface"]])
        players.append(video)
        video.update()
        if type(players[0]) == Img and players[0].isMask:
            players[0].update()
        playWin.update()

        print("go")

    elif cue[0] == AUDIO:
        pygame.mixer.music.load(cue[1][0])
        pygame.mixer.music.play()

    elif cue[0] == IMG:
        """if cue[1][1] == MASK:
            img = Img(cueList[actualCue][1][0], (0, 0, 1920, 1080), True)
        else:"""
        img = Img(cue[1][0], surfaces[cue[2][0]])
        players.append(img)
    """elif cue[0] == AUDIOSTOP:
        pygame.mixer.music.stop()
    elif cue[0] == AUDIOOUT:
        pygame.mixer.music.fadeout(cue[2][0])"""
    """elif cueList[actualCue][0] == AUTOPLAY:
        nextCue()"""
    """try:
        if cueList[actualCue + 1][0] == AUTOPLAY:
            nextCue()
    except:
        pass"""


def nextCue(e=None):
    global actualCue, videoplayer, cap, isReading
    actualCue += 1
    try:
        actualCueLab.configure(
            text="Actual cue : " + str(actualCue) + " (" + cueList[actualCue][2] + ")")
    except IndexError:
        actualCue = -1
        return
    except:
        pass
    cueWin.update()
    execCue(cueList[actualCue])

def genSurfaceModif(index):
    return lambda: editSurface(index)

def editSurface(index):
    surface=surfaces[index]
    tk.Label(surWin, text=surface[4]).pack()
    tk.Label(surWin, text="X : "+str(surface[0])).pack()
    tk.Label(surWin, text="Y : " + str(surface[1])).pack()
    tk.Label(surWin, text="WIDTH : " + str(surface[2])).pack()
    tk.Label(surWin, text="HEIGHT : " + str(surface[3])).pack()

def editSurfaces():
    global surWin
    surWin=tk.Toplevel()
    for index, surface in enumerate(surfaces):
        tk.Button(surWin, text=surface[4], command=genSurfaceModif(index)).pack()


def startPlayer():
    global playWin, playCan, videoEnv
    playWin = tk.Toplevel()
    playWin["bg"] = "black"
    playCan = tk.Canvas(playWin, height=1080, width=1920)
    # playerId = playCan.create_image(0, 0, anchor="nw")
    playCan.pack()
    playWin.bind("<space>", nextCue)
    videoEnv = True
    videomask = Img(mask, (0, 0, WIDTH, HEIGHT), True)
    players.append(videomask)
    playWin.mainloop()


cueList = []
actualCue = -1
imgReferences = []
videoplayer = None

cueWin = tk.Tk()
cueBox = tk.Listbox(cueWin, width=300, height=30, background="black", foreground="white")
actualCueLab = tk.Label(cueWin, text="Actual cue : -1 (virtual cue)")
actualCueLab.pack()
drawCueList()
cueBox.pack()
tk.Button(cueWin, text="New file cue", command=newFileCue).pack()
# tk.Button(cueWin, text="New camera cue", command=).pack()
tk.Button(cueWin, text="New stop cue", command=lambda: newCue(STOP)).pack()
tk.Button(cueWin, text="New fade out cue", command=lambda: newCue(FADEOUT)).pack()
tk.Button(cueWin, text="New fade in cue", command=lambda: newCue(FADEIN)).pack()
# tk.Button(cueWin, text="New autoplay cue", command=newAutoPlay).pack()
tk.Button(cueWin, text="Fullscreen player", command=fullscreen).pack()
# tk.Button(cueWin, text="New lighting cue", command=newFileCue).pack()
tk.Button(cueWin, text="Save cue list", command=saveList).pack()
tk.Button(cueWin, text="Load cue list", command=loadList).pack()
tk.Button(cueWin, text="Go to cue -1", command=lambda: goToCue(-1)).pack()
tk.Button(cueWin, text="Edit surfaces", command=editSurfaces).pack()
tk.Button(cueWin, text="Start remote server", command=startServer).pack()
tk.Button(cueWin, text="Start video Environement", command=startPlayer).pack()
cueWin.bind("<space>", nextCue)

videoEnv = False
videoMainloop = False

# cueWin.event_add("<<NextCue>>", '<space>')
# cueWin.bind("<<NextCue>>", nextCue)


cueWin.mainloop()
