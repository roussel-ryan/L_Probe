//pin assignments
int stp=2; //pin connected to easydriver stp port
int dir=3; //pin connected to easydriver dir port
int pls=4; //pin location of positive limit switch
int plsanalog=A1; //pin to read analog voltage output of the positive limit switch
int zlsanalog=A2; //pin to read analog voltage output of the zero limit switch 
int zls=5; //pin location of zero limit switch 
int ms1=6;//pin to control step size 
int ms2=7;//pin to control step size 
//numerical values 
float disp; //initializing variable containing the current amount to be displaced
float pos; //initializing variable containing the current position of the probe
float stps; //initializing variable containing number of steps to be take
float perc; //initializing variable containing percentage of steps completed 
//strings 
String input; //initializing string to contain user displacement input 
char option; //initializing string to contain user option input 
String dispmessage; //initializing message to display number of millimeters about to be travelled
String stpsmessage; //initializing message to display number of steps about to be taken
String currlocmessage; //initializing message to display current location of probe
String percmessage; //initializing message to display percentage of steps completed 
//functions
void resetPins(); //function to set pin values to defaults 
void gotoZero(); //function to return the probe to its zero location
void backStep(); //function to step backwards 
void forwardStep(); //function to step forwards 
void Pulse(); //complete one pulse 
void clearSerial(); //clears serial buffer to take incoming input

void setup() {
  Serial.begin(9600);
  pinMode(stp,OUTPUT);
  pinMode(dir,OUTPUT);
  pinMode(ms1,OUTPUT);
  pinMode(ms2,OUTPUT);
  pinMode(pls,INPUT_PULLUP);
  pinMode(zls,INPUT_PULLUP);
  resetPins(); }

void loop() {  
  while (Serial.available()==0){}
  
  input=Serial.readString();
  float steps = input.toFloat();
  if (steps < 0.0){ //identify if stepping backwards
     //remove negative sign and return value as a float
    if (! backStep(-steps)){Serial.println("neg_limit");} else {Serial.println("normal");}
    }
  else if (steps > 0.0){ //identify if stepping forwards
    if (!forwardStep(steps)){Serial.println("pos_limit");} else {Serial.println("normal");}
    }
  else{} 
  resetPins();
}

bool forwardStep(float stps){
  digitalWrite(dir,HIGH);
  for(long x=0;x<stps;x++){
    if (analogRead(plsanalog)>=300){
      Pulse();}
    else if (analogRead(plsanalog)<300){
      digitalWrite(dir,LOW);
      while (analogRead(plsanalog)<300){
        Pulse(); }  
      return false; }}
  return true;
}
bool backStep(float stps){
  digitalWrite(dir,LOW);
  for(long y=0;y<stps;y++){
    if (analogRead(zlsanalog)>=300){
      Pulse();}
    else if (analogRead(zlsanalog)<300){
      digitalWrite(dir,HIGH);
      while (analogRead(zlsanalog)<300){
        Pulse(); }
      return false; }}
  return true;
}

void Pulse(){
  digitalWrite(stp,HIGH);
  delay(1);
  digitalWrite(stp,LOW);
  delay(1); }

void resetPins(){
  digitalWrite(stp,LOW);
  digitalWrite(dir,LOW);
  digitalWrite(ms1,LOW);
  digitalWrite(ms2,LOW);}

void clearSerial(){
  while (Serial.available()>0)
  {
    Serial.read(); 
  }
}
