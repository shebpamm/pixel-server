import time, traceback
import paho.mqtt.client as mqtt
from logipy import logi_led
from jsonsocket import Client

host = 'LOCALHOST'
port = 8989

localclient = Client()

logi_led.logi_led_init()
ledOnState = False
numLeds = 512

current_color = "000000"

base_topic = "gBridge/u1207/"

def sendPacket(packet):
    localclient.connect(host, port)
    localclient.send(packet)
    response = localclient.recv()
    print(response)
    localclient.close()
    return response

class bidict(dict):
    def __init__(self, *args, **kwargs):
        super(bidict, self).__init__(*args, **kwargs)
        self.inverse = {}
        for key, value in self.items():
            self.inverse.setdefault(value,[]).append(key)

    def __setitem__(self, key, value):
        if key in self:
            self.inverse[self[key]].remove(key)
        super(bidict, self).__setitem__(key, value)
        self.inverse.setdefault(value,[]).append(key)

    def __delitem__(self, key):
        self.inverse.setdefault(self[key],[]).remove(key)
        if self[key] in self.inverse and not self.inverse[self[key]]:
            del self.inverse[self[key]]
        super(bidict, self).__delitem__(key)

topics = bidict({
            "onoff" : "bedlamp/onoff",
#            "brightness" : "bedlamp/brightness",
            "colorsettingrgb" : "bedlamp/colorsettingrgb"
         })

'''
devices = bidict({
            "window" : 0,
            "bedlamp" : 1,
            "bedframe" : 2,
            "pcstrip" : 3
          })
'''

devices = bidict({
            "pcstrip" : 0,
            "bedframe" : 1,
            "bookshelf" : 2,
            "window" : 3,
            "bedlamp" : 4
          })

def hex_to_RGB(hex):
  ''' "FFFFFF" -> [255,255,255] '''
  # Pass 16 to the integer function for change of base
  return [int(hex[i:i+2], 16) for i in range(0,5,2)]


def RGB_to_hex(RGB):
  ''' [255,255,255] -> "FFFFFF" '''
  # Components need to be integers for hex to make sense
  RGB = [int(x) for x in RGB]
  return "".join(["0{0:x}".format(v) if v < 16 else
            "{0:x}".format(v) for v in RGB])

def ledOff(devIndex):
    """for i in range(64*devIndex, 64*(devIndex+1)):
        raw_pixels[i] = [0, 0, 0]"""

    sendPacket('{"type":"state", "channel": ' + str(devIndex) + ', "state" : "off"}')

def ledOn(devIndex):
    """for i in range(64*devIndex, 64*(devIndex+1)):
        raw_pixels[i] = color_pixels[i]"""

    sendPacket('{"type":"state", "channel": ' + str(devIndex) + ', "state" : "on"}')

def setLedState(devIndex, state):
    ledOn(devIndex) if state else ledOff(devIndex)
    print("gBridge/u1207/" + devices.inverse[devIndex][0] + "/onoff/set", state)
    client.publish("gBridge/u1207/" + devices.inverse[devIndex][0] + "/onoff/set", state)

def setPixelColors(devIndex, hex):
    try:
        current_color = hex
        packet = '{"type":"fill", "channel": ' + str(devIndex) + ', "color" : "' + str(hex) + '"}'
        sendPacket(packet)

        client.publish("gBridge/u1207/" + devices.inverse[devIndex][0] + "/colorsettingrgb/set", hex)
        client.publish("gBridge/u1207/" + devices.inverse[devIndex][0] + "/onoff/set", 1)
    except Exception:
        print(traceback.format_exc())
def setPixelBrightness(devIndex, bright):
    packet = '{"type":"brightness", "channel": ' + str(devIndex) + ', "brightness" : "' + str(bright) + '"}'
    sendPacket(packet)
    print(devIndex, bright)

    if bright == 0:
        client.publish("gBridge/u1207/" + devices.inverse[devIndex][0] + "/onoff/set", 0)
    else:
        client.publish("gBridge/u1207/" + devices.inverse[devIndex][0] + "/onoff/set", 1)

def keyboardOn():
    logi_led.logi_led_set_lighting(100, 100, 100)
    client.publish("gBridge/u1207/keyboard/onoff/set", 1)

def keyboardOff():
    logi_led.logi_led_set_lighting(0, 0, 0)
    client.publish("gBridge/u1207/keyboard/onoff/set", 0)

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))

    client.subscribe("gBridge/u1207/keyboard/onoff")

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    for device in devices:
        print(device)
        client.subscribe(base_topic + device + "/onoff")
        client.subscribe(base_topic + device + "/brightness")
        client.subscribe(base_topic + device + "/colorsettingrgb")
        client.publish(base_topic + device + "/onoff/set", 0)

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    print(msg.topic+" "+str(msg.payload))
    params = msg.topic.split('/')[2:]

    if params[0] == "keyboard":
        keyboardOn() if int(msg.payload) else keyboardOff()

    if params[1] == "onoff":
        setLedState(devices[params[0]], int(msg.payload))
    elif params[1] == "colorsettingrgb":
        setPixelColors(devices[params[0]], msg.payload)
    elif params[1] == "brightness":
        setPixelBrightness(devices[params[0]], msg.payload)


client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.username_pw_set("gbridge-u1207", "***REMOVED***")
client.connect("mqtt.gbridge.io", 1883, 60)


# Blocking call that processes network traffic, dispatches callbacks and
# handles reconnecting.
# Other loop*() functions are available that give a threaded interface and a
# manual interface.
client.loop_forever()
