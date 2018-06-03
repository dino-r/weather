#! /usr/bin/python

import sys, fcntl, time
from prometheus_client import start_http_server, Gauge

class CO2monitor(object):
    def __init__(self, dev):
        # Key retrieved from /dev/random, guaranteed to be random ;)
        self._key = [0xc4, 0xc6, 0xc0, 0x92, 0x40, 0x23, 0xdc, 0x96]
        self._HIDIOCSFEATURE_9 = 0xC0094806
        self._set_report = "\x00" + "".join(chr(e) for e in self._key)
        self._cstate = [0x48,  0x74,  0x65,  0x6D,  0x70,  0x39,  0x39,  0x65]
        self._shuffle = [2, 4, 0, 7, 1, 6, 5, 3]
    
        self.fp = open(dev, "a+b",  0)
        fcntl.ioctl(self.fp, self._HIDIOCSFEATURE_9, self._set_report)

        self.temperature = None #[C]
        self.co2         = None #[ppm]

    def decrypt(self, data):
        phase1 = [0] * 8
        for i, o in enumerate(self._shuffle):
            phase1[o] = data[i]
        
        phase2 = [0] * 8
        for i in range(8):
            phase2[i] = phase1[i] ^ self._key[i]
        
        phase3 = [0] * 8
        for i in range(8):
            phase3[i] = ( (phase2[i] >> 3) | (phase2[ (i-1+8)%8 ] << 5) ) & 0xff
        
        ctmp = [0] * 8
        for i in range(8):
            ctmp[i] = ( (self._cstate[i] >> 4) | (self._cstate[i]<<4) ) & 0xff
        
        out = [0] * 8
        for i in range(8):
            out[i] = (0x100 + phase3[i] - ctmp[i]) & 0xff
        
        return out

    def read(self):
        values = {}

        data = list(ord(e) for e in self.fp.read(8))
        decrypted = self.decrypt(data)
        if decrypted[4] != 0x0d or (sum(decrypted[:3]) & 0xff) != decrypted[3]:
            print hd(data), " => ", hd(decrypted),  "Checksum error"
        else:
            op = decrypted[0]
            val = decrypted[1] << 8 | decrypted[2]
            
            values[op] = val
            
            ## From http://co2meters.com/Documentation/AppNotes/AN146-RAD-0401-serial-communication.pdf
            if 0x50 in values:
                #print "CO2: %4i" % values[0x50], 
                self.co2 = values[0x50]
            if 0x42 in values:
                #values[0x42] is a tuple 
                self.temperature  = values[0x42]/16.0 - 273.15


def hd(d):
    return " ".join("%02X" % e for e in d)


if __name__ == "__main__":
    monitor = CO2monitor(sys.argv[1])    

    #prometheus clients
    REQUEST_TEMPERATURE = Gauge("co2_monitor_temperature", "Temperature converted to Celsius as reported by the CO2 monitoring device")
    REQUEST_CO2 = Gauge("co2_monitor_CO2", "CO2 level in ppm")
    start_http_server(9110)

    # wait for the sensor a bit until we start reading
    time.sleep(60)
    while True:
        monitor.read()
        #print("temperature: {}C,   CO2: {}ppm".format(monitor.temperature, monitor.co2))

        if(monitor.temperature != None):
            REQUEST_TEMPERATURE.set(monitor.temperature)

        if(monitor.co2 != None):
            REQUEST_CO2.set(monitor.co2)
        
