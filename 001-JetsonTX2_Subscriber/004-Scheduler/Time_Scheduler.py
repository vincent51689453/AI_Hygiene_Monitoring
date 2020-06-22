import time
import os

intervals_minutes = 15
h,m,s = 0,0,0
past_h,past_m,past_s = 0,0,0
initializer = False

def get_current_time():
    t = time.localtime()
    current_time = time.strftime("%H:%M:%S",t)
    #print("[INFO] System Time->",current_time)
    hour_str = current_time[0]+current_time[1]
    minutes_str = current_time[3]+current_time[4]
    seconds_str = current_time[6]+current_time[7]
    #print("[INFO] Hour="+hour_str+" Minutes="+minutes_str+" Seconds="+seconds_str)
    return int(hour_str),int(minutes_str),int(seconds_str)

def main():
    #Reference
    global initializer
    past_h,past_m,past_s = get_current_time()
    print("[INFO] SysTime Started at->"+str(past_h)+":"+str(past_m)+":"+str(past_s))
    while True:
        if(initializer==False):
            h,m,s = get_current_time()
            if(abs(s-past_s)==1):
                initializer=True
                print("[INFO] SysTime Synchronized!")
                print("[INFO] SysTime Recorded at->"+str(h)+":"+str(m)+":"+str(s))
                print("\r\n")
                past_h = h
                past_m = m
                past_s = s
        else:
            h,m,s = get_current_time()
            #Process every minutes
            if(abs(m-past_m)==1):
                print("[INFO] Task executed at->"+str(h)+":"+str(m)+":"+str(s))
                os.system('python3 task.py')
                past_h = h
                past_m = m
                past_s = s 
             


if __name__ == '__main__':
    main()


