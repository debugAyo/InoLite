int counter = 0;

void setup() {
  Serial.begin(9600); // Opens the communication line
}

void loop() {
  Serial.print("Hello from Arduino! Count: ");
  Serial.println(counter);
  counter++;
  delay(1000); // Wait 1 second before sending the next line
}