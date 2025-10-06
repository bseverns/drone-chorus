#!/usr/bin/env python3
import time, struct, yaml, threading
import serial, mido

MSP_ATTITUDE = 108
MSP_RC = 105
MSP_ALTITUDE = 109
MSP_ANALOG = 110

def clamp(x, lo, hi): return max(lo, min(hi, x))

class Smoother:
    def __init__(self, slew=0.05):
        self.y = None; self.slew = slew
    def step(self, x):
        if self.y is None: self.y = x
        d = clamp(x - self.y, -self.slew, self.slew); self.y += d; return self.y

class Mapper:
    def __init__(self, norm): self.norm=norm; self.s={k:Smoother(v.get('slew',0.03)) for k,v in norm.items()}
    def norm01(self, key, val):
        n=self.norm[key]; lo,hi=n['min'],n['max']; v=0 if hi==lo else (val-lo)/(hi-lo)
        v=clamp(v,0,1); 
        if n.get('curve')=='expo': v = ((abs(v-0.5)*2)**1.3) * (1 if v>=0.5 else -1) * 0.5 + 0.5
        return self.s[key].step(v)

def read_msp_frame(ser):
    if ser.read(1)!=b'$' or ser.read(1)!=b'M' or ser.read(1)!=b'<': return None,None
    size=ser.read(1)[0]; cmd=ser.read(1)[0]; data=ser.read(size); _=ser.read(1); return cmd,data

def worker(drone, base_norm, midi_out):
    norm={k:dict(v) for k,v in base_norm.items()}
    for k,v in (drone.get('norm_overrides') or {}).items(): norm[k].update(v)
    M=Mapper(norm); ch=drone['channel']-1
    state={'roll':0,'pitch':0,'yaw':0,'altitude':0.0,'rssi':100,'vbat':4.0,'throttle':1000}
    altitude_valid=False
    altitude_last_time=0.0
    with serial.Serial(drone['serial'],115200,timeout=0.01) as ser:
        t0=0
        while True:
            cmd,data=read_msp_frame(ser)
            if cmd is None: time.sleep(0.001); continue
            if cmd==MSP_ATTITUDE and len(data)>=6:
                r,p,y=struct.unpack('<hhh',data[:6]); state['roll']=r/10.0; state['pitch']=p/10.0
            elif cmd==MSP_RC and len(data)>=16:
                chs=struct.unpack('<8H',data[:16]); state['throttle']=chs[2]; state['yaw']=(chs[3]-1500)/500.0*200.0
            elif cmd==MSP_ALTITUDE and len(data)>=6:
                alt_cm,vario=struct.unpack('<ih',data[:6])
                state['altitude']=alt_cm/100.0
                altitude_valid=True
                altitude_last_time=time.time()
            elif cmd==MSP_ANALOG and len(data)>=7:
                state['vbat']=data[0]/10.0; state['rssi']=data[3] if len(data)>=5 else 100
            now=time.time()
            if altitude_valid and now-altitude_last_time>1.5:
                altitude_valid=False
            if not altitude_valid:
                thr_ratio=clamp((state['throttle']-1000)/1000.0,0,1)
                alt_norm=norm['altitude']
                state['altitude']=alt_norm['min'] + thr_ratio*(alt_norm['max']-alt_norm['min'])
            if now-t0>0.02:
                for key,cc in [('roll',14),('pitch',15),('yaw',16),('altitude',17),('rssi',18),('vbat',19),('throttle',20)]:
                    v=int(M.norm01(key,state[key])*127); midi_out.send(mido.Message('control_change',channel=ch,control=cc,value=v))
                gate=127 if state['throttle']>1050 else 0
                midi_out.send(mido.Message('control_change',channel=ch,control=64,value=gate)); t0=now

def main():
    cfg=yaml.safe_load(open('config/multi.yaml'))
    try: out=mido.open_output(cfg['midi']['port_name'],virtual=True)
    except Exception: out=mido.open_output()
    threads=[]
    for d in cfg['drones']:
        t=threading.Thread(target=worker,args=(d,cfg['norm'],out),daemon=True); t.start(); threads.append(t)
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt: pass

if __name__=='__main__': main()
