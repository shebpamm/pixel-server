from __future__ import division
import fastopc as opc
import time, os, sys, traceback
import numpy as np
#from logipy import logi_led
import colortools as ct
import threading
import jsonsocket, json
from timeit import default_timer as timer
from enum import Enum
from websocket_server import WebsocketServer


connection = opc.FastOPC()

class Effect(Enum):
    NONE = 'none'
    BREATHE = "breathe"
    GRADIENT = "gradient"
    RAINBOW = "rainbow"
    RAINBOW_GRADIENT = "rainbow_gradient"
    CYANIZE = "cyanize"

class Anim(Enum):
    NONE = 'none'
    BREATHE = 'breathe'
    ROLL = 'roll'

class wsLED:
    def __init__(self, channel, length, controller, speed=5, step=10):
        self.channel = channel
        self.length = length
        self.controller = controller
        self.transitionSpeed = speed
        self.animationSpeed = speed/4
        self.speed = speed
        self.step = step
        self.running = False
        self.interpolating = False
        self.targetPixels = np.array([ [0,0,0] ] * length)
        self.targetAnimPixels = np.array([ [0,0,0] ] * length)
        self.realPixels = np.array([ [0,0,0] ] * length)
        self.blackPixels = np.array([ [0,0,0] ] * length)
        self.brightlevel = 100
        self.isOn = False

        self.isAnimating = False
        self.animCycle = 0
        self.animMaxCycle = 1000
        self.animation = Anim.NONE

    def setOverride(self, state):

        print(type(state))

        if state == True:
            self.interpolating = False
        if state == False:
            self.interpolating = True

    def lightOn(self):
        self.disableAnimation()
        self.isOn = True

    def lightOff(self):
        self.disableAnimation()
        self.isOn = False

    def setState(self, state):
        if state == "on":
            self.lightOn()
        elif state == "off":
            self.lightOff()
        else: print("Channel {0}: Invalid state".format(self.channel))

    def setEffect(self, effect):
        if effect == 'cyanize':
            self.gradientPixels('37D5D6', 'ff00e8')
        if effect == 'beach':
            self.gradientPixels('4db6ac', 'ffb74d')
        if effect == 'rainbow':
            self.rainbowPixels()
        if effect == 'pastel-rainbow':
            self.rainbowPixels(saturation=0.4)
        if effect == 'rolling':
            self.setAnimation(Anim.ROLL)
        if effect == 'breathing':
            self.setAnimation(Anim.BREATHE)
        if effect == 'none':
            self.disableAnimation()

    def setAnimation(self, animation):
        self.isAnimating = True
        self.animation = animation
        self.speed = self.animationSpeed

    def disableAnimation(self):
        self.isAnimating = False
        self.animation = Anim.NONE
        self.speed = self.transitionSpeed

    def fillPixels(self, hex):
        self.disableAnimation()
        #Actually RBG LOL :D
        rgb = ct.hex_to_RGB(hex)
        #print(hex)
        rgb[1], rgb[2] = rgb[2], rgb[1]

        #print(rgb)

        if rgb == [0, 0, 0]:
            self.lightOff()
        else:
            self.lightOn()
            for i in range(0, self.length):
                self.targetPixels[i] = rgb
            #leds.put_pixels(self.realPixels, channel=self.channel)

    def gradientPixels(self, start_hex, end_hex, phase=0):
        self.disableAnimation()
        self.lightOn()
        self.targetPixels = ct.phase(ct.linear_gradient(self.targetPixels, start_hex, self.length, end_hex), phase)

    def triplePixels(self, colors):
        self.disableAnimation()
        self.lightOn()
        self.targetPixels = ct.triplecolor(self.targetPixels, colors, self.length)

    def rainbowPixels(self, phase=0, saturation=1):
        self.disableAnimation()
        self.lightOn()
        self.targetPixels = ct.rainbow(self.targetPixels, phase, self.length, saturation=saturation)

    def brightness(self, bright):
        self.disableAnimation()

        if bright == 0:
            self.lightOff()
        else:
            self.lightOn()
            self.brightlevel = bright

            for i in range(0, 64):
                hsv = ct.RGB_to_HSV(self.targetPixels[i])
                self.targetPixels[i] = ct.HSV_to_RGB((hsv[0], hsv[1], bright/100.0))



    def run(self):
        self.running = True
        self.interpolating = True
        self.thread = threading.Thread(target=self.interpolate)
        self.thread.daemon = True
        self.thread.start()

    def preProcessAnimations(self):
        if self.isAnimating:
            if self.animation == Anim.ROLL:
                self.targetPixels = np.roll(self.targetPixels, 1, axis=0)
            if self.animation == Anim.BREATHE:
                pass


    def process(self):
        processedPixels = self.targetPixels if self.isOn else self.blackPixels

        diff = processedPixels - self.realPixels
        self.realPixels = self.realPixels + self.step*np.divide(diff, np.abs(diff), out=np.zeros_like(diff), where=np.abs(diff)>=self.step )


    def interpolate(self):
        stats = []
        while self.running:
            if self.interpolating:

                start = timer()
                self.animCycle += 1

                self.preProcessAnimations()
                self.process()

                if self.animCycle == self.animMaxCycle:
                    self.animCycle = 0

                self.controller.putPixels(self.channel, self.realPixels)

                end = timer()

                stats.append(end - start)
                if(len(stats) == 500):
                    print(sum(stats) / 500)
            time.sleep(0.1/self.speed)

#TCP Stack


def handlePacket(data):
    try:
        data = json.loads(data)
        commandType = data['type']
        if commandType == 'fill':
            #{"type":"fill", "channel":1, "color" : "00ff00"}
            strips[data['channel']].fillPixels(data['color'])
            return True

        if commandType == 'state':
            #{"type":"state", "channel":1, "state" : "off"}
            strips[data['channel']].setState(data['state'])
            return True

        if commandType == 'gradient':
            #{"type":"gradient", "channel":1, "startcolor":"ff0000", "endcolor":"00ff00", "phase" : 0}
            strips[data['channel']].gradientPixels(data['startcolor'], data['endcolor'], data['phase'])
            return True

        if commandType == 'brightness':
            #{"type" : "brightness", "channel" : 1, "brightness" : 50}
            strips[data['channel']].brightness(int(data['brightness']))

        if commandType == 'triple':
            #{"type":"triple", "channel":1, "colorone":"ff0000", "colortwo":"00ff00", "colorthree":"0000ff"}
            strips[data['channel']].triplePixels((data['colorone'], data['colortwo'], data['colorthree']))
            return False

        if commandType == 'rainbow':
            #{"type":"rainbow", "channel":1, "phase" : "0"}
            strips[data['channel']].rainbowPixels(data['phase'])
            return True

        if commandType == 'override':
            #{"type":"override", "channel":1, "state" : true}
            strips[data['channel']].setOverride(data['state'])
            return True

        if commandType == 'effect':
            #{"type":"effect", "channel":1, "effect" : "breathe"}
            strips[data['channel']].setEffect(data['effect'])

        if commandType == 'query':
            #{"type":"query", "channel":1, "full" : false}

            if bool(data['full']) == False:
                return {
                    "self.channel" : strips[data['channel']].channel,
                    "self.length" : strips[data['channel']].length,
                    "self.speed" : strips[data['channel']].speed,
                    "self.step" : strips[data['channel']].step,
                    "self.interpolating" : strips[data['channel']].interpolating,
                    "self.brightlevel" : strips[data['channel']].brightlevel,
                    "self.isOn" : strips[data['channel']].isOn,
                    "self.effect" : str(strips[data['channel']].effect),
                    "self.effectLoopCount" : strips[data['channel']].effectLoopCount
                }
            else:
                return {
                    "self.channel" : strips[data['channel']].channel,
                    "self.length" : strips[data['channel']].length,
                    "self.speed" : strips[data['channel']].speed,
                    "self.step" : strips[data['channel']].step,
                    "self.interpolating" : strips[data['channel']].interpolating,
                    "self.targetPixels" : strips[data['channel']].targetPixels.tolist(),
                    "self.realPixels" : strips[data['channel']].realPixels.tolist(),
                    "self.blackPixels" : strips[data['channel']].blackPixels.tolist(),
                    "self.brightlevel" : strips[data['channel']].brightlevel,
                    "self.isOn" : strips[data['channel']].isOn,
                    "self.effect" : str(strips[data['channel']].effect),
                    "self.effectLoopCount" : strips[data['channel']].effectLoopCount,
                    "self.effectLoopCountMax" : strips[data['channel']].effectLoopCountMax
                }

    except Exception as e:
        print(traceback.format_exc())
        return False

def serveTCP(port=8989):

    host = '127.0.0.1'

    global server
    server = jsonsocket.Server(host, port)

    while True:
        server.accept()
        data = server.recv()
        result = handlePacket(data)
        server.send({ "success" : result })
    server.close()

# Websocket server callbacks

# Called for every client connecting (after handshake)
def WS_new_client(client, server):
	return


# Called for every client disconnecting
def WS_client_left(client, server):
	pass


# Called when a client sends a message
def WS_onmessage(client, server, message):
    #print(type(message), message )
    result = handlePacket(message)
    server.send_message(client, json.dumps({ "success" : result }))

def serveWS(PORT=8988):
    wsServer = WebsocketServer(PORT, host='192.168.1.200')
    wsServer.set_fn_new_client(WS_new_client)
    wsServer.set_fn_client_left(WS_client_left)
    wsServer.set_fn_message_received(WS_onmessage)
    wsServer.run_forever()


if __name__ == '__main__':

    print("-- START --")

    """
        pcstrip : 0,
        bedframe : 1,
        bookshelf : 2,
        window : 3,
        bedlamp : 4
    """
    strips =[wsLED(1, 30, connection), wsLED(2, 40, connection), wsLED(3, 37, connection), wsLED(5, 56, connection),  wsLED(6, 33, connection), wsLED(4, 56, connection)]
    """for x in strips:
        print(x)
        x.run()"""

    for strip in strips:
        strip.run()

    tcpThread = threading.Thread(target=serveTCP)
    tcpThread.daemon = True
    tcpThread.start()

    wsThread = threading.Thread(target=serveWS)
    wsThread.daemon = True
    wsThread.start()

    wsThread.join()
"""
    while True:
        i = raw_input(": ")

        if i == "r" or i == "restart" or i == "reload":
            os.execl(sys.executable, sys.executable, *sys.argv)
        if i == "e" or i == "exit" or i == "quit" or i == "q":
            server.close()
            break
"""
    #while True:
    #    idx, hex = raw_input("Set:").split('.')
    #    strips[int(idx)].fillPixels(hex)
