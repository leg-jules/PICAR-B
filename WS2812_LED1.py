import time
from rpi_ws281x import *

class LED:
    def __init__(self):
        self.LED_COUNT = 14 # Set to the total number of LED lights on the robot
        # which can be more than the total number of LED lights
        # connected to the Raspberry Pi
        self.LED_PIN = 10 # GPIO pin
        self.LED_FREQ_HZ = 800000 # LED signal frequency in hertz (usually 800khz)
        self.LED_DMA = 10 # DMA channel to use for generating signal
        self.LED_BRIGHTNESS = 255 # Set to 0 for darkest and 255 for brightest
        self.LED_INVERT = False # True to invert the signal
        self.LED_CHANNEL = 0
        # Create NeoPixel object with appropriate configuration.
        self.strip = Adafruit_NeoPixel(self.LED_COUNT, self.LED_PIN, self.LED_FREQ_HZ,
        self.LED_DMA, self.LED_INVERT, self.LED_BRIGHTNESS, self.LED_CHANNEL)
        # Intialize the library (must be called once before other functions).
        self.strip.begin()

    #Choisir une couleur pour toutes les LED
    def colorWipe(self, R, G, B):
        # This function is used to change the color of the LED
        color = Color(R,G,B)
        for i in range(self.strip.numPixels()):
            # Only one LED light color can be set at a time, so a cycle is required
            self.strip.setPixelColor(i, color)
            self.strip.show() # After calling the show method, the color will really change
            # This code will control all the WS2812 lights to switch among the three colors
            # Press CTRL+C to exit the program.

    #Choisir l'intensité des LED
    def setBrightness(self, brightness):
        #brightness doi être entre 0 et 255
        if brightness < 0:
            brightness = 0
        if brightness > 255:
            brightness = 255
        
        self.strip.setBrightness(brightness)
        self.strip.show()

    #Choisir la couleur d'une LED
    def setLedColor(self, led_number, R,G,B): 
        #Vérifie que le numéro de LED est valide
        if led_number < 0 or led_number >= self.strip.numPixels():
            print("Erreur : numéro de LED invalide")
            return
        
        #Crée la couleur RGB
        color = Color(R, G, B)

        #Change la couleur de la LED choisie
        self.strip.setPixelColor(led_number, color)

        #Envoie le changement aux LED
        self.strip.show()

    def setPixelColorRGB(self, led_number ,R, G, B, brightness):
        #Vérifie que le numéro de LED est valide
        if led_number < 0 or led_number >= self.strip.numPixels():
            print("Erreur : numéro de LED invalide")
            return
        
        # Vérifie que brightness est entre 0 et 255
        if brightness < 0:
            brightness = 0
        if brightness > 255:
            brightness = 255
        
         # Applique la luminosité à la couleur
        red = int(R * brightness / 255)
        green = int(G * brightness / 255)
        blue = int(B * brightness / 255)

        color = Color(R, G, B)        

        self.strip.setPixelColor(led_number, color)

        self.strip.show()

if __name__ == '__main__':
    led = LED()

    try:

        led.setPixelColorRGB(5, 0, 0, 255, 60)

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        led.colorWipe(0,0,0) # Turn off all lights
