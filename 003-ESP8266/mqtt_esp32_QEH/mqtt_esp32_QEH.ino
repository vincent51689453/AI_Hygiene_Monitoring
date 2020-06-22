#include <WiFi.h>
#include <WiFiClient.h>
#include <WiFiServer.h>
#include <WiFiUdp.h>
//#include <ESP8266WiFi.h>


    int T=0;

int interval=350;//set reading period
int j=50;
int A,B,C,D;
int i=0;
long result;
int led=50;
int off=0;
int bodym=28000;
int offbedv=4200;
int lastSensor=0;

int Status;
int LastStatus;

long int Timev=0;
int buttonstate=0;

#include <PubSubClient.h>  
#define LED_BUILTIN 2

// Update these with values suitable for your network.

const char* ssid = "MDSSC"; //"IoTDemo" //"EiA-Mbot"  //"iHome_Xiaomi_D484"
const char* password = "42004200"; //"ihomepass"
const char* mqtt_server = "192.168.68.100"; //"broker.mqtt-dashboard.com";  //158.132.153.178  192.168.31.181

WiFiClient espClient;
PubSubClient client(espClient);
long lastMsg = 0;
char msg[50];
int value = 0;

String ipAddress;
String macAddr;
const char* mqttTopic="MDSSCC/AIHH/SENSOR";   //CSYS

int buttonInput = 23; //Button input D23

void setup() {
  pinMode(LED_BUILTIN, OUTPUT);     // Initialize the BUILTIN_LED pin as an output
   pinMode(buttonInput, INPUT_PULLUP);     // Button input D23


Serial.begin(115200);
  setup_wifi();
  client.setServer(mqtt_server, 1883);
  client.setCallback(callback);
}


void setup_wifi() {

  delay(10);
  // We start by connecting to a WiFi network
  Serial.printf("\nConnecting to %s\n", ssid);
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.printf("\nWiFi connected\n");
  ipAddress=WiFi.localIP().toString();
  Serial.printf("\nIP address: %s\n", ipAddress.c_str());
  macAddr=WiFi.macAddress();
  Serial.printf("MAC address: %s\n", macAddr.c_str());
}

void callback(char* topic, byte* payload, unsigned int length) {
  Serial.print("Message arrived [");
  Serial.print(topic);
  Serial.print("] ");
  for (int i = 0; i < length; i++) {
    Serial.print((char)payload[i]);
  }
  Serial.println();

  // Switch on the LED if an 1 was received as first character
  if ((char)payload[0] == '1') {
    digitalWrite(LED_BUILTIN, HIGH);   // Turn the LED on (Note that LOW is the voltage level
    // but actually the LED is on; this is because
    // it is acive low on the ESP-01)
  } else {
    digitalWrite(LED_BUILTIN, LOW);  // Turn the LED off by making the voltage HIGH
  }

}

void reconnect() {
  // Loop until we're reconnected
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    // Attempt to connect
    //if (client.connect("ESP8266Client")) {
    if (client.connect(macAddr.c_str())) {
      Serial.println("Connected");
      // Once connected, publish an announcement...
      snprintf(msg, 75, "ESP32 Smart Sensor (%s) is READY", ipAddress.c_str());
      client.publish(mqttTopic, "Connected!!!");
      // ... and resubscribe
      client.subscribe(mqttTopic);
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      // Wait 5 seconds before retrying
      delay(5000);
    }
  }
}
void loop() {
  int press_status = 0;
  buttonstate=digitalRead(23);
  if (!client.connected()) {
    reconnect();
  }
  press_status = analogRead(32);
  Serial.print("Press_status=");
  Serial.println(press_status);
  if(press_status>=3300)
  {
    Serial.println("Button Pressed");
    client.publish(mqttTopic, "PRESS");    
  }else{
    
    client.publish(mqttTopic,"RELEASE");
  }
  //if(buttonstate == LOW)
  //{
  //  Serial.println("Button Pressed");
  //  client.publish(mqttTopic, "PRESS");
  //}else{
  //  client.publish(mqttTopic,"RELEASE");
  //}

  delay(500);
  client.loop();

}
