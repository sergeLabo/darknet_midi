#!/usr/bin/env python3
# -*- coding: utf8 -*-

########################################################################
# This file is part of Darknet Midi.
#
# Darknet Midi is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Darknet Midi is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
########################################################################


"""
Utilise FluidR3_GM.sf2 uniquement
Installation:
    numpy
    pretty_midi
    fluidsynth
    FluidR3_GM.sf2
Le dossier music doit exister avec des morceaux midi
Le fichier bank_GM.txt doit être avec ce script

Excécution du script, pour jouer un morceau au hasard:
    python3 analyse_play_midi.py
"""


import os
from time import sleep
import pathlib
from random import randint, choice
import threading
import numpy
import pretty_midi
import fluidsynth


class PlayOneMidiChannel:
    """Ne fonctionne qu'avec FluidR3_GM.sf2"""
    
    def __init__(self, fonts, bank, bank_number):
        """self.channel 1 to 16"""

        self.fonts = fonts
        self.channel = 1
        self.bank = bank
        self.bank_number = bank_number
        
        self.set_audio()
        self.thread_dict = {}
        for i in range(128):
            self.thread_dict[i] = 0
            
    def set_audio(self):
        """Spécific à FluidR3_GM.sf2
        note from 0 to 127 but all values are not possible in all bank
        life 0 to ?
        channel 1 to 16
        volume 0 to 127

        yamaha grand piano
           program_select(channel,  sfid, bank, bank number)
        fs.program_select(  1  ,    sfid,  0,      0       )
        """

        self.fs = fluidsynth.Synth()
        self.fs.start(driver='alsa')
        sfid = self.fs.sfload(self.fonts)
        self.fs.program_select(self.channel, sfid, self.bank, self.bank_number)
            
    def play_note(self, note, volume):
        
        self.fs.noteon(self.channel, note, volume)
        
        while self.thread_dict[note]:
            sleep(0.0001)
        # Sinon fin de la note
        #print("Fin du thread de la note:", note)
        self.fs.noteoff(self.channel, note)
        
    def thread_note(self, note, volume):
        """Le thread se termine si note_off"""

        #print("Lancement du thread de la note:", note)
        self.thread_dict[note] = 1
        thread = threading.Thread(target=self.play_note, args=(note, volume))
        thread.start()

    def play_partition(self, partition, FPS, instrument):
        """partition = liste de listes (note=82, velocity=100)
        [[(82,100)], [(82,100), (45,88)], [(0,0)], ...
        un item tous les 1/FPS
        """

        print("Excécution de la partition de", instrument)
        for event in partition:
            # event sont les notes pour la frame
            nombre_de_note = len(event)
            note_en_cours = []
            for midi in range(nombre_de_note):
                note = int(event[midi][0])
                note_en_cours.append(note)
                volume = int(event[midi][1])
                
                # Lancement de la note si pas en cours
                if self.thread_dict[note] == 0:
                    self.thread_note(note, volume)

            # Fin des notes autres que les notes en cours
            for k, v in self.thread_dict.items():
                if v == 1:
                    if k not in note_en_cours:
                        self.thread_dict[k] = 0

            sleep(1/FPS)
            
        print("The end of", instrument, "!")
        self.the_end()

    def the_end(self):
        """Fin  de tous les threads"""
        
        for i in range(128):
            self.thread_dict[i] = 0


class AnalyseMidiFile:
    """Analyse le fichier midi,
    trouve le nombre et le nom des instruments.
    Retourne la liste des notes sur une time lapse de chaque instrument.
    """
    
    def __init__(self, midi_file, FPS):
        """Un seul fichier midi
        FPS de 10 à 1000, 50 ou 100 est bien
        Plus le FPS est élevé, plus le temps de calcul est long !
        """
        
        self.midi_file = midi_file
        self.FPS = FPS
        
    def get_partitions(self):
        """Fait les étapes pour tous les instruments"""
        
        parts, instruments_dict = self.analyse()
        partitions = []
        for k, v in instruments_dict.items():
            instrument_roll = self.get_instrument_roll(v)
            partition = self.get_partition(instrument_roll, v)
            partitions.append(partition)
        return partitions, instruments_dict
                
    def analyse(self):
        """ Instrument 0 Nom: Bass    
            Instrument 1 Nom: Drums   
            Instrument 2 Nom: Piano   
            Instrument 3 Nom: Piano
            Instrument 4 Nom: Guitar
        Si 2 piano !!
        """
        midi_pretty_format = pretty_midi.PrettyMIDI(self.midi_file)
        instruments = midi_pretty_format.instruments
        nbi = len(instruments)
        print("Nombre d'intruments:", nbi)

        # Dict des partitions des instruments
        partitions_dict = {}
        instruments_dict = {}
        for i in range(nbi):
            nom = instruments[i].name
            instruments_dict[i] = instruments[i]
            print("Instrument", i, "Nom:", nom)
            # Chaque partition est un array
            partitions_dict[i] = instruments[i]

        return partitions_dict, instruments_dict
        
    def get_instrument_roll(self, partition):
        """Retourne un np.array de (128, FPS*durée du morceau en secondes)"""

        # La méthode get_piano_roll marche pour tous les instruments
        instrument_roll = partition.get_piano_roll(self.FPS)

        return instrument_roll

    def get_partition(self, instrument_roll, instrument):
        """Conversion du numpy array en liste de note tous les FPS
        La conversion est longue, 10 à 20 secondes par instrument
        """

        # Copie des lignes du array dans une liste de ligne
        lignes = []
        for i in range(instrument_roll.shape[1]):
            ligne = instrument_roll[:,i]
            lignes.append(ligne)

        # Analyse des lignes pour ne garder que les non nuls
        partition = []
        for e in lignes:
            notes = []
            for n in range(instrument_roll.shape[0]):
                if numpy.any(e[n] != numpy.float64(0)):
                    notes.append((n, e[n]))
            partition.append(notes)
            
        print("Nombre de note dans la partition de", instrument, ":", len(partition))
        return partition


class AnalyseAndPlay:
    """    """
    
    def __init__(self, midi, FPS, fonts, bank_GM_txt):
        """Fichier midi et FPS"""
        
        self.midi = midi
        self.FPS = FPS
        self.fonts = fonts
        self.bank_GM_txt = bank_GM_txt
        self.banks = self.get_banks()
        self.analyse_and_play()
        
    def get_banks(self):
        file_name = self.bank_GM_txt
        with open(file_name) as f:
            data = f.read()
            f.close()
        lines = data.splitlines()
        return lines
        
    def analyse_and_play(self):
        amf = AnalyseMidiFile(self.midi, self.FPS)
        partitions, instruments_dict = amf.get_partitions()
        print("Nombre de partition", len(partitions))
        
        for i in range(len(partitions)):
            # ligne au hasard
            haz = randint(0, len(self.banks)-1)
            line = self.banks[haz].split(" ")
            bank, bank_number = int(line[0]), int(line[1])
            self.thread_play_partition( bank,
                                        bank_number,
                                        partitions[i],
                                        instruments_dict[i])
                
        sleep(len(partitions[0])/100)
        print("Fin du fichier", file_list[n])
    
    def play_partition(self, bank, bank_number, partition, instrument):
        pomc = PlayOneMidiChannel(self.fonts, bank, bank_number)
        pomc.play_partition(partition, FPS, instrument)

    def thread_play_partition(self, bank, bank_number, partition, instrument):
        """Le thread se termine si note_off"""

        thread = threading.Thread(target=self.play_partition, args=(bank,
                                                                bank_number,
                                                                partition,
                                                                instrument))
        thread.start()


if __name__ == '__main__':
    """Joue au hasard un morceau du dossier music
    Il faut définir le chemin de FluidR3_GM.sf2
    """
    
    file_list = []
    for path, subdirs, files in os.walk("./music"):
        for name in files:
            if name.endswith("mid"):
                file_list.append(str(pathlib.PurePath(path, name)))
    
    n = randint(0, len(file_list)-1)
    print("Fichier en cours:", "./" + file_list[n])

    # FPS de 10 (trop petit) à 100 (bien)
    FPS = 50

    # Il faut installer FluidR3_GM.sf2
    fonts = "/usr/share/sounds/sf2/FluidR3_GM.sf2"
    
    # Le fichier bank_GM.txt doit être avec ce sript
    bank_GM_txt = "./bank_GM.txt"
    
    midi = "./" + file_list[n]
    aap = AnalyseAndPlay(midi, FPS, fonts, bank_GM_txt)
