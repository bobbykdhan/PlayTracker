#!/usr/bin/env python3
import time
import os
from playsound import playsound

os.system("bluetoothctl connect 74:A7:EA:B0:8D:0E")
while KeyboardInterrupt:
    playsound('audio.mp3')
    time.sleep(0.5)