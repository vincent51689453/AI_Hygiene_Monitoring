import csv
import numpy as np
import matplotlib.pyplot as plt
import cv2
from mpl_toolkits.mplot3d import Axes3D
from matplotlib import cm
import os
import sqlite3
from enum import Enum
import timeit
import time
import paho.mqtt.client as mqtt

#Disable mqtt when testing
enable_mqtt = True
previous_personal_statement = 0
previous_target_id = 0
#Systm Life Counter
SysLife = 0
background = []
#Green pixel for label
label_pixel_color = (0,255,0)
#Number of Total Data
total_data = 0
#Raw ID data list
ID_buffer_list=[]
#A list to store (x,y,distance_bed,distance_clean,hand_wash)
Position_list=[]
#Report Output (text file)
Monitor_Report = 0
#SQLite Database
SQL_Database = 0
#Filters
class Advanced_noise_filter(Enum):
    In_Out_Filter_dir = 1
    In_Out_Filter_no_dir = 2


def get_current_time():
    t = time.localtime()
    current_time = time.strftime("%H:%M:%S",t)
    #print("[INFO] System Time->",current_time)
    hour_str = current_time[0]+current_time[1]
    minutes_str = current_time[3]+current_time[4]
    seconds_str = current_time[6]+current_time[7]
    #print("[INFO] Hour="+hour_str+" Minutes="+minutes_str+" Seconds="+seconds_str)
    return int(hour_str),int(minutes_str),int(seconds_str)

def scheduler():
    time.sleep(10)
    return True

def background_creation(height,width):
    blank_image = np.zeros((height,width,3), np.uint8)
    return blank_image

def section_creation():
    global background
    #Patient Zone (for Room_Hygiene_Demo_12_5fps.mp4)
    #zone_x_min_patient,zone_y_min_patient,zone_x_max_patient,zone_y_max_patient = 840,500,1300,1000
    #Cleaning Zone (for Room_Hygiene_Demo_12_5fps.mp4)
    #zone_x_min_clean,zone_y_min_clean,zone_x_max_clean,zone_y_max_clean = 300,416,580,680
    #Entrence Zone (for Room_Hygiene_Demo_12_5fps.mp4)
    #zone_x_min_door,zone_y_min_door,zone_x_max_door,zone_y_max_door = 1200,140,1300,380   
    #Draw Paitent Zone

    #Bondary boxes for video demo
    #Patient Zone (RTSP_Room_View_Ready.mp4)
    #zone_x_min_patient,zone_y_min_patient,zone_x_max_patient,zone_y_max_patient = 600,500,1000,1000
    #Cleaning Zone (RTSP_Room_View_Ready.mp4)
    #zone_x_min_clean,zone_y_min_clean,zone_x_max_clean,zone_y_max_clean = 1600,500,1900,820
    #Entrence Zone (RTSP_Room_View_Ready.mp4)
    #zone_x_min_door,zone_y_min_door,zone_x_max_door,zone_y_max_door = 450,140,730,480  
    #Alcohol
    #zone_x_min_alchol,zone_y_min_alchol,zone_x_max_alchol,zone_y_max_alchol = 300+800,200+300,350+800,270+300



    #Boundary boxes for RTSP (low resolution)
    zone_x_min_patient,zone_y_min_patient,zone_x_max_patient,zone_y_max_patient = 186,222,327,353
    zone_x_min_clean,zone_y_min_clean,zone_x_max_clean,zone_y_max_clean = 490,147,627,338
    zone_x_min_door,zone_y_min_door,zone_x_max_door,zone_y_max_door = 70,27,171,196
    zone_x_min_alchol,zone_y_min_alchol,zone_x_max_alchol,zone_y_max_alchol = 278,156,300,193

    #Draw Paitent Zone
    color_patient = (255,102,255)
    cv2.rectangle(background,(zone_x_min_patient,zone_y_min_patient),(zone_x_max_patient,zone_y_max_patient),color_patient,2)
    mid_x_patient = int((zone_x_min_patient+zone_x_max_patient)/2.0)
    mid_y_patient = int((zone_y_min_patient+zone_y_max_patient)/2.0)
    cv2.circle(background,(mid_x_patient,mid_y_patient),4,color_patient,-1)
    cv2.putText(background,"Patient",(mid_x_patient-40,mid_y_patient-20),cv2.FONT_HERSHEY_SIMPLEX,0.5,color_patient,1)
    #Draw Cleaning Zone
    color_clean = (255,255,51)
    cv2.rectangle(background,(zone_x_min_clean,zone_y_min_clean),(zone_x_max_clean,zone_y_max_clean),color_clean,2)
    mid_x_clean = int((zone_x_min_clean+zone_x_max_clean)/2.0)
    mid_y_clean = int((zone_y_min_clean+zone_y_max_clean)/2.0)
    cv2.circle(background,(mid_x_clean,mid_y_clean),4,color_clean,-1)
    cv2.putText(background,"Cleaning Zone",(mid_x_clean-120,mid_y_clean-20),cv2.FONT_HERSHEY_SIMPLEX,0.5,color_clean,1)
    #Drawing Entrence 
    color_door = (127,0,255)
    cv2.rectangle(background,(zone_x_min_door,zone_y_min_door),(zone_x_max_door,zone_y_max_door),color_door,2)
    mid_x_door = int((zone_x_min_door+zone_x_max_door)/2.0)
    mid_y_door = int((zone_y_min_door+zone_y_max_door)/2.0)
    cv2.circle(background,(mid_x_door,mid_y_door),4,color_door,-1)
    cv2.putText(background,"Entrance",(mid_x_door-30,mid_y_door-20),cv2.FONT_HERSHEY_SIMPLEX,0.5,color_door,2) 
    #Drawing Alchohol
    cv2.rectangle(background, (zone_x_min_alchol,zone_y_min_alchol),(zone_x_max_alchol,zone_y_max_alchol),(255,255,51),2)            
    zone_x_alchol = int((zone_x_min_alchol+zone_x_max_alchol)/2.0)
    zone_y_alchol = int((zone_y_min_alchol+zone_y_max_alchol)/2.0)
    cv2.circle(background, (zone_x_alchol, zone_y_alchol), 4, (255,255,51), -1)
    cv2.putText(background, "CLEANING ZONE", (zone_x_alchol-30, zone_y_alchol-20),cv2.FONT_HERSHEY_SIMPLEX, 0.5,(255,255,51), 1)


    #Incoming Detection (for Room_Hygiene_Demo_12_5fps.mp4)
    #zone_x_min_in,zone_y_min_in,zone_x_max_in,zone_y_max_in = 600,140,1180,420

    #Incoming Detection (RTSP_Room_View_Ready.mp4)
    zone_x_min_in,zone_y_min_in,zone_x_max_in,zone_y_max_in = 30,65,140,200
    color_in = (192,192,192)
    cv2.rectangle(background,(zone_x_min_in,zone_y_min_in),(zone_x_max_in,zone_y_max_in),color_in,2) 
    #Outcoming Detection (for Room_Hygiene_Demo_12_5fps.mp4)
    #zone_x_min_out,zone_y_min_out,zone_x_max_out,zone_y_max_out = 900,160,580,600

    #Outcoming Detection (RTSP_Room_View_Ready.mp4)
    zone_x_min_out,zone_y_min_out,zone_x_max_out,zone_y_max_out = 88,65,412,180
    color_out = (102,178,255)
    cv2.rectangle(background,(zone_x_min_out,zone_y_min_out),(zone_x_max_out,zone_y_max_out),color_out,2)

def id_frequency_transform():
    global ID_buffer_list,total_data 
    with open('./path_log.csv') as log_file:
        log_analyzer = csv.reader(log_file)       
        for row in log_analyzer:
            #Filtering temporary / fake ID which only appear for a short period of time
            #Row = ID,x,y,distance_patient,distance_clean
            ID_buffer_list.append(row[0])
            total_data+=1           
    #Assume the datasets must not excede 50 id index
    max_id = 2000
    id_counter = 0
    #An array which store the mapping of index and frequency
    #ID_buffer_list_sort[2] = 10
    #ID 2 appeared for 10 times
    ID_buffer_list_sort = []
    while(id_counter<max_id):
        i = 0
        frequency = 0
        while(i<total_data):
            if(int(ID_buffer_list[i])==id_counter):
                frequency+=1
            i+=1
        ID_buffer_list_sort.append(frequency)
        id_counter+=1
    i = 0
    #print("[DEBUG] Total Number Of Data =",total_data)
    check = 0
    while(i<len(ID_buffer_list_sort)):
        #print("[DEBUG] ID:%d => Frequency:%d"%(i,ID_buffer_list_sort[i]))
        check += ID_buffer_list_sort[i]
        i+=1
    #print("[DEBUG] Verifying =",check)
    if(check == total_data):
        #print("[INFO] Data Fetching Complete")
        return True,ID_buffer_list_sort
    else:
        #print("[INFO] Data Broken")
        return False,ID_buffer_list_sort

def id_filtering(id_list,threshold,advanced_filter,filter_type):
    i = 0
    valid=0
    output_list = []       
    while(i<len(id_list)):
        if(advanced_filter==True):
            if(filter_type==Advanced_noise_filter.In_Out_Filter_dir):
                """
                    In Out Filter Algorithm (Directional)
                    Algo: Check the ID starts from Incoming zone and leave through Outcoming zone.
                    Output: advanced_filter_output -> True: valid or False: invalid
                """
                advanced_filter_output = False
                valid_income = False
                valid_outcome = False
                #print("[INFO] In Out Filter Chosen!")
                #print("[INFO] Advanced filter Activated  --> ID =",i)
                global background
                #Incoming Detection
                zone_x_min_in,zone_y_min_in,zone_x_max_in,zone_y_max_in = 30,65,140,250
                #Outcoming Detection
                zone_x_min_out,zone_y_min_out,zone_x_max_out,zone_y_max_out = 88,65,412,265
                with open('./path_log.csv') as filter_x:
                    log_filter_x = csv.reader(filter_x)
                    for row_x1 in log_filter_x:
                        if(i==int(row_x1[0])):
                            if(valid_income==False):
                                if((int(row_x1[1])>=zone_x_min_in)and(int(row_x1[1])<=zone_x_max_in)and(int(row_x1[2])>=zone_y_min_in)and(int(row_x1[2])<=zone_y_max_in)):
                                    #Once valid_income = True, there is no necesscity to check anymore
                                    #print("[DEBUG] Valid Income Detected!")
                                    valid_income = True
                            if(valid_outcome==False):
                                if((int(row_x1[1])>=zone_x_min_out)and(int(row_x1[1])<=zone_x_max_out)and(int(row_x1[2])>=zone_y_min_out)and(int(row_x1[2])<=zone_y_max_out)):
                                    #Once valid_outcome = True, there is no necesscity to check anymore
                                    #print("[DEBUG] Valid Outcome Detected!")
                                    valid_outcome = True    
                if((valid_income==True)and(valid_outcome==True)):
                    #If the ID enter from "entrence" and leave from "entrence", it is a valid ID
                    advanced_filter_output=True                     
                #Filtered by frequencies of apperance and advanced filter
                if((id_list[i]>=threshold)and(advanced_filter_output==True)):
                    output_list.append(id_list[i])
                    valid+=1
                else:
                    output_list.append(0)
            if(filter_type==Advanced_noise_filter.In_Out_Filter_no_dir):
                """
                    In Out Filter Algorithm (Non-directional)
                    Algo: Check the ID starts enter and leave by entrence. There is no specific incoming/outcoming zone
                    Output: advanced_filter_output_2 -> True: valid or False: invalid

                    Phase 0: Initial Phase
                    Phase 1: ID is inside detection zone
                    Phase 2: ID leaves inside detection zone
                    Phase 3: ID is inside detection zone again
                """ 
                #Is it a valid ID? True for Yes
                advanced_filter_output_2 = False
                phase_counter = 0
                #Detection Zone(for Room_Hygiene_Demo_12_5fps.mp4)
                #zone_x_min_in,zone_y_min_in,zone_x_max_in,zone_y_max_in = 600,140,1180,420
                #zone_x_min_out,zone_y_min_out,zone_x_max_out,zone_y_max_out = 900,160,1350,600
 
                #Detection Zone (for RTSP_Room_View_Read.mp4)
                #zone_x_min_out,zone_y_min_out,zone_x_max_out,zone_y_max_out = 600,160,1350,750
                #zone_x_min_in,zone_y_min_in,zone_x_max_in,zone_y_max_in = 300,140,620,600
                #print("[INFO] In Out Filter Advanced Activated  --> ID =",i)

                #Detection zone for rtsp (low resolution)
                zone_x_min_in,zone_y_min_in,zone_x_max_in,zone_y_max_in = 30,65,140,200
                zone_x_min_out,zone_y_min_out,zone_x_max_out,zone_y_max_out = 88,65,412,180
                with open('./path_log.csv') as filter_x_adv:
                    log_filter_x_adv = csv.reader(filter_x_adv)
                    for row_x1_adv in log_filter_x_adv:
                        involved = False
                        advanced_filter_output_2=False
                        if(i==int(row_x1_adv[0])):
                            #Check whether inside the detection zone
                            if(((int(row_x1_adv[1])>=zone_x_min_in)and(int(row_x1_adv[1])<=zone_x_max_in)and(int(row_x1_adv[2])>=zone_y_min_in)and(int(row_x1_adv[2])<=zone_y_max_in))or((int(row_x1_adv[1])>=zone_x_min_out)and(int(row_x1_adv[1])<=zone_x_max_out)and(int(row_x1_adv[2])>=zone_y_min_out)and(int(row_x1_adv[2])<=zone_y_max_out))):
                                    involved = True 
                            if(phase_counter==0):
                                if(involved==True):
                                    phase_counter+=1
                            elif(phase_counter==1):
                                if(involved==False):
                                    phase_counter+=1
                            elif(phase_counter==2):
                                if(involved==True):
                                    phase_counter+=1                         
                if(phase_counter==3):
                    advanced_filter_output_2=True 
                #print("[INFO] Resultant Filter State =",phase_counter)
                #print("[DEBUG] Advanced_filter_output_2 =",advanced_filter_output_2) 
                phase_counter = 0                          
                #Filtered by frequencies of apperance and advanced filter
                if((id_list[i]>=threshold)and(advanced_filter_output_2==True)):
                    output_list.append(id_list[i])
                    #print("Advanced FIlter Output Status=True")
                    valid+=1
                else:
                    #print("Advanced FIlter Output Status=False")
                    #print("Phase Counter = ",phase_counter)
                    output_list.append(0)         
        else:
            #Simply filtered by frequencies of apperance       
            if(id_list[i]>=threshold):
                output_list.append(id_list[i])
                valid+=1
            else:
                output_list.append(0)
        i+=1
    return valid,output_list

def read_localization_data(target_id):
    global Position_list
    Position_list = []
    with open('./path_log.csv') as log_file_x:
        log_analyzer_x = csv.reader(log_file_x) 
        id_filter = 0      
        for row_x in log_analyzer_x:
            #Storing the remaining data to anothe list(x,y,distance_bed,distance_clean,hand_wash)
            x = 1
            temp=[]
            if(target_id==int(row_x[0])):
                while(x <= 7):
                    temp.append(row_x[x])                
                    x+=1
                id_filter+=1
                Position_list.append(temp)

def report_config():
    global Monitor_Report,SQL_Database
    #Text File
    #Is file exist?  
    file_built = os.path.isfile('./output/report_summary.txt')
    if(file_built==True):
        #Append
        Monitor_Report = open("./output/report_summary.txt","a")
    else:
        #Create a new one
        Monitor_Report = open("./output/report_summary.txt","w")
        Monitor_Report.write("<--------------Hygiene Monitor Report-------------->\n")
    #SQLite Database
    #If .db is not found then a new database will be created
    SQL_Database = sqlite3.connect('./SQL_Database/HA_Hygiene.db')
    print("[INFO] Accesed Database successfully")

def reconstruction_2d(target_id,id_map):
    global Position_list,Monitor_Report,previous_target_id,previous_personal_statement
    currentPosition=[]
    previous_x = 0
    previous_y = 0
    #If hand washing detected = 1, else = 0
    hand_wash_flag = 0
    patient_threshold = 99
    distance_thres_clean = 120
    distance_thres_alchol = 85
    num_of_contact = 0
    valid_patient_counter,invalid_patient_counter = 0,0
    valid_exit_counter, invalid_exit_counter = 0,0 
    access_flag = False
    record_buffer=[]
    max_record = 0
    check_hand_record = False
    access_paitient_achor = False
    initial_lock = False
    personal_status = False
    counter = 0
    leave_confirm = False
    leave_confirm_counter = 0
    #Process all data of one single ID
    while(counter<len(Position_list)):
        currentPosition=Position_list[counter]
        centroid_x = int(currentPosition[0])
        centroid_y = int(currentPosition[1])
        distance_patient = int(currentPosition[2])
        distance_clean = int(currentPosition[3])
        distance_alchol = int(currentPosition[4])
        hand_wash_flag = int(currentPosition[5])
        personal_status = int(currentPosition[6])
        #print("Distance_Patient:",distance_patient)
        #print("Hand_wash_flag=",hand_wash_flag)           
        #Direct Display location on a 2D blank images
        #background[row(y),column(x)] = (r,g,b)
        pixel_offset=5
        background[centroid_y:(centroid_y+pixel_offset),centroid_x:(centroid_x+pixel_offset)] = label_pixel_color
        if(counter > 0):
            if(previous_target_id<target_id):
                #if(initial_lock == False):
                #Reset when id is different
                #    check_hand_record = False
                #    access_paitient_achor=False
                #    initial_lock = True
                check_hand_record = False
                access_paitient_achor = False
                    #print("For ID={}, personal_status={}".format(previous_target_id,previous_personal_statement))
                    #print("Valid_exit="+str(valid_exit_counter))
                    #print("Invalid_exit="+str(invalid_exit_counter))
            #By Pass first iteration
            #Connect all the points
            if(hand_wash_flag==1):
                #If hand washing action detected, display in Yellow Color
                cv2.arrowedLine(background,(previous_x,previous_y),(centroid_x,centroid_y),(0,255,255),1)
            if((distance_clean <= distance_thres_clean)or(distance_alchol <= distance_thres_alchol)):
                #Noted that the hand wash status can only pop up serval times during "hand washing" from Jetson Nano
                if(access_flag==False):
                    #Starting recording data when staff is next to cleaning zone
                    access_flag=True
                    print("access-point:",distance_clean)
                    #Start recording hand_wash_status
                record_buffer.append(hand_wash_flag)
            else:
                if(access_flag==True):
                    #End of contact
                    #Find out any hand wash record during contact
                    max_record = max(record_buffer)
                    print("record=",record_buffer)
                    if(max_record==1):
                        #Indicating whether there is hand washing record ?
                        check_hand_record = True
                        print("Record-Check = True")
                    else:
                        check_hand_record = False
                        print("Record-Check = False")
                    access_flag = False
            if(distance_patient<patient_threshold):
                #If the staff touches the patient, display in White Color
                #print("distance = ",distance_patient)
                #print(access_paitient_achor)
                cv2.arrowedLine(background,(previous_x,previous_y),(centroid_x,centroid_y),(255,255,255),1)
                if(access_paitient_achor==False):
                    #store all handwashing record until access patient
                    record_buffer=[]
                    print("Patient Contact Point:",str(distance_patient))
                    print("set")
                    access_paitient_achor = True
                    if(check_hand_record==True):
                        #Is there any hand washing record in the previous "cleaning zone"?
                        valid_patient_counter+=1
                        print("Valid Found+1!")
                    else:
                        invalid_patient_counter+=1
                        print("Invalid Found+1!")
            else:
                if(access_paitient_achor == True):
                    #Solve suddenly out-of-range threshold
                    if(leave_confirm==False):
                        leave_confirm = True
                        leave_confirm_counter = counter
                    #Solve suddenly out-of-range threshold
                    if(counter>leave_confirm_counter)and(leave_confirm==True):
                        print("reset")
                        access_paitient_achor = False
                        #Once finished contact patient, remove check hand record
                        check_hand_record = False
                        #Reset 
                        leave_confirm = False
                        leave_confirm_counter = 0


                if((hand_wash_flag==0)and(distance_patient>patient_threshold)):
                    #Others
                    cv2.arrowedLine(background,(previous_x,previous_y),(centroid_x,centroid_y),(255,255,0),1)
            #print("Current Personal status = {}".format(personal_status))
            previous_personal_statement =  personal_status
            previous_x=centroid_x
            previous_y=centroid_y
            previous_hand_wash_status = hand_wash_flag
            previous_target_id = target_id
        counter+=1
    #New ID is arranged to the report
    report_text = ("ID:"+str(id_map)+" Total Number of Contact:"+str(num_of_contact)+" Valid: "+str(999)+" Invalid:"+str(999)+"\n")
    Monitor_Report.write(report_text)
    #Basic 2D path reconstruction in black image 
    path_1="./output/2D_Path_Reconstruction_"
    path_2=str(target_id)
    path_3=".jpg"
    file_path=path_1+path_2+path_3     
    cv2.imwrite(file_path,background)
    print("[INFO] 2D Path Reconstruction of ID %d FINISHED"%(target_id))
    print("[INFO] Saved at ",file_path)
    print("Valid_patient="+str(valid_patient_counter))
    print("Invalid_patient="+str(invalid_patient_counter))
    #Check leaving room status
    if(personal_status == 1):
        valid_exit_counter=1
        invalid_exit_counter = 0
    else:
        invalid_exit_counter=1
        valid_exit_counter = 0
    print("valid_exit_counter="+str(valid_exit_counter))
    return valid_patient_counter,invalid_patient_counter,valid_exit_counter,invalid_exit_counter


def main():
    while True:
        global SysLife
        time_to_work_min = False
        time_to_work_min = scheduler()
        if(time_to_work_min == True):
            global total_data,ID_buffer_list,Position_list
            total_data = 0
            #Raw ID data list
            ID_buffer_list=[]
            #A list to store (x,y,distance_bed,distance_clean,hand_wash)
            Position_list=[]
            #MQTT Publisher for Dashboard
            if(enable_mqtt==True):
                client = mqtt.Client()
                client.connect("localhost",1883,60)
                client.loop_start()
            #Calculate Starting time of the alogrithm
            start_time = timeit.default_timer()
            global background,Monitor_Report,SQL_Database
            t = time.localtime()
            current_time = time.strftime("%H:%M:%S",t)
            print("[INFO] System Time->",current_time)
            ID_frequency_list = []
            #Transform IDs into frequency 
            transform,ID_frequency_list = id_frequency_transform()
            report_config()
            total_contact,valid_contact,invalid_contact=0,0,0  
            a,b,c,d = 0,0,0,0     
            mapped_id = 0
            if(transform == True): 
                valid_id_list=[]
                valid = 0
                #Frequency < 80 are defined as interference
                #Input Parameters: (id_frequency,threshold,advanced filer)
                valid,valid_id_list=id_filtering(ID_frequency_list,0,True,Advanced_noise_filter.In_Out_Filter_no_dir)
                print("[INFO] Number Of Valid ID:",valid)
                #print("[INFO] Filter Output:",valid_id_list)
                i = 0
                while(i<len(valid_id_list)):
                    if(valid_id_list[i]!=0):
                        #Create a black background (h,w)
                        background = background_creation(360,640)
                        #Create different regions in background image
                        section_creation()
                        read_localization_data(i)
                        a_1,b_1,c_1,d_1 = 0,0,0,0
                        a_1,b_1,c_1,d_1=reconstruction_2d(i,mapped_id)
                        #Incase this id did not contact patient
                        if((a_1 == 0)and(b_1==0)):
                            print("ignore")
                            d_1 = 0
                            c_1 = 0
                        print("id=",str(mapped_id))
                        print("a_1 =",str(a_1))
                        print("b_1 =",str(b_1))
                        print("c_1 =",str(c_1))
                        print("d_1 =",str(d_1)) 
                        SQL_Cursor = SQL_Database.cursor()
                        num_valid_contact,num_invalid_contact = 0,0
                        SQL_Cursor.execute("INSERT INTO STAFF_HYGIENE (staffID,valid,invalid) VALUES (%d,%d,%d)"%(mapped_id,num_valid_contact,num_invalid_contact))
                        SQL_Database.commit()
                        a+=a_1
                        b+=b_1
                        c+=c_1
                        print("d will be updated by {}".format(d_1))
                        d+=d_1
                        mapped_id+=1
                    i+=1
            report_text = ("SysTime->"+current_time+" Total ID detected:"+str(mapped_id)+" Total Valid Contact: "+str(valid_contact)+" Total Invalid Contact: "+str(invalid_contact)+"\n")
            #SysLife Counter (check substainability)
            SysLife+=1
            #MQTT Dashboard Update
            #mqtt_message =' { "Man-time" :' + str(mapped_id)+ \
            #    ', "valid_patient_counter" :'+ str(a)+ \
            #    ', "invalid_patient_counter" :'+str(b)+\
            #    ', "valid_exit_counter":'+str(c)+\
            #    ', "invalid_exit_counter":'+str(d) +\
            #    ', "syslife":'+str(SysLife) + '}'
            total_contact,sucess_rate = 0,0
            total_contact = a+b+c+d
            if(total_contact >0):
                sucess_rate = int(((a+c)/total_contact)*100)
            else:
                sucess_rate = 0
            mqtt_message =' { "total_count" :' + str(total_contact)+ \
                ', "valid_patient_counter" :'+ str(a)+ \
                ', "invalid_patient_counter" :'+str(b)+\
                ', "valid_exit_counter":'+str(c)+\
                ', "invalid_exit_counter":'+str(d) +\
                ', "success_rate":'+str(sucess_rate) +\
                ', "total_sucess":'+str(a+c) +\
                ', "total_fail":'+str(b+d) + '}'


            #mqtt_message =' { "Man-time" :' + str(mapped_id)+ ', "valid_patient_counter" :'+ str(10)+ ', "invalid_patient_counter" :'+str(20)+', "valid_exit_counter":'+str(30)+', "invalid_exit_counter":'+str(40) +', "syslife":'+str(SysLife) + '}'


            print("[INFO] MQTT Message:",mqtt_message)
            if(enable_mqtt==True):
                client.publish("MDSSCC/AIHH/gui_dashboard", mqtt_message)
                client.loop_stop()
                client.disconnect()
            #client.loop()
            #Insert Data to Database
            SQL_Cursor = SQL_Database.cursor()
            #Database Table: STAFF_HYGIENE [staffID,valid,invalid]
            #SQL_Database/SQL_Database_Display.py to display the results
            #Time information is added
            sql_systime = "'"+current_time+"'"
            SQL_Cursor.execute("INSERT INTO STAFF_HYGIENE (systime,totalContact,totalValid,totalInvalid) VALUES (%s,%d,%d,%d)"%(sql_systime,total_contact,valid_contact,invalid_contact))
            SQL_Database.commit()
            SQL_Database.close()
            print("[INFO] Database Record Inserted successfully")
            Monitor_Report.write(report_text)
            Monitor_Report.close()   
            print("[INFO] All valid reconstructions are finished")
            stop_time = timeit.default_timer()
            print("[INFO] Total RunTime:",stop_time-start_time,"s")
           
        else:
            t = time.localtime()
            current_time = time.strftime("%H:%M:%S",t)
            print("[INFO] System Time->",current_time)


if __name__ == "__main__":
   main()    
