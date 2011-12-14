import psmove
import sys
import mpd
import subprocess
from datetime import datetime, timedelta
import time
from ConfigParser import SafeConfigParser

config = SafeConfigParser()
config.read('mpdmove.conf')

PORT = config.getint('Login', 'port')
HOST = config.get('Login', 'hostname')
PASSWD = config.get('Login', 'password')

move = psmove.PSMove()
mpc = mpd.MPDClient()
mpc.connect(HOST, PORT)
mpc.password(PASSWD)

ANGLE_DOWN = (config.getint('ANGLE', 'volume_down_min'), config.getint('ANGLE', 'volume_down_max'))
ANGLE_UP = (config.getint('ANGLE', 'volume_up_min'), config.getint('ANGLE', 'volume_up_max'))
ANGLE_TOGGLE = (config.getint('ANGLE', 'toggle_min'), config.getint('ANGLE', 'toggle_max'))

ANGLE_DOWN = (config.getint('ANGLE', 'volume_down_min'), config.getint('ANGLE', 'volume_down_max'))

ANGLE = (ANGLE_TOGGLE, ANGLE_DOWN, ANGLE_UP)
BTN_MOVE = 524288

last_trigger = 0
last_button = 0
gesture = []
last_rumble = datetime.now()

TOGGLE, DOWN, UP = range(3)

def postition_leds():
    state = get_state()
    if state == UP:
        move.set_leds(0,0,100)
    elif state == DOWN:
        move.set_leds(0,100,0)
    elif state == TOGGLE:
        move.set_leds(100,0,0)
    else:
        move.set_leds(0,0,0)

def is_between(value, borders):
    return value >= borders[0] and value <= borders[1]

def get_state():
    if is_between(move.ay, ANGLE[UP]):
        return UP
    elif is_between(move.ay, ANGLE[DOWN]):
        return DOWN
    elif is_between(move.ay, ANGLE[TOGGLE]):
        return TOGGLE
    else:
        return None

def react_bias(horizontal=None, down=None, up=None):
    state = get_state()
    if state == UP and not up == None:
        up()
    elif state == DOWN and not down == None:
        down()
    elif state == TOGGLE and not horizontal == None:
        horizontal()

def volume_up():
    if mpc.status()['volume'] == '100':
        move.set_rumble(150)
        global last_rumble
        last_rumble = datetime.now()
    else:
        print "volume up by 5"
        subprocess.call(['mpc', 'volume', '+5'], stdout=subprocess.PIPE)

def volume_down():
    if mpc.status()['volume'] == '0':
        move.set_rumble(150)
        global last_rumble
        last_rumble = datetime.now()
    else:
        print "volume down by 5"
        subprocess.call(['mpc', 'volume', '-5'], stdout=subprocess.PIPE)

def toggle():
    if mpc.status()['state'] == 'pause' or mpc.status()['state'] == 'stop':
        print "play"
        mpc.play()
    else:
        print "pause"
        mpc.pause()

def check_rise(lst):
    return reduce(lambda x,y: x+y, lst)
        

def handle_trigger():
    react_bias(toggle, volume_down, volume_up)

def handle_gesture(gest):
    if len(gest) < 5:
        print "gesture too short"
        return
    g = map(lambda x: x[0], gest[1:])
    rise = check_rise(g)
    if rise > 0:
        # left
        print "previous"
        mpc.previous()
    elif rise < 0:
        # right
        print "next"
        mpc.next()
        

try:
    while True:
        if move.poll():
            if bool(move.get_trigger()) and not bool(last_trigger):
                handle_trigger()
            postition_leds()
            if move.get_buttons() == BTN_MOVE:
                if last_button == 0:
                    last_button = BTN_MOVE
                
                last_button = BTN_MOVE
                gesture.append((move.ax, move.ay, move.az))
                move.set_leds(255,255,0)
            elif last_button == BTN_MOVE and move.get_buttons() == 0:
                last_button = 0
                handle_gesture(gesture)
                gesture = []
            last_trigger = move.get_trigger()

            #disable rumble after 0.3 seconds
            dt_rumble = datetime.now() - last_rumble
            if dt_rumble.total_seconds() > .3:
                move.set_rumble(0)
            move.update_leds()
        time.sleep(.05)
except KeyboardInterrupt:
    sys.exit()
