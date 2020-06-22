import sys
import time
import logging
import argparse

import numpy as np
import cv2
import tensorflow as tf
import tensorflow.contrib.tensorrt as trt
import centroidtracker as ot
import imutils
import csv
import paho.mqtt.client as mqtt
from utils.camera import add_camera_args, Camera
from utils.od_utils import read_label_map, build_trt_pb, load_trt_pb, \
                           write_graph_tensorboard, detect
#from utils.visualization import BBoxVisualization
import math

#Global Parameters -- Vincent
ALPHA = 0.5
FONT = cv2.FONT_HERSHEY_PLAIN
TEXT_SCALE = 1.0
TEXT_THICKNESS = 1
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
person_detection = False #Control Display status
hand_wash_status=0
ct = ot.CentroidTracker()
temp=[]
client = mqtt.Client()

#It should connect to MQTT server
#Jetson TX2(vincent) has been set as a MQTT server
#If publisher/subscriber on JetsonTX2(vincet) please connect to localhost
#Else please connect to  192.168.0.101 in the LAN
client.connect("localhost",1883,60)
#Global Parameters -- Vincent

# Constants
DEFAULT_MODEL = 'ssd_mobilenet_v1_coco'
DEFAULT_LABELMAP = 'third_party/models/research/object_detection/' \
                   'data/mscoco_label_map.pbtxt'
WINDOW_NAME = 'AI-Hygiene-Tracking[Room]'
BBOX_COLOR = (0, 255, 0)  # green


def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    client.subscribe("MDSSCC/AIHH/SENSOR")

def on_message(client, userdata, msg):
    global hand_wash_status
    if(msg.payload.decode() == "WASHED"):
        print("<<WASHED>> received")
        hand_wash_status=1 
    if (msg.payload.decode() == "DIRTY"):
        print("<<DIRTY>> received")
        hand_wash_status=0
    if(msg.payload.decode() == "PRESS"):
        print("alchol")
        hand_wash_status=1
    if(msg.payload.decode() == "RELEASE"):
        hand_wash_status=0
#Not using loop_forever since it is using the current thread
client.loop_start()
client.on_connect = on_connect
client.on_message = on_message

def parse_args():
    """Parse input arguments."""
    desc = ('This script captures and displays live camera video, '
            'and does real-time object detection with TF-TRT model '
            'on Jetson TX2/TX1/Nano')
    parser = argparse.ArgumentParser(description=desc)
    parser = add_camera_args(parser)
    parser.add_argument('--model', dest='model',
                        help='tf-trt object detecion model '
                        '[{}]'.format(DEFAULT_MODEL),
                        default=DEFAULT_MODEL, type=str)
    parser.add_argument('--build', dest='do_build',
                        help='re-build TRT pb file (instead of using'
                        'the previously built version)',
                        action='store_true')
    parser.add_argument('--tensorboard', dest='do_tensorboard',
                        help='write optimized graph summary to TensorBoard',
                        action='store_true')
    parser.add_argument('--labelmap', dest='labelmap_file',
                        help='[{}]'.format(DEFAULT_LABELMAP),
                        default=DEFAULT_LABELMAP, type=str)
    parser.add_argument('--num-classes', dest='num_classes',
                        help='(deprecated and not used) number of object '
                        'classes', type=int)
    parser.add_argument('--confidence', dest='conf_th',
                        help='confidence threshold [0.3]',
                        default=0.3, type=float)
    args = parser.parse_args()
    return args


def open_display_window(width, height):
    """Open the cv2 window for displaying images with bounding boxeses."""
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW_NAME, width, height)
    cv2.moveWindow(WINDOW_NAME, 0, 0)
    cv2.setWindowTitle(WINDOW_NAME, 'AI-Hygiene-Tracker[ROOM]')


def draw_help_and_fps(img, fps):
    """Draw help message and fps number at top-left corner of the image."""
    help_text = "'Esc' to Quit, 'H' for FPS & Help, 'F' for Fullscreen"
    font = cv2.FONT_HERSHEY_PLAIN
    line = cv2.LINE_AA

    fps_text = 'FPS: {:.1f}'.format(fps)
    cv2.putText(img, help_text, (11, 20), font, 1.0, (32, 32, 32), 4, line)
    cv2.putText(img, help_text, (10, 20), font, 1.0, (240, 240, 240), 1, line)
    cv2.putText(img, fps_text, (11, 50), font, 1.0, (32, 32, 32), 4, line)
    cv2.putText(img, fps_text, (10, 50), font, 1.0, (240, 240, 240), 1, line)
    return img


def set_full_screen(full_scrn):
    """Set display window to full screen or not."""
    prop = cv2.WINDOW_FULLSCREEN if full_scrn else cv2.WINDOW_NORMAL
    cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN, prop)

#<<-----------------------------------------------------Vincent---------------------------------->>#
def gen_colors(num_colors):
    """Generate different colors.

    # Arguments
      num_colors: total number of colors/classes.

    # Output
      bgrs: a list of (B, G, R) tuples which correspond to each of
            the colors/classes.
    """
    import random
    import colorsys

    hsvs = [[float(x) / num_colors, 1., 0.7] for x in range(num_colors)]
    random.seed(1234)
    random.shuffle(hsvs)
    rgbs = list(map(lambda x: list(colorsys.hsv_to_rgb(*x)), hsvs))
    bgrs = [(int(rgb[2] * 255), int(rgb[1] * 255),  int(rgb[0] * 255))
            for rgb in rgbs]
    return bgrs


def draw_boxed_text(img, text, topleft, color):
    """Draw a transluent boxed text in white, overlayed on top of a
    colored patch surrounded by a black border. FONT, TEXT_SCALE,
    TEXT_THICKNESS and ALPHA values are constants (fixed) as defined
    on top.

    # Arguments
      img: the input image as a numpy array.
      text: the text to be drawn.
      topleft: XY coordinate of the topleft corner of the boxed text.
      color: color of the patch, i.e. background of the text.

    # Output
      img: note the original image is modified inplace.
    """
    assert img.dtype == np.uint8
    img_h, img_w, _ = img.shape
    if topleft[0] >= img_w or topleft[1] >= img_h:
        return
    margin = 3
    size = cv2.getTextSize(text, FONT, TEXT_SCALE, TEXT_THICKNESS)
    w = size[0][0] + margin * 2
    h = size[0][1] + margin * 2
    # the patch is used to draw boxed text
    patch = np.zeros((h, w, 3), dtype=np.uint8)
    patch[...] = color
    cv2.putText(patch, text, (margin+1, h-margin-2), FONT, TEXT_SCALE,
                WHITE, thickness=TEXT_THICKNESS, lineType=cv2.LINE_8)
    cv2.rectangle(patch, (0, 0), (w-1, h-1), BLACK, thickness=1)
    w = min(w, img_w - topleft[0])  # clip overlay at image boundary
    h = min(h, img_h - topleft[1])
    # Overlay the boxed text onto region of interest (roi) in img
    roi = img[topleft[1]:topleft[1]+h, topleft[0]:topleft[0]+w, :]
    cv2.addWeighted(patch[0:h, 0:w, :], ALPHA, roi, 1 - ALPHA, 0, roi)
    return img


class BBoxVisualization():
    """BBoxVisualization class implements nice drawing of boudning boxes.

    # Arguments
      cls_dict: a dictionary used to translate class id to its name.
    """

    def __init__(self, cls_dict):
        self.cls_dict = cls_dict
        self.colors = gen_colors(len(cls_dict))

    def draw_bboxes(self, img, box, conf, cls):
        """Draw detected bounding boxes on the original image.""" 
        global person_detection,rects,ct,temp,hand_wash_status
        print("================================================================================")
        for bb, cf, cl in zip(box, conf, cls):
            cl = int(cl)
            print("Confidence=",cf)
            if((cl == 1)and(cf>=0.6)): #Vincent:Only process "person" (label id of persion = 1) + confidence control
                y_min, x_min, y_max, x_max = bb[0], bb[1], bb[2], bb[3]
                color = self.colors[cl]
                temp.append(x_min)
                temp.append(y_min)
                temp.append(x_max)
                temp.append(y_max)
                print("Boundary Box Coordinates:")
                print("X-min:%d Y-min:%d X-max:%d Y-max:%d"%(x_min,y_min,x_max,y_max))
                print("Buffer:",temp)
                print("Hand-Wash?",hand_wash_status)
                rects.append(temp)
                temp=[]
                cv2.rectangle(img, (x_min, y_min), (x_max, y_max), color, 2)
                txt_loc = (max(x_min+2, 0), max(y_min+2, 0))
                cls_name = self.cls_dict.get(cl, 'CLS{}'.format(cl))
                txt = '{} {:.2f}'.format(cls_name, cf)
                img = draw_boxed_text(img, txt, txt_loc, color)
                person_detection = True
        print("Trackers=",rects)
        #if(person_detection == True):  #Vincent: Detection status display
            #cv2.putText(img, "Status:Person IN ROOM", (10, 90), cv2.FONT_HERSHEY_PLAIN, 1.5, (0,255,0), 2, cv2.LINE_AA)
        #else:
        #    cv2.putText(img, "Status:EMPTY", (10, 90), cv2.FONT_HERSHEY_PLAIN, 1.5, (0,0,255), 2, cv2.LINE_AA)
        person_detection = False          
        return img,hand_wash_status
#<<-----------------------------------------------------Vincent---------------------------------->>#
def pixel_info(event,x,y,flag,param):
    if event == cv2.EVENT_LBUTTONDOWN:  #When Left is clicked in the mouse
        print("X:{} Y:{}".format(x,y))




def loop_and_detect(cam, tf_sess, conf_th, vis, od_type):
    """Loop, grab images from camera, and do object detection.

    # Arguments
      cam: the camera object (video source).
      tf_sess: TensorFlow/TensorRT session to run SSD object detection.
      conf_th: confidence/score threshold for object detection.
      vis: for visualization.
    """
    show_fps = True
    full_scrn = False
    fps = 0.0
    tic = time.time()
    global rects,ct,temp
    zone_x_bed = 0
    zone_y_bed = 0
    #Boundary boxes for Room_Hygiene_Demo_12_5fps.mp4
    #zone_x_min_bed,zone_y_min_bed,zone_x_max_bed,zone_y_max_bed = 840,500,1300,1000
    zone_x_clean = 0
    zone_y_clean = 0
    #Boundary boxes for Room_Hygiene_Demo_12_5fps.mp4
    #zone_x_min_clean,zone_y_min_clean,zone_x_max_clean,zone_y_max_clean = 300,416,580,680
    #Boundary boxes for Room_Hygiene_Demo_12_5fps.mp4
    #zone_x_min_door,zone_y_min_door,zone_x_max_door,zone_y_max_door = 1200,140,1300,380

    #Bondary boxes for video demo
    #Boundary boxes for RTSP_Room_View_Ready.mp4
    #zone_x_min_bed,zone_y_min_bed,zone_x_max_bed,zone_y_max_bed = 600,500,1000,1000
    #Boundary boxes for RTSP_Room_View_Ready.mp4
    #zone_x_min_clean,zone_y_min_clean,zone_x_max_clean,zone_y_max_clean = 1600,500,1900,820
    #Boundary boxes for RTSP_Room_View_Ready.mp4
    #zone_x_min_door,zone_y_min_door,zone_x_max_door,zone_y_max_door = 450,140,730,480
    #Boundary boxes for RTSP_Room_View_Ready.mp4
    #zone_x_min_alchol,zone_y_min_alchol,zone_x_max_alchol,zone_y_max_alchol = 300+800,200+300,350+800,270+300


    #Boundary boxes for RTSP (low resolution)
    zone_x_min_bed,zone_y_min_bed,zone_x_max_bed,zone_y_max_bed = 154,199,248,326
    zone_x_min_clean,zone_y_min_clean,zone_x_max_clean,zone_y_max_clean = 490,147,627,338
    zone_x_min_door,zone_y_min_door,zone_x_max_door,zone_y_max_door = 62,78,101,128
    zone_x_min_alchol,zone_y_min_alchol,zone_x_max_alchol,zone_y_max_alchol = 325,151,364,194


    #Room_Hygiene_Demo_12_5fps.mp4
    #distance_thres_bed = 150
    #distance_thres_clean = 80

    #RTSP_Room_View_Read.mp4
    distance_thres_bed = 79
    distance_thres_clean = 120
    distance_thres_alchol = 40

    counter_msg = 0
    fail_msg = 0
    pass_msg = 0
    global hand_wash_status,args
    hd = 0
    wash_delay = 0
    invalid_id = []
    invalid_id.append(999)
    enter,leave = False,False
    restart_flag = False #restart issue
    backup_label = None  #restart issue
    none_buff = 0 #restart issue
    previous_id = 999
    frame_buffer = 0
    frame_reset_thres=27000
    # 15fps  -> 27000 -> reset every 30 minutes
    #CSV Log File
    with open('./path_analyzer/path_log.csv','w',newline='') as csv_log_file:
        log_writer=csv.writer(csv_log_file)
        while True:
            #if cv2.getWindowProperty(WINDOW_NAME, 0) < 0:
                # Check to see if the user has closed the display window.
                # If yes, terminate the while loop.
            #    break
            if(restart_flag == True):
                cam = Camera(args)
                cam.open()
                cam.start()
                print("Camera is opened!")
                dummy_img = np.zeros((720, 1280, 3), dtype=np.uint8)
                _, _, _ = detect(dummy_img, tf_sess, conf_th=.3, od_type=od_type)
                print("Loading dummy image!")
                restart_flag = False


            rects = []
            img = cam.read()
            if img is not None:
                #check mqtt status
                #client.on_message = on_message
                #client.loop_forever()
                box, conf, cls = detect(img, tf_sess, conf_th, od_type=od_type)    
                img,hd = vis.draw_bboxes(img, box, conf, cls)
                #Detection Zone
                cv2.rectangle(img, (zone_x_min_bed,zone_y_min_bed),(zone_x_max_bed,zone_y_max_bed),(255,102,255),2)
                zone_x_bed = int((zone_x_min_bed+zone_x_max_bed)/2.0)
                zone_y_bed = int((zone_y_min_bed+zone_y_max_bed)/2.0)
                cv2.circle(img, (zone_x_bed, zone_y_bed), 4, (255,102,255), -1)
                cv2.putText(img, "Patient", (zone_x_bed-40, zone_y_bed-20),cv2.FONT_HERSHEY_SIMPLEX, 0.5,(255,102,255), 1)
                cv2.rectangle(img, (zone_x_min_clean,zone_y_min_clean),(zone_x_max_clean,zone_y_max_clean),(255,255,51),2)            
                zone_x_clean = int((zone_x_min_clean+zone_x_max_clean)/2.0)
                zone_y_clean = int((zone_y_min_clean+zone_y_max_clean)/2.0)
                cv2.circle(img, (zone_x_clean, zone_y_clean), 4, (255,255,51), -1)
                cv2.putText(img, "CLEANING ZONE", (zone_x_clean-110, zone_y_clean-20),cv2.FONT_HERSHEY_SIMPLEX, 0.5,(255,255,51), 1)
                cv2.rectangle(img, (zone_x_min_door,zone_y_min_door),(zone_x_max_door,zone_y_max_door),(127,0,255),2)            
                zone_x_door = int((zone_x_min_door+zone_x_max_door)/2.0)
                zone_y_door = int((zone_y_min_door+zone_y_max_door)/2.0)
                cv2.circle(img, (zone_x_door, zone_y_door), 4, (127,0,255), -1)
                cv2.putText(img, "ENTRANCE", (zone_x_door-40, zone_y_door-20),cv2.FONT_HERSHEY_SIMPLEX, 0.5,(127,0,255), 1)
                cv2.rectangle(img, (zone_x_min_alchol,zone_y_min_alchol),(zone_x_max_alchol,zone_y_max_alchol),(255,255,51),2)            
                zone_x_alchol = int((zone_x_min_alchol+zone_x_max_alchol)/2.0)
                zone_y_alchol = int((zone_y_min_alchol+zone_y_max_alchol)/2.0)
                cv2.circle(img, (zone_x_alchol, zone_y_alchol), 4, (255,255,51), -1)
                cv2.putText(img, "CLEANING ZONE", (zone_x_alchol-35, zone_y_alchol-20),cv2.FONT_HERSHEY_SIMPLEX, 0.5,(255,255,51), 1)
                distance_bed = 0
                distance_clean = 0
                #Detection Zone
                objects,valid_checker = ct.update(rects)
                flag = False
                for ((objectID, centroid),(objectID,valid)) in zip(objects.items(),valid_checker.items()):
		    # draw both the ID of the object and the centroid of the
		    # object on the output frame
                    text_id = "ID {}".format(objectID)
                    backup_label = str(objectID)
                    text = "staff"
                    cv2.putText(img, text, (centroid[0] - 10, centroid[1] - 10),cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                    cv2.putText(img, text_id, (centroid[0] - 10, centroid[1] - 50),cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                    cv2.circle(img, (centroid[0], centroid[1]), 4, (0, 255, 0), -1)
                    distance_bed = int(math.sqrt((centroid[0]-zone_x_bed)**2+(centroid[1]-zone_y_bed)**2))
                    distance_clean = int(math.sqrt((centroid[0]-zone_x_clean)**2+(centroid[1]-zone_y_clean)**2))
                    distance_clean_alchol = int(math.sqrt((centroid[0]-zone_x_alchol)**2+(centroid[1]-zone_y_alchol)**2))
                    enter = ct.display_enter_status(objectID)
                    leave = ct.display_leave_status(objectID)
                    flag = ct.display_hygiene(objectID)
                    if(distance_clean_alchol <= distance_thres_alchol):
                        cv2.line(img,(centroid[0], centroid[1]),(zone_x_alchol,zone_y_alchol),(255,0,255),1)
                        if(hand_wash_status == 1):
                            personal_status = 1
                        ct.update_wash(True,objectID) 
                 
                    if(distance_bed <= distance_thres_bed):
                        personal_status = 0
                        hand_wash_status = 0
                        cv2.line(img,(centroid[0], centroid[1]),(zone_x_bed,zone_y_bed),(255,0,255),1)
                        #Update Hygiene Status as the staff is originally cleaned
                        ct.update_hygiene(False,objectID)
                        #Never enter
                        if(enter == False):
                            ct.update_enter(True,objectID)
                            #If the staff did not wash hand and go to patient directly
                            hand_wash_flag = ct.display_wash(objectID) 
                            if(hand_wash_flag == False):
                                ct.update_valid(False,objectID)
                                m = 0
                                match = True
                                #Check whether this ID is marked as fail or not (on the screen)
                                while(m<len(invalid_id)):
                                    if(objectID==invalid_id[m]):
                                        #ObjectID is found in the invalid bank
                                        match = True
                                    else:
                                        match = False
                                    m+=1
                                #If it is not in the bank,then mark it and fail counter + 1
                                if(match == False):
                                    fail_msg +=1
                                    invalid_id.append(objectID)                                                            
                        #Enter again with uncleaned => invalid
                        else:
                            if(flag == False):
                                #Re-enter the patient zone
                                if((enter == True)and(leave == True)):
                                    ct.update_valid(False,objectID)
                                    m = 0
                                    match = True
                                    #Check whether this ID is marked as fail or not (on the screen)
                                    while(m<len(invalid_id)):
                                        if(objectID==invalid_id[m]):
                                            #ObjectID is found in the invalid bank
                                            match = True
                                        else:
                                            match = False
                                        m+=1
                                    #If it is not in the bank,then mark it and fail counter + 1
                                    if(match == False):
                                        fail_msg +=1
                                        invalid_id.append(objectID)
                    else:
                        if(enter == True):
                            ct.update_leave(True,objectID)    


                            
                    if(distance_clean <= distance_thres_clean):
                        cv2.line(img,(centroid[0], centroid[1]),(zone_x_clean,zone_y_clean),(255,0,255),1)
                        if(hand_wash_status == 1):
                            personal_status = 1
                        #hand_wash_status = 1
                        #Update Hygiene Status
                        ct.update_hygiene(True,objectID)
                        #Reset IN/OUT Mechanism
                        ct.update_enter(False,objectID)
                        ct.update_leave(False,objectID)
                        ct.update_wash(True,objectID)                     
                    #Return hygiene status
                    flag = ct.display_hygiene(objectID)
                    if(previous_id!=objectID):
                        hand_wash_status = 0
                        personal_status = 0
                    previous_id = objectID 

                    #if(hand_wash_status == 1):
                    #    cv2.putText(img,"Cleaned", (centroid[0]-10, centroid[1]-30),cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                    #else:
                    #    cv2.putText(img,"Uncleaned", (centroid[0]-10, centroid[1]-30),cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                    #CSV TABLE FORMAT: ID, X, Y, DISTANCE_BED, DISTANCE_CLEAN, Hand_wash_status
                    log_writer.writerow([objectID,centroid[0],centroid[1],int(distance_bed),int(distance_clean),int(distance_clean_alchol),int(hand_wash_status),int(personal_status)])
                #cv2.putText(img, "Counter:", (1400, 90), cv2.FONT_HERSHEY_PLAIN, 2, (0,255,255), 2, cv2.LINE_AA)
                #cv2.putText(img, str(counter_msg), (1550, 90), cv2.FONT_HERSHEY_PLAIN, 2, (0,255,255), 2, cv2.LINE_AA)
                #cv2.putText(img, "Fail:", (1590, 90), cv2.FONT_HERSHEY_PLAIN, 2, (0,255,255), 2, cv2.LINE_AA)
                #cv2.putText(img, str(fail_msg), (1660, 90), cv2.FONT_HERSHEY_PLAIN, 2, (0,255,255), 2, cv2.LINE_AA)
                #cv2.putText(img, "Pass:", (1700, 90), cv2.FONT_HERSHEY_PLAIN, 2, (0,255,255), 2, cv2.LINE_AA)
                #cv2.putText(img, str(pass_msg), (1790, 90), cv2.FONT_HERSHEY_PLAIN, 2, (0,255,255), 2, cv2.LINE_AA)       
                if(restart_flag == False):        
                    if show_fps:
                        img = draw_help_and_fps(img, fps)
                    cv2.imshow(WINDOW_NAME, img)
                    frame_buffer += 1
                    cv2.setMouseCallback(WINDOW_NAME,pixel_info)  #Receive mouse click on HSV_Picker
                    toc = time.time()
                    curr_fps = 1.0 / (toc - tic)
                    # calculate an exponentially decaying average of fps number
                    fps = curr_fps if fps == 0.0 else (fps*0.9 + curr_fps*0.1)
                    tic = toc
                    if(frame_buffer == frame_reset_thres):
                        #Resolving camera slowwing down issue, force reset after thres frame
                        restart_flag = True
                        frame_buffer = 0

            else:
                print("None Image  --> None Buff = {}".format(none_buff))
                none_buff+=1
                if(none_buff == 1000):
                    print("[SYSTEM] VSTARCAMERA Restart")
                    cam.stop()  # terminate the sub-thread in camera
                    #tf_sess.close()
                    #tf.reset_default_graph()
                    #tf.contrib.keras.backend.clear_session()
                    cam.release() 
                    restart_flag = True
                    none_buff = 0
                    #img = None
                    cv2.destroyAllWindows()       

            if(restart_flag == False):
                key = cv2.waitKey(1)
                if key == 27:  # ESC key: quit program
                    break
                elif key == ord('H') or key == ord('h'):  # Toggle help/fps
                    show_fps = not show_fps
                elif key == ord('F') or key == ord('f'):  # Toggle fullscreen
                    full_scrn = not full_scrn
                    set_full_screen(full_scrn)

                

        #client.loop_start()
        #client.loop_forever()
    

def main():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    # Ask tensorflow logger not to propagate logs to parent (which causes
    # duplicated logging)
    logging.getLogger('tensorflow').propagate = False
    global args #restart issue
    args = parse_args()
    logger.info('called with args: %s' % args)

    # build the class (index/name) dictionary from labelmap file
    logger.info('reading label map')
    cls_dict = read_label_map(args.labelmap_file)

    pb_path = './data/{}_trt.pb'.format(args.model)
    log_path = './logs/{}_trt'.format(args.model)
    if args.do_build:
        logger.info('building TRT graph and saving to pb: %s' % pb_path)
        build_trt_pb(args.model, pb_path)

    logger.info('opening camera device/file')
    cam = Camera(args)
    cam.open()
    if not cam.is_opened:
        sys.exit('Failed to open camera!')

    logger.info('loading TRT graph from pb: %s' % pb_path)
    trt_graph = load_trt_pb(pb_path)

    logger.info('starting up TensorFlow session')
    tf_config = tf.ConfigProto()
    tf_config.gpu_options.allow_growth = True
    #tf_sess = tf.Session(config=tf_config, graph=trt_graph) -- Vincent
    #Solve : "unable to satfisfy explicit device /dev/CPU:0 -- Vincent
    tf_sess = tf.Session(config=tf.ConfigProto(allow_soft_placement=True,log_device_placement=True),graph=trt_graph)
    if args.do_tensorboard:
        logger.info('writing graph summary to TensorBoard')
        write_graph_tensorboard(tf_sess, log_path)

    logger.info('warming up the TRT graph with a dummy image')
    od_type = 'faster_rcnn' if 'faster_rcnn' in args.model else 'ssd'
    dummy_img = np.zeros((720, 1280, 3), dtype=np.uint8)
    _, _, _ = detect(dummy_img, tf_sess, conf_th=.3, od_type=od_type)

    cam.start()  # ask the camera to start grabbing images
    # grab image and do object detection (until stopped by user)
    logger.info('starting to loop and detect')
    vis = BBoxVisualization(cls_dict)
    open_display_window(cam.img_height, cam.img_width)
    #<<----------------------------------Vincent---------------------------------->>#  
    print("[INFO] Version: HT-002")                        #Vincent 
    print("[INFO]Screen Dimensions (H,W) =",cam.img_height,"x",cam.img_width)
    #Low resolution RTSP: 360 x 640
    #<<----------------------------------Vincent---------------------------------->>#
    result=loop_and_detect(cam, tf_sess, args.conf_th, vis, od_type=od_type)
    logger.info('cleaning up')
    cam.stop()  # terminate the sub-thread in camera
    tf_sess.close()
    cam.release()
    cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
