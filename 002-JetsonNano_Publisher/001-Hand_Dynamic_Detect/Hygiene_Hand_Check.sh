#Runnign Demo Video - Custom Hand Training
#python3 Hygiene_Hand_Check_Publisher.py --file --filename ./videos/Hand_Wash_Demo_001.mp4 --model ssd_mobilenet_v1_coco --labelmap third_party/models/research/object_detection/data/labelmap_hand.pbtxt --num-classes 1 --confidence 0.7 --build

#Running Demo Video - Pretrained
#python3 Hygiene_Hand_Check.py --file --filename ./videos/Hand_Wash_Demo_001.mp4 --model ssd_mobilenet_v1_egohands  --labelmap data/egohands_label_map.pbtxt --num-classes 1 --confidence 0.7 --build


#Running ON Board Camera - Custom Hand Detection
#python3 Hygiene_Hand_Check_Publisher.py --model ssd_mobilenet_v1_coco --labelmap third_party/models/research/object_detection/data/labelmap_hand.pbtxt --num-classes 1 --confidence 0.5 --build

#Running ON Board Camera - Pretrained Hand Detection
python3 Hygiene_Hand_Check.py --model ssd_mobilenet_v1_coco --model ssd_mobilenet_v1_egohands  --labelmap data/egohands_label_map.pbtxt --num-classes 1 --confidence 0.7 
