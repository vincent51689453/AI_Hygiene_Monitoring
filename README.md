# AI_Hygiene_Monitoring

This project is mainly designed to monitorthe hygiene status of a clincal staff. By using object detection on **Nividia Jetson TX2**, it helps to track the movement of the staff under the view of a RTSP camera. Meanwhile, there is a **Nvidia Jetson Nano** which can help to detect "handwashing" motions to ensure the staff has been cleaned. Furthermore, there is a ESP8266 module for hand rub. All these modules are linked by MQTT throught WiFi. Meanwhile, the final statistical results are displayed in a node-red dashboard.

![image](https://github.com/vincent51689453/AI_Hygiene_Monitoring/blob/master/004-Git_Image/2D_Path_Reconstruction_1.jpg)

![image](https://github.com/vincent51689453/AI_Hygiene_Monitoring/blob/master/004-Git_Image/dashboard.png)
