# Try importing RPi.GPIO safely
try:
    import RPi.GPIO as GPIO
    RPI_GPIO_AVAIL = True
except ImportError:
    RPI_GPIO_AVAIL = False

class RpiHandler:
    def __init__(self):
        if RPI_GPIO_AVAIL:
            self.fan_pin = 12
            GPIO.setwarnings(False)			#disable warnings
            GPIO.setmode(GPIO.BCM)		#set pin numbering system
            GPIO.setup(self.fan_pin,GPIO.OUT)
            self.pi_pwm = GPIO.PWM(self.fan_pin,80)		#create PWM instance with frequency
            self.pi_pwm.start(0)				#start PWM of required Duty Cycle 
            self.pi_pwm.ChangeDutyCycle(40)