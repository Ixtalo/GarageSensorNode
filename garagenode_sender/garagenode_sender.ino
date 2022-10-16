/// AST, 08/2019
#include <SoftwareSerial.h>
#include <DHT.h>  // https://github.com/adafruit/DHT-sensor-library
#include <Sleep_n0m1.h> // https://github.com/n0m1/Sleep_n0m1

// sleep time in ms
#define SLEEPTIME 30000

// reed switches GPIO pins
#define SWITCH1_PIN 3  // D3
#define SWITCH2_PIN 4  // D4

// DHT22 GPIO pin
#define DHTPIN 2  // D2
#define DHTTYPE DHT22

const DHT dht(DHTPIN, DHTTYPE);
const SoftwareSerial mySerial(10, 11); // RX, TX
const Sleep sleep;

/////unsigned long lastMillis = 0;
/////unsigned long currentMillis;


struct Data 
{
  unsigned int light = -1;
  float temperature = -1;
  float humidity = -1;
  bool switch1 = false;
  bool switch2 = false;
};


void setup()
{
  pinMode(LED_BUILTIN, OUTPUT);
  Serial.begin(9600);
  mySerial.begin(9600);
  dht.begin();

  pinMode(SWITCH1_PIN, INPUT);
  pinMode(SWITCH2_PIN, INPUT);
  //////attachInterrupt(digitalPinToInterrupt(SWITCH_PIN), readAndPrint, CHANGE);

  // wait time for debugging
  delay(3000);
  Serial.println("ready!");
}

void print(const Stream& stream, const Data& data)
{
  // begin-marker
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

  stream.print("S1:");
  stream.print(data.switch1);
  stream.print(";");

  stream.print("S2:");
  stream.print(data.switch2);

  // end-marker
  stream.print("$$");
}

void readAndPrint()
{
/////  // must be before noInterrupts()
/////  // millis() internally makes a noInterrupts() and interrupts()
/////  currentMillis = millis();
/////
  // disable interrupts while reading and printing
  noInterrupts();
/////
/////  // check if function was called too often too fast
/////  unsigned long millisDiff = currentMillis - lastMillis;
/////  if (millisDiff < 100) {
/////    //Serial.print("too fast! ");
/////    //Serial.print(millisDiff);
/////    //Serial.println();
/////    delay(100);
/////    
/////    return; // interrupts() gets also re-enabled by millis()
/////  } 
/////
/////  // store current time
/////  lastMillis = currentMillis;

  delay(200); //delay to allow serial output to be ready after wake up

  digitalWrite(LED_BUILTIN, HIGH); // turn the LED on
  Data data;

  // read DHT22
  data.humidity = dht.readHumidity();
  data.temperature = dht.readTemperature();

  // read LDR - Light Dependent Resistor at A0
  data.light = analogRead(A0);

  // read switch status (digital on/off, 0/1)
  data.switch1 = !digitalRead(SWITCH1_PIN);
  data.switch2 = !digitalRead(SWITCH2_PIN);

  digitalWrite(LED_BUILTIN, LOW); // turn the LED off

  // normal serial console output
  print(Serial, data);
  Serial.println();
  
  // virtual serial console output
  print(mySerial, data);

  interrupts(); // re-enable interrupts
}



void loop()
{
  readAndPrint();

  Serial.println(F("sleeping..."));
  delay(100); //delay to allow serial to fully print before sleep

  // sets the Arduino into power Down Mode sleep
  // The most power saving, all systems are powered down except the watch dog timer and external reset
  sleep.pwrDownMode(); //set sleep mode
  // NOTE sleepDelay *and* sleepPinInterrupt does not work both at the same time!
  //////DOES NOT WORK! sleep.sleepPinInterrupt(SWITCH_PIN, CHANGE);
  sleep.sleepDelay(SLEEPTIME);  
}
