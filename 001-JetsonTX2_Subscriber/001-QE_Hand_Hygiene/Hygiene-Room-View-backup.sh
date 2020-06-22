#Running Demo Video RTSP_Room_View_Ready.mp4
python3 Hygiene_Tracking_Room_Subscriber_backup.py --file --filename ./videos/RTSP_Room_View_Ready.mp4 --model ssd_mobilenet_v1_coco  --num-classes 1 --confidence 0.35


#Running Demo Video Room_Hygiene_Demo_12_5fps
#python3 Hygiene_Tracking_Room_Subscriber.py --file --filename ./videos/Room_Hygiene_Demo_12_5fps.mp4 --model ssd_mobilenet_v1_coco  --num-classes 1 --confidence 0.4

#Running RTSP Camera with default CNN (testing)
#python3 camera_tf_trt.py --rtsp --uri rtsp://admin:51689453@192.168.0.104:554/udp/av0_0 --model ssd_mobilenet_v1_coco  --num-classes 1 --confidence 0.4

#Running Hygiene Tracker with RTSP Camera
#python3 Hygiene_Tracking_Room_Subscriber.py --rtsp --uri rtsp://admin:51689453@192.168.0.112:554/udp/av0_0 --model ssd_mobilenet_v1_coco  --num-classes 1 --confidence 0.4

