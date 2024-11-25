import RPi.GPIO as GPIO
import I2C_LCD_driver
from time import sleep
import requests
import time
from mfrc522 import SimpleMFRC522 as reader
from flask import Flask, request, jsonify
import threading

app = Flask(__name__)
program_thread = None
stop_thread = False

LCD = I2C_LCD_driver.lcd()

GPIO.setmode(GPIO.BCM)  # choose BCM mode
GPIO.setwarnings(False)

GPIO.setup(17, GPIO.IN)  # set GPIO 17 as input for IR sensor
GPIO.setup(26, GPIO.OUT)  # set GPIO 26 as output for servo motor
GPIO.setup(4, GPIO.IN)  # set GPIO 4 as input for moisture sensor
GPIO.setup(25, GPIO.OUT)  # GPIO25 as Trig for ultrasonic sensor
GPIO.setup(27, GPIO.IN)  # GPIO27 as Echo for ultrasonic sensor
PWM = GPIO.PWM(26, 50)  # set 50Hz PWM output at GPIO26
GPIO.setup(24, GPIO.OUT)

TOKEN = "7486004594:AAEuUVq4_QcWx2no6ZmFatZzg8i8RInjrTY"
chat_id = "6748747083"
message = "The bin is full already. Please come and collect. Don't forget to bring the card!"
thanks = "Thank you for collecting the bin."

def getGpio():
    GPIO.cleanup()
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(17, GPIO.IN)  # set GPIO 17 as input for IR sensor
    GPIO.setup(26, GPIO.OUT)  # set GPIO 26 as output for servo motor
    GPIO.setup(4, GPIO.IN)  # set GPIO 4 as input for moisture sensor
    GPIO.setup(25, GPIO.OUT)  # GPIO25 as Trig for ultrasonic sensor
    GPIO.setup(27, GPIO.IN)  # GPIO27 as Echo for ultrasonic sensor

def distance():
    GPIO.output(25, 1)
    time.sleep(0.00001)
    GPIO.output(25, 0)

    StartTime = time.time()
    StopTime = time.time()
    while GPIO.input(27) == 0:
        StartTime = time.time()
    while GPIO.input(27) == 1:
        StopTime = time.time()
    ElapsedTime = StopTime - StartTime

    Distance = (ElapsedTime * 34300) / 2
    return Distance

def read_rfid(timeout=5):
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            id = reader().read_id_no_block()
            if id:
                return str(id)
        except Exception as e:
            print("Error reading RFID:", e)
        time.sleep(0.5)
    return None

def start_program(token):
    GPIO.cleanup()
    getGpio()
    global stop_thread
    stop_thread = False

    while not stop_thread:
        ultra_distance = distance()
        if GPIO.input(4):
            LCD.lcd_display_string("It's raining     ", 1)
            LCD.lcd_display_string("                ", 2)
            sleep(2)
            LCD.lcd_display_string("Bin cannot be   ", 1)
            LCD.lcd_display_string("opened          ", 2)
            sleep(2)
        elif ultra_distance < 5:
            LCD.lcd_display_string("Bin is full      ", 1)
            LCD.lcd_display_string("                ", 2)
            url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={message}"
            try:
                response = requests.get(url)
                print("Telegram message response:", response.json())
            except Exception as e:
                print("Error sending Telegram message:", e)
            collected = 0
            while collected == 0:
                GPIO.cleanup()
                collector = reader()
                id = collector.read_id_no_block()
                id = str(id)
                if id == "810585240464":
                    getGpio()
                    url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={thanks}"
                    response = requests.get(url)
                    print("Telegram message response:", response.json())
                    LCD.lcd_display_string("Thank You       ", 1)
                    collected = 1
                    sleep(2)
                    break
                else:
                    getGpio()
                    LCD.lcd_display_string("Bin is full      ", 1)
                    LCD.lcd_display_string("                ", 2)
                sleep(2)
        else:
            if GPIO.input(17) == 0:
                LCD.lcd_display_string("Dustbin is     ", 1)
                LCD.lcd_display_string("opened.         ", 2)
                print('Object in range')
                PWM.start(3)
                print('duty cycle:', 3)
                sleep(4)
            else:
                LCD.lcd_display_string("Dustbin is     ", 1)
                print('No object in range')
                LCD.lcd_display_string("closed.       ", 2)
                PWM.start(12)
                print('duty cycle:', 12)
                sleep(4)
        if stop_thread:
            break
    GPIO.cleanup()

def stop_program():
    getGpio()
    LCD.lcd_display_string("                ", 1)
    LCD.lcd_display_string("                ", 2)
    global stop_thread
    stop_thread = True
    GPIO.cleanup()

@app.route('/start', methods=['POST'])
def start():
    global program_thread
    if program_thread is None or not program_thread.is_alive():
        program_thread = threading.Thread(target=start_program, args=(TOKEN,))
        program_thread.start()
        return jsonify({"status": "Program started"})
    else:
        return jsonify({"status": "Program is already running"})

@app.route('/stop', methods=['POST'])
def stop():
    LCD.lcd_display_string("                ", 1)
    LCD.lcd_display_string("                ", 2)
    global program_thread
    if program_thread is not None and program_thread.is_alive():
        stop_program()
        program_thread.join()
        return jsonify({"status": "Program stopped"})
    else:
        return jsonify({"status": "Program is not running"})

@app.route('/status')
def status():
    global program_thread
    if program_thread is None or not program_thread.is_alive():
        return jsonify({"status": "Stopped"})
    else:
        return jsonify({"status": "Running"})

@app.route('/')
def index():
    return '''
        <html>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@4.3.1/dist/css/bootstrap.min.css" integrity="sha384-ggOyR0iXCbMQv3Xipma34MD+dH/1fQ784/j6cY/iJTQUOhcWr7x9JvoRxT2MZw1T" crossorigin="anonymous">
            <body style="margin-top: 100px">
                <h1 style="text-align: cetner;">Smart Bin Control</h1>
                <p style="text-align: cetner;" id="program-status">Status: Unknown</p>
                <button style="margin-left: 400px"onclick="startProgram()">Start Program</button>
                <button onclick="stopProgram()">Stop Program</button>
                <script>
                    function updateStatus() {
                        fetch('/status')
                            .then(response => response.json())
                            .then(data => {
                                document.getElementById('program-status').innerText = 'Status: ' + data.status;
                            });
                    }

                    function startProgram() {
                        fetch('/start', {method: 'POST'})
                            .then(response => response.json())
                            .then(data => {
                                alert(data.status);
                                updateStatus();
                            });
                    }

                    function stopProgram() {
                        fetch('/stop', {method: 'POST'})
                            .then(response => response.json())
                            .then(data => {
                                alert(data.status);
                                updateStatus();
                            });
                    }

                    setInterval(updateStatus, 5000); // Update status every 5 seconds
                    updateStatus(); // Initial status update
                </script>
            </body>
        </html>
    '''

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
