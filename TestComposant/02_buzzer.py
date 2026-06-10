#!/usr/bin/env python3
from gpiozero import TonalBuzzer
from gpiozero.tones import Tone
from time import sleep
import mido

tb = TonalBuzzer(18, octaves=4)

def play_midi(midi_file_path):
    mid = mido.MidiFile(midi_file_path)
    print("Lecture du fichier bridée entre 220Hz et 880Hz...")

    for msg in mid.play():
        if msg.type == 'note_on' and msg.velocity > 0:
            note = msg.note

            # Calcul de la fréquence
            frequency = 440 * (2 ** (((note - 69) / 12) -0.5))
            tb.play(Tone(frequency=frequency))
                
        elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
            tb.stop()
if __name__ == "__main__":
    try:
        play_midi("7.mid")
    except KeyboardInterrupt:
        tb.stop()
