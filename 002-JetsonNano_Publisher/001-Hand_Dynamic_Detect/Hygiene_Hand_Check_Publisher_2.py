"""camera_tf_trt.py

This is a Camera TensorFlow/TensorRT Object Detection sample code for
Jetson TX2 or TX1.  This script captures and displays video from either
a video file, an image file, an IP CAM, a USB webcam, or the Tegra
onboard camera, and do real-time object detection with example TensorRT
optimized SSD models in NVIDIA's 'tf_trt_models' repository.  Refer to
README.md inside this repository for more information.

This code is written and maintained by JK Jung <jkjung13@gmail.com>.
"""


import sys
import time
import logging
import argparse

import numpy as np
import cv2
import tensorflow as tf
import tensorflow.contrib.tensorrt as trt
import math

from utils.camera import add_camera_args, Camera
from utils.od_utils import read_label_map, build_trt_pb, load_trt_pb, \
                           write_graph_tensorboard, detect
#from utils.visualization import BBoxVisualization
import math

import paho.mqtt.client as mqtt
import time
client = mqtt.Client()
client.connect("192.168.68.100",1883)
#Global Parameters -- Vincent
ALPHA = 0.5
FONT = cv2.FONT_HERSHEY_PLAIN
TEXT_SCALE = 1.0
TEXT_THICKNESS = 1
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
zone_x_min_clean,zone_y_min_clean,zone_x_max_clean,zone_y_max_clean = 50,50,400,400
center_x_old,center_y_old = 0,0
delay_counter = 0 
#Global Parameters -- Vincent

# Constants
DEFAULT_MODEL = 'ssd_mobilenet_v1_coco'
DEFAULT_LABELMAP = 'third_party/models/research/object_detection/' \
                   'data/mscoco_label_map.pbtxt'
WINDOW_NAME = 'AI-Hygiene-Check[Hand Wash]'
BBOX_COLOR = (0, 255, 0)  # green

Clean_flag = False


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
    cv2.setWindowTitle(WINDOW_NAME, 'AI-Hygiene-Check[Hand Wash]')


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
        global zone_x_min_clean,zone_y_min_clean,zone_x_max_clean,zone_y_max_clean
        global center_x_old,center_y_old,delay_counter,box_wash
        center_x,center_y = 0,0
        #Number of similar positions of hands detected to identify "WASH"
        max_wash = 2         
        related_motion = False
        global Clean_flag
        for bb, cf, cl in zip(box, conf, cls):
            cl = int(cl)
            y_min, x_min, y_max, x_max = bb[0], bb[1], bb[2], bb[3]
            #Effective Area Detection
            #if((x_min>zone_x_min_clean)and(x_max<zone_x_max_clean)and(y_min>zone_y_min_clean)and(y_max<zone_y_max_clean)):
            cv2.rectangle(img, (x_min, y_min), (x_max, y_max), (0,0,255), 2)
            txt_loc = (max(x_min+2, 0), max(y_min+2, 0))
            cls_name = self.cls_dict.get(cl, 'CLS{}'.format(cl))
            txt = '{} {:.2f}'.format(cls_name, cf)
            img = draw_boxed_text(img, txt, txt_loc, (0,0,255)) 
            center_x = int((x_min+x_max)/2)
            center_y = int((y_min+y_max)/2)
            cv2.circle(img, (center_x, center_y), 4, (0,0,255), -1)
            distance = int(math.sqrt((center_x-center_x_old)**2+(center_y-center_y_old)**2))
            print("Previous Center X:%d Center Y:%d"%(center_x_old,center_y_old))
            print("Current Center X:%d Center Y:%d"%(center_x,center_y))
            print("Mapping Distance:",distance)
            Clean_flag = True             
            center_x_old = center_x
            center_y_old = center_y  
            print("---------------------------------------------------------------------")            
        return img

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
    while True:
        global Clean_flag
        Clean_flag = False
        if cv2.getWindowProperty(WINDOW_NAME, 0) < 0:
            # Check to see if the user has closed the display window.
            # If yes, terminate the while loop.
            break
        img = cam.read()
        global zone_x_min_clean,zone_y_min_clean,zone_x_max_clean,zone_y_max_clean        
        img = img[zone_y_min_clean:zone_y_max_clean, zone_x_min_clean:zone_x_max_clean]
        overlay = img.copy()
        output = img.copy()
        overall = img.copy()

        cv2.rectangle(overlay, (zone_x_min_clean,zone_y_min_clean),(zone_x_max_clean,zone_y_max_clean),(153,255,153),-1)
        if img is not None:
            box, conf, cls = detect(img, tf_sess, conf_th, od_type=od_type)   
            print("Detection Matrix:",cls)  
            output = vis.draw_bboxes(img, box, conf, cls)                              
            if show_fps:
                output = draw_help_and_fps(img, fps)
            overall = cv2.addWeighted(overlay,0.2,output,1,0)
            if(Clean_flag == True):
                client.publish("MDSSCC/AIHH/SENSOR", "WASHED")
                print("washed!")     
            else:
                client.publish("MDSSCC/AIHH/SENSOR", "DIRTY")
            cv2.imshow(WINDOW_NAME, overall)
            toc = time.time()
            curr_fps = 1.0 / (toc - tic)
            # calculate an exponentially decaying average of fps number
            fps = curr_fps if fps == 0.0 else (fps*0.9 + curr_fps*0.1)
            tic = toc

        key = cv2.waitKey(1)
        if key == 27:  # ESC key: quit program
            break
        elif key == ord('H') or key == ord('h'):  # Toggle help/fps
            show_fps = not show_fps
        elif key == ord('F') or key == ord('f'):  # Toggle fullscreen
            full_scrn = not full_scrn
            set_full_screen(full_scrn)
        client.loop()
    

def main():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    # Ask tensorflow logger not to propagate logs to parent (which causes
    # duplicated logging)
    logging.getLogger('tensorflow').propagate = False

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
    print("Version:HW-001")  
    print("[INFO]Screen Dimensions (H,W) =",cam.img_height,"x",cam.img_width)
    #<<----------------------------------Vincent---------------------------------->>#
    result=loop_and_detect(cam, tf_sess, args.conf_th, vis, od_type=od_type)
    logger.info('cleaning up')
    cam.stop()  # terminate the sub-thread in camera
    tf_sess.close()
    cam.release()
    cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
