SYSTEM_MODE(MANUAL);

#include <ESP8266WiFi.h>
#include <PubSubClient.h>

char SSID[] = "mywifi";
char wifikey[] = "somepassword";

char mqtt_server[] = "192.0.2.1";
int mqtt_port = 1883;
char mqtt_user[] = "mqttuser";
char mqtt_pass[] = "mqttpass";

char command_topic[] = "home/garage_door/set";
char state_topic[] = "home/garage_door";
char ont_command_topic[] = "home/ont/set";
char ont_state_topic[] = "home/ont";

int sensor = 7;
int relay = 8;
int ont_relay = 9;

WiFiClient espClient;
PubSubClient client(espClient);

int sensor_status = 0;
int last_status = 0;
long last_update = 0;
int command_cooldown = 15000;
long last_command = 0;

void setup() {
  pinMode(LED_BUILTIN, OUTPUT);
  pinMode(sensor, INPUT);
  pinMode(relay, OUTPUT);
  pinMode(ont_relay, OUTPUT);
  
  // Make sure relay is off
  digitalWrite(relay, HIGH);
  digitalWrite(ont_relay, HIGH);

  Serial.begin(115200);
  
  //don't save these details
  WiFi.persistent(false);

  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(SSID);

  //start the WiFi connection process
  WiFi.begin_internal(SSID, wifikey, 0, NULL);

  //wait for WiFi to connect
  while (WiFi.status() != WL_CONNECTED)
  {
    digitalWrite(LED_BUILTIN, HIGH);
    delay(100);
    digitalWrite(LED_BUILTIN, LOW);
    delay(100);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("WiFi connected");
  Serial.println("IP address: ");
  Serial.println(WiFi.localIP());

  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback);

  // Set initial status
  sensor_status = digitalRead(sensor);
  last_status = sensor_status;
}

void press_button() {
  long now = millis();
  
  // Don't allow rapid fire commands
  if (now - last_command > command_cooldown) {
    digitalWrite(relay, LOW);
    delay(500);
    digitalWrite(relay, HIGH);

    last_command = now;
  } else {
    long seconds_left = command_cooldown - (now - last_command);
    Serial.print("Command cooldown in effect! Time left: "); 
    Serial.print(seconds_left/1000);
    Serial.println("s");
  }
}

void update_status(int state) {
  if (state == HIGH) {
    Serial.println("Door Status: open");
    client.publish(state_topic, "open");
  } else if (state == LOW) {
    Serial.println("Door Status: closed");
    client.publish(state_topic, "closed");
  } else {
    Serial.println("Door Status: unknown!");
  }
}

void callback(char* topic, byte* payload, unsigned int length) {
  Serial.print("Message arrived [");
  Serial.print(topic);
  Serial.print("] ");
  for (int i = 0; i < length; i++) {
    Serial.print((char)payload[i]);
  }
  Serial.println();

  String strTopic = String((char*)topic);

  if (strTopic == command_topic) {
    payload[length] = '\0';
    String strPayload = String((char*)payload);
    
    // Switch on the LED if an 1 was received as first character
    if (strPayload == "open") {
      Serial.println("Command: Open Door");
      press_button();
    } else if (strPayload == "closed") {
      Serial.println("Command: Close Door");
      press_button();
    } else if (strPayload == "status") {
      Serial.println("Command: Door Status");
      update_status(digitalRead(sensor));
    } else {
      Serial.println("Unknown command");
    }
  } else if (strTopic == ont_command_topic) {
    payload[length] = '\0';
    String strPayload = String((char*)payload);

    if (strPayload == "on") {
      Serial.println("Command: ONT On");
      client.publish(ont_state_topic, "on", true);
      digitalWrite(ont_relay, HIGH);
    } else if (strPayload == "off") {
      Serial.println("Command: ONT off");
      client.publish(ont_state_topic, "off", true);
      digitalWrite(ont_relay, LOW);
    } else {
      Serial.println("Unknown command");
    }
  }
}

void reconnect() {
  // Loop until we're reconnected
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    // Attempt to connect
    if (client.connect("ESP8266Client", mqtt_user, mqtt_pass)) {
      Serial.println("connected");
      // Once connected, publish state
      update_status(digitalRead(sensor));
      // ... and resubscribe
      client.subscribe(command_topic);
      client.subscribe(ont_command_topic);
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
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  long now = millis();
  
  // Only read the sensor every 0.2s
  if (now - last_update > 200) {
    sensor_status = digitalRead(sensor);
    
    if (sensor_status != last_status) {
      last_status = sensor_status;
      update_status(sensor_status);
    }

    last_update = now;
  }
}
