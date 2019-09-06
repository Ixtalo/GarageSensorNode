/// AST, 08/2019
#include <SoftwareSerial.h>
#include <DHT.h>  // https://github.com/adafruit/DHT-sensor-library
#include <Sleep_n0m1.h> // https://github.com/n0m1/Sleep_n0m1


#define DHTPIN 2
#define DHTTYPE DHT22
const DHT dht(DHTPIN, DHTTYPE);

const SoftwareSerial mySerial(10, 11); // RX, TX
const Sleep sleep;
#define SLEEPTIME 60000 // sleep time in ms


#define REEDSWITCH_PIN 4  // D4


struct Data 
{
  unsigned int light = -1;
  float temperature = -1;
  float humidity = -1;
  bool reed_state = false;
};


void setup()
{
  pinMode(LED_BUILTIN, OUTPUT);
  Serial.begin(9600);
  mySerial.begin(9600);
  dht.begin();

  // wait time for debugging
  delay(5000);
  Serial.println("ready!");
}

void print(const Stream& stream, const Data& data)
{
  stream.print("**");
  stream.print("L:");
  stream.print(data.light);
  stream.print(";");
  stream.print("H:");
  stream.print(data.humidity);
  stream.print(";");
  stream.print("T:");
  stream.print(data.temperature);
  stream.print(";");
  stream.print("R:");
  stream.print(data.reed_state);
  stream.print("$$");
}

void loop()
{
  delay(100); //delay to allow serial output to be ready after wake up

  digitalWrite(LED_BUILTIN, HIGH); // turn the LED on
  Data data;

  // read DHT22
  data.humidity = dht.readHumidity();
  data.temperature = dht.readTemperature();

  // read LDR - Light Dependent Resistor at A0
  data.light = analogRead(A0);

  // read reed switch status (digital on/off, 0/1)
  data.reed_state = digitalRead(REEDSWITCH_PIN);

  digitalWrite(LED_BUILTIN, LOW); // turn the LED off


  // normal serial console output
  print(Serial, data);
  Serial.println();
  // virtual serial console output
  print(mySerial, data);


  // sets the Arduino into power Down Mode sleep
  // The most power saving, all systems are powered down except the watch dog timer and external reset
  Serial.println("Going to sleep...");
  sleep.pwrDownMode(); //set sleep mode
  sleep.sleepDelay(SLEEPTIME);
}
