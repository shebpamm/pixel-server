import fastopc as opc
import time, os, sys, traceback
import numpy as np
#from logipy import logi_led
import colortools as ct
import threading
import jsonsocket, json
from websocket_server import WebsocketServer


connection = opc.FastOPC()

class wsLED:
    def __init__(self, channel, length, controller, speed=1, step=1):
        self.channel = channel
        self.length = length
        self.controller = controller
        self.speed = speed
        self.step = step
        self.running = False
        self.interpolating = False
        self.targetPixels = np.array([ [0,0,0] ] * 64)
        self.realPixels = np.array([ [0,0,0] ] * 64)
        self.blackPixels = np.array([ [0,0,0] ] * 64)
        self.brightlevel = 100
        self.isOn = False


    def setOverride(self, state):

        print(type(state))

        if state == True:
            self.interpolating = False
        if state == False:
            self.interpolating = True

    def lightOn(self):
        self.isOn = True

    def lightOff(self):
        self.isOn = False

    def setState(self, state):
        if state == "on":
            self.lightOn()
        elif state == "off":
            self.lightOff()
        else: print("Channel {0}: Invalid state".format(self.channel))

    def fillPixels(self, hex):
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

    def gradientPixels(self, start_hex, end_hex, phase):
        self.lightOn()
        self.targetPixels = ct.phase(ct.linear_gradient(self.targetPixels, start_hex, self.length, end_hex), phase)

    def triplePixels(self, colors):
        self.lightOn()
        self.targetPixels = ct.triplecolor(self.targetPixels, colors, self.length)

    def rainbowPixels(self, phase):
        self.lightOn()
        self.targetPixels = ct.rainbow(self.targetPixels, phase, self.length)

    def brightness(self, bright):

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

    def interpolate(self):
        while self.running:
            if self.interpolating:
                for i in range(0, self.length):
                    for c in range(0, 3):

                        if not self.isOn:
                            targetcolor = self.blackPixels[i][c]

                        else:
                            targetcolor = self.targetPixels[i][c]

                        realcolor = self.realPixels[i][c]

                        if realcolor > targetcolor and realcolor-targetcolor >= self.step:
                                self.realPixels[i][c] -= self.step
                        elif realcolor < targetcolor  and targetcolor-realcolor >= self.step:
                                self.realPixels[i][c] += self.step

            #    if i == 1:
                    #print(self.targetPixels[i])
                    #print(self.realPixels[i])

                self.controller.putPixels(self.channel, self.realPixels)
            time.sleep(0.00392156862*self.speed)

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
                    "self.isOn" : strips[data['channel']].isOn
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
                    "self.isOn" : strips[data['channel']].isOn
                }

    except Exception as e:
        print(traceback.format_exc())
        return False

def serveTCP(port=8989):

    host = '127.0.0.1'


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
    strips =[wsLED(1, 30, connection), wsLED(2, 40, connection), wsLED(3, 37, connection), wsLED(5, 41, connection),  wsLED(6, 33, connection), wsLED(4, 64, connection)]
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

    while False:
        i = raw_input(": ")

        if i == "r" or i == "restart" or i == "reload":
            os.execl(sys.executable, sys.executable, *sys.argv)
        if i == "e" or i == "exit" or i == "quit" or i == "q":
            break

    #while True:
    #    idx, hex = raw_input("Set:").split('.')
    #    strips[int(idx)].fillPixels(hex)
