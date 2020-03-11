import json, time, traceback, platform, uuid
import paho.mqtt.client as mqtt
from jsonsocket import Client as jsonclient

namespace = uuid.UUID('3e76db36-6c8c-4d56-a80b-ad4a8683de30')
localclient = jsonclient()

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

def sendPacket(packet):
    localclient.connect(config['json_host'], config['json_port'])
    localclient.send(packet)
    response = localclient.recv()
    localclient.close()
    return response

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

def ledOff(device):
    """for i in range(64*devIndex, 64*(devIndex+1)):
        raw_pixels[i] = [0, 0, 0]"""

    states[device]['state'] = "OFF"
    sendPacket('{"type":"state", "channel": ' + str(devices[device]) + ', "state" : "off"}')

def ledOn(device):
    """for i in range(64*devIndex, 64*(devIndex+1)):
        raw_pixels[i] = color_pixels[i]"""
    states[device]['state'] = "ON"
    sendPacket('{"type":"state", "channel": ' + str(devices[device]) + ', "state" : "on"}')

def setLedState(device, state):
    ledOn(device) if state else ledOff(device)
    #client.publish("gBridge/u1207/" + devices.inverse[devIndex][0] + "/onoff/set", state)
    client.publish("{0}/{1}/state".format(platform.node(), device), json.dumps(states[device]), retain=True)

def setPixelColors(device, rgb_dict):
        rgb = (rgb_dict['r'], rgb_dict['g'], rgb_dict['b'])
        packet = '{"type":"fill", "channel": ' + str(devices[device]) + ', "color" : "' + str(RGB_to_hex(rgb)) + '"}'
        sendPacket(packet)

        states[device]['color'] = rgb_dict
        #print(states)
        client.publish("{0}/{1}/state".format(platform.node(), device), json.dumps(states[device]), retain=True)

def setPixelBrightness(device, bright):
    packet = '{"type":"brightness", "channel": ' + str(devices[device]) + ', "brightness" : "' + str(bright) + '"}'
    sendPacket(packet)

    states[device]['brightness'] = bright
    client.publish("{0}/{1}/state".format(platform.node(), device), json.dumps(states[device]), retain=True)


def loadConfig(cfg="config.json"):
    global config, devices, states

    with open(cfg) as cfg_file:
        config = json.load(cfg_file)
    devices = bidict(config['devices'])

    states = {}
    for device in devices:
        states[device] = { "state" : "OFF" }

def publishDiscovery():
    try:
        for device in devices:
            payload = {
                "name" : "{0}-{1}".format(platform.node(), device),
                "~" : "{0}/{1}".format(platform.node(), device),
                "unique_id": "{0}-{1}".format(platform.node(), device),
                "cmd_t": "~/set",
                "stat_t": "~/state",
                "schema": "json",
                "brightness": True,
                "rgb" : True,
                "device" : {
                    "identifiers" : [
                        str(uuid.uuid3(namespace, format(platform.node())))
                    ],
                    "name" : "Fadecandy {}".format(platform.node())
                }
            }

            client.subscribe("{0}/{1}/set".format(platform.node(), device))

            client.publish("homeassistant/light/{0}-{1}/config".format(platform.node(), device), json.dumps(payload), retain=True)
    except Exception:
        print(traceback.format_exc())

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))

    publishDiscovery()

def on_message(client, userdata, msg):
    try:

        device = msg.topic.split('/')[1]

        payload = json.loads(msg.payload)

        if "state" in payload:
            setLedState(device, payload['state'].upper() == "ON")
        if "brightness" in payload:
            setPixelBrightness(device, payload['brightness'])
        if "color" in payload:
            setPixelColors(device, payload['color'])

    except Exception:
        print(traceback.format_exc())

if __name__ == "__main__":

    loadConfig()

    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    client.username_pw_set(config['mqtt_user'], config['mqtt_pw'])
    client.connect(config['mqtt_host'], 1883, 60)

    client.loop_forever()
