import cv2
import os
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;udp"
#This RTSP_Camera_Display.py is tested by VStarcamera G43S
camera_user = 'admin'
seperator_1 = ':'
camera_password = '51689453'
seperator_2 = '@'
camera_ip = '192.168.0.100'
rtsp_header = 'rtsp://'
rtsp_remainder = ':554/udp/av0_0'
rtsp_url = rtsp_header+camera_user+seperator_1+camera_password+seperator_2+camera_ip+rtsp_remainder
print("[INFO] RTSP Url->",rtsp_url)

cap = cv2.VideoCapture(rtsp_url)
while True:
    _,frame=cap.read()
    #Output Image is resized to 640x480
    resize_frame=cv2.resize(frame,(640,480))
    cv2.imshow('Display',resize_frame)
    if cv2.waitKey(1)&0xFF==ord('q'):
        break
cap.release()
cv2.destroyAllWindows()

