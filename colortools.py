from __future__ import division

import math
import numpy as np
import colorsys

def K_to_RGB(colour_temperature):
    if colour_temperature < 1000:
        colour_temperature = 1000
    elif colour_temperature > 40000:
        colour_temperature = 40000

    tmp_internal = colour_temperature / 100.0

    # red
    if tmp_internal <= 66:
        red = 255
    else:
        tmp_red = 329.698727446 * math.pow(tmp_internal - 60, -0.1332047592)
        if tmp_red < 0:
            red = 0
        elif tmp_red > 255:
            red = 255
        else:
            red = tmp_red

    # green
    if tmp_internal <=66:
        tmp_green = 99.4708025861 * math.log(tmp_internal) - 161.1195681661
        if tmp_green < 0:
            green = 0
        elif tmp_green > 255:
            green = 255
        else:
            green = tmp_green
    else:
        tmp_green = 288.1221695283 * math.pow(tmp_internal - 60, -0.0755148492)
        if tmp_green < 0:
            green = 0
        elif tmp_green > 255:
            green = 255
        else:
            green = tmp_green

    # blue
    if tmp_internal >=66:
        blue = 255
    elif tmp_internal <= 19:
        blue = 0
    else:
        tmp_blue = 138.5177312231 * math.log(tmp_internal - 10) - 305.0447927307
        if tmp_blue < 0:
            blue = 0
        elif tmp_blue > 255:
            blue = 255
        else:
            blue = tmp_blue

    return [red, green, blue]


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

def RGB_to_HSV(RGB):
    ''' [255,255,255] -> "[0, 0, 1]" '''
    RGB = [int(x)/255.0 for x in RGB]
    return colorsys.rgb_to_hsv(*RGB)

def HSV_to_RGB(HSV):
    RGB = colorsys.hsv_to_rgb(*HSV)
    return [x*255 for x in RGB]

def phase(px, phase):
    return np.moveaxis(px, phase, 0)

def linear_gradient(pixels, start_hex, n, finish_hex="FFFFFF", list_offset=0):
  ''' returns a gradient list of (n) colors between
    two hex colors. start_hex and finish_hex
    should be the full six-digit color string,
    inlcuding the number sign ("FFFFFF") '''
  # Starting and ending colors in RGB form
  RGB_list = np.empty_like(pixels)
  s = hex_to_RGB(start_hex)
  f = hex_to_RGB(finish_hex)
  # Initilize a list of the output colors with the starting color

  # Calcuate a color at each evenly spaced value of t from 1 to n
  for t in range(1, n):
    # Interpolate RGB vector for color at the current value of t
      RGB_list[t-1+list_offset, 0] = int(s[0] + (float(t)/(n-1))*(f[0]-s[0]))
      RGB_list[t-1+list_offset, 1] = int(s[2] + (float(t)/(n-1))*(f[2]-s[2]))
      RGB_list[t-1+list_offset, 2] = int(s[1] + (float(t)/(n-1))*(f[1]-s[1]))

  return RGB_list

def multi_gradient(px, colors, n):
    s = int(float(n)/len(colors))
    for x in range(0, len(colors)-2):
        px = linear_gradient(px, colors[x], colors[x+1], s, (s*x)-5)

def triplecolor(px, colors, n):
    colorone = hex_to_RGB(colors[0])
    colorone[1], colorone[2] = colorone[2], colorone[1]

    colortwo = hex_to_RGB(colors[1])
    colortwo[1], colortwo[2] = colortwo[2], colortwo[1]

    colorthree = hex_to_RGB(colors[2])
    colorthree[1], colorthree[2] = colorthree[2], colorthree[1]

    for i in range(0, n):
        if i % 3 == 0:
            px[i] = colorone
        elif i % 3 == 1:
            px[i] = colortwo
        elif i % 3 == 2:
            px[i] = colorthree
    return px


def rainbow(px, phase, n, saturation=1):

    for i in range(0, n):
        hue = i*(1.0/n)
        #Apply phase to hue
        hue += phase/360
        if hue > 1:
            hue -= 1

        px[i] = HSV_to_RGB([hue, saturation, 1])

    return px


def solid_fill(px, hex, n):
    rgb = hex_to_RGB(hex)

    px[0] = [rgb[0]]*n
    px[1] = [rgb[2]]*n
    px[2] = [rgb[1]]*n

    return px
