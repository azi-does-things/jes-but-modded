import pygame
from utils import arrayLerp, getUnit, hue_to_rgb, speciesToColor, species_to_name, dist_to_text, bound, getDist, arrayIntMultiply
from jes_dataviz import displayAllGraphs, drawAllGraphs
from jes_shapes import drawRect, drawRingLight, drawX, centerText, alignText, rightText, drawClock, drawSpeciesCircle
from jes_slider import Slider
from jes_button import Button
import time
import numpy as np
import math
import random

class UI:
    def __init__(self, _W_W, _W_H, _MOVIE_SINGLE_DIM, _GRAPH_COOR, _SAC_COOR, _GENEALOGY_COOR,
                 _COLUMN_MARGIN, _MOSAIC_DIM, _MENU_TEXT_UP, _CM_MARGIN1, _CM_MARGIN2):
        self.sliderList = []
        self.buttonList = []
        pygame.font.init()
        self.bigFont = pygame.font.Font('C:/Users/caryk/AppData/Local/Microsoft/Windows/Fonts/Jygquip 1.ttf', 60)
        self.smallFont = pygame.font.Font('C:/Users/caryk/AppData/Local/Microsoft/Windows/Fonts/Jygquip 1.ttf', 30)
        self.tinyFont = pygame.font.Font('C:/Users/caryk/AppData/Local/Microsoft/Windows/Fonts/Jygquip 1.ttf', 21)
        self.BACKGROUND_PIC = pygame.image.load("visuals/background.png")
        self.W_W = _W_W
        self.W_H = _W_H
        self.MOVIE_SINGLE_DIM = _MOVIE_SINGLE_DIM
        self.INFO_W = self.MOVIE_SINGLE_DIM[0]

        self.GRAPH_COOR = _GRAPH_COOR
        self.graph = pygame.Surface(self.GRAPH_COOR[2:4], pygame.SRCALPHA, 32)
        self.SAC_COOR = _SAC_COOR
        self.sac = pygame.Surface(self.SAC_COOR[2:4], pygame.SRCALPHA, 32)
        self.GENEALOGY_COOR = _GENEALOGY_COOR
        self.gene_graph = pygame.Surface(self.GENEALOGY_COOR[2:4], pygame.SRCALPHA, 32)

        self.COLUMN_MARGIN = _COLUMN_MARGIN
        self.MOSAIC_DIM = _MOSAIC_DIM
        self.MENU_TEXT_UP = _MENU_TEXT_UP

        self.CM_MARGIN1 = _CM_MARGIN1
        self.CM_MARGIN2 = _CM_MARGIN2
        self.MS_W = self.W_W - self.CM_MARGIN1 * 2    # mosaic screen width
        self.MS_WC = self.MS_W - self.INFO_W - self.COLUMN_MARGIN  # mosaic screen width (just creatures)
        self.MS_H = self.W_H - self.MENU_TEXT_UP - self.CM_MARGIN1 * 2

        s1 = int((self.MS_WC) / self.MOSAIC_DIM[0] - self.CM_MARGIN2 * 2)
        s2 = int((self.MS_WC) / self.MOSAIC_DIM[1] - self.CM_MARGIN2 * 2)
        self.ICON_DIM = ((s1, s1), (s2, s2), (s2, s2))

        self.mosaicVisible = False
        self.CLH = [None, None, None]  # Creature Location Highlight. First: is it in the mosaic (0), or top-3? (1). Second: Index of highlighted creature? Third: rank of creature?
        self.creatureHighlight = []
        self.sliderDrag = None

        self.visualSimMemory = []
        self.movieScreens = []
        self.sim = None

        self.screen = pygame.display.set_mode((self.W_W, self.W_H))
        self.mosaicScreen = pygame.Surface((self.MS_WC, self.MS_H), pygame.SRCALPHA, 32)
        self.infoBarScreen = pygame.Surface((self.INFO_W, self.MS_H), pygame.SRCALPHA, 32)
        self.previewLocations = [[570, 105, 250, 250], [570, 365, 250, 250], [570, 625, 250, 250]]
        self.salt = str(random.uniform(0, 1))
        self.sc_colors = {}  # special-case colors: species colored by the user, not RNG

        # variables for the "Watch sample" button
        self.sample_frames = 0
        self.sample_i = 0

        self.FPS = 60  # for faster speed and no choppy, modify to your fps!
        pygame.time.Clock().tick(self.FPS)

        # colors
        self.GREEN = (0, 255, 0)
        self.GRAYISH = (108, 118, 155)
        self.BLACK = (0, 0, 0)
        self.WHITE = (255, 255, 255)
        self.MOSAIC_COLOR = (80, 80, 80)
        self.SAMPLE_FREEZE_TIME = 90
        self.showXs = True
        self.species_storage = None
        self.storage_coor = (660, 52)
        self.running = True

    # --- BUTTONS AND SLIDERS ---
    def addButtonsAndSliders(self):
        self.genSlider = Slider(self, (40, self.W_H - 100, self.W_W - 80, 60, 140), 0, 0, 0, True, True, self.updateGenSlider)
        self.sliderList.append(self.genSlider)

        buttonCoor = []
        for i in range(6):
            buttonCoor.append((self.W_W - 1340 + 220 * i, self.W_H - self.MENU_TEXT_UP, 200, 60))

        self.showCreaturesButton = Button(self, buttonCoor[0], ["Show creatures", "Hide creatures"], self.toggleCreatures)
        self.sortButton = Button(self, buttonCoor[1], ["Sort by ID", "Sort by fitness", "Sort by weakness"], self.toggleSort)
        self.styleButton = Button(self, buttonCoor[2], ["Big Icons", "Small Icons", "Species Tiles"], self.toggleStyle)
        self.sampleButton = Button(self, buttonCoor[3], ["Watch sample", "Stop sample"], self.startSample)
        self.doGenButton = Button(self, buttonCoor[4], ["Do a generation"], self.sim.doGeneration)
        self.ALAPButton = Button(self, buttonCoor[5], ["Turn on ALAP", "Turn off ALAP"], self.doNothing)

        self.buttonList.extend([
            self.showCreaturesButton, self.sortButton, self.styleButton,
            self.sampleButton, self.doGenButton, self.ALAPButton
        ])

    # --- HELPERS ---
    def reverse(self, i):
        return self.sim.c_count - 1 - i

    def getHighlightedSpecies(self):
        gen = self.genSlider.val
        if self.CLH[0] == 2:
            return self.CLH[1]
        elif self.CLH[0] == 0 or self.CLH[0] == 1:
            return self.sim.creatures[gen][self.CLH[1]].species
        return None

    # --- MOUSE ---
    def detectMouseMotion(self):
        if self.sampleButton.setting == 1:
            return
        gen = self.genSlider.val
        mouseX, mouseY = pygame.mouse.get_pos()
        newCLH = [None, None, None]
        if self.mosaicVisible:
            rel_mouseX = mouseX - self.CM_MARGIN1
            rel_mouseY = mouseY - self.CM_MARGIN1
            if 0 <= rel_mouseX < self.MS_WC and 0 <= rel_mouseY < self.MS_H:
                DIM = self.MOSAIC_DIM[self.styleButton.setting]
                SPACING = self.MS_WC / DIM
                ix = min(int(rel_mouseX / SPACING), DIM - 1)
                iy = min(int(rel_mouseY / SPACING), DIM - 1)
                i = iy * DIM + ix
                if 0 <= i < self.sim.c_count:
                    sort = self.sortButton.setting
                    if sort == 0 or gen >= len(self.sim.rankings):
                        newCLH = [0, i, i]
                    elif sort == 1:
                        newCLH = [0, self.sim.rankings[gen][i], i]
                    elif sort == 2:
                        newCLH = [0, self.sim.rankings[gen][self.reverse(i)], i]

        elif 0 <= gen < len(self.sim.rankings):
            # rolling mouse over the Best+Median+Worst previews
            for r in range(len(self.previewLocations)):
                PL = self.previewLocations[r]
                if PL[0] <= mouseX < PL[0] + PL[2] and PL[1] <= mouseY < PL[1] + PL[3]:
                    index = self.sim.rankings[gen][self.r_to_rank(r)]
                    newCLH = [1, index, r]

            # rolling mouse over species circles
            rX = mouseX - self.GENEALOGY_COOR[0]
            rY = mouseY - self.GENEALOGY_COOR[1]
            answer = self.getRollOver(rX, rY)
            if answer is not None:
                newCLH = [2, answer]

            # rolling over storage
            if self.species_storage is not None and getDist(mouseX, mouseY, self.storage_coor[0], self.storage_coor[1]) <= self.GENEALOGY_COOR[4]:
                newCLH = [2, self.species_storage]

        if newCLH[1] != self.CLH[1]:
            self.CLH = newCLH
            if self.CLH[1] is None:
                self.clearMovies()
            elif self.CLH[0] == 2:  # a species was highlighted
                info = self.sim.species_info[self.CLH[1]]
                L = len(info.reps)
                self.visualSimMemory = []
                self.creatureHighlight = []
                self.movieScreens = []
                for i in range(L):
                    ID = info.reps[i]
                    gen = ID // self.sim.c_count
                    c = ID % self.sim.c_count
                    self.creatureHighlight.append(self.sim.creatures[gen][c])
                    self.visualSimMemory.append(self.sim.simulateImport(gen, c, c + 1, True))
                    self.movieScreens.append(None)
                self.drawInfoBarSpecies(self.CLH[1])
            else:  # a creature was highlighted!
                self.creatureHighlight = [self.sim.creatures[gen][self.CLH[1]]]
                self.visualSimMemory = [self.sim.simulateImport(gen, self.CLH[1], self.CLH[1] + 1, True)]
                self.movieScreens = [None] * 1
                self.drawInfoBarCreature(self.sim.creatures[gen][self.CLH[1]])

    def clearMovies(self):
        self.visualSimMemory = []
        self.creatureHighlight = []
        self.movieScreens = []
        self.CLH = [None, None, None]

    def getRollOver(self, mouseX, mouseY):
        answer = None
        ps = self.sim.prominent_species
        for level in range(len(ps)):
            for i in range(len(ps[level])):
                s = ps[level][i]
                sX, sY = self.sim.species_info[s].coor
                if getDist(mouseX, mouseY, sX, sY) <= self.GENEALOGY_COOR[4]:
                    answer = s
        return answer

    # --- MOSAIC ---
    def drawCreatureMosaic(self, gen):
        self.mosaicScreen.fill(self.MOSAIC_COLOR)
        for c in range(self.sim.c_count):
            i = c
            creature = self.sim.creatures[gen][c]
            if creature.rank is not None:
                if self.sortButton.setting == 1:
                    i = creature.rank
                elif self.sortButton.setting == 2:
                    i = self.reverse(creature.rank)
            DIM = self.MOSAIC_DIM[self.styleButton.setting]
            x = i % DIM
            y = i // DIM
            SPACING = self.MS_WC / DIM
            creature.iconCoor = (x * SPACING + self.CM_MARGIN2, y * SPACING + self.CM_MARGIN2, SPACING, SPACING)
            if creature.iconCoor[1] < self.mosaicScreen.get_height():
                s = self.styleButton.setting
                if s <= 1:
                    self.mosaicScreen.blit(creature.icons[s], creature.iconCoor)
                elif s == 2:
                    EXTRA = 1
                    pygame.draw.rect(self.mosaicScreen, speciesToColor(creature.species, self),
                                     (creature.iconCoor[0], creature.iconCoor[1], SPACING + EXTRA, SPACING + EXTRA))
                if not creature.living and self.showXs:
                    color = (255, 0, 0) if s <= 1 else (0, 0, 0)
                    drawX(creature.iconCoor, self.ICON_DIM[s][0], color, self.mosaicScreen)

    # --- INFO BAR ---
    def drawInfoBarCreature(self, creature):
        X_center = int(self.INFO_W * 0.5)
        self.infoBarScreen.fill(self.MOSAIC_COLOR)
        stri = [f"Creature #{creature.IDNumber}",
                f"Species: {species_to_name(creature.species, self)}",
                f"Untested"]
        if creature.fitness is not None:
            fate = "Living" if creature.living else "Killed"
            stri = [f"Creature #{creature.IDNumber}",
                    f"Species: {species_to_name(creature.species, self)}",
                    f"Fitness: {dist_to_text(creature.fitness, True, self.sim.UNITS_PER_METER)}",
                    f"Rank: {creature.rank + 1} - {fate}"]

        for i in range(len(stri)):
            color = self.WHITE
            if stri[i][0:7] == "Species":
                color = speciesToColor(creature.species, self)
            centerText(self.infoBarScreen, stri[i], X_center, self.MOVIE_SINGLE_DIM[1] + 40 + 42 * i, color, self.smallFont)

    # --- MOVIES ---
    def drawMovieGrid(self, screen, coor, mask, titles, colors, font):
        LMS = len(self.movieScreens)
        per_row = 1 if LMS == 1 else LMS // 2
        for i in range(LMS):
            if mask is not None and not mask[i]:
                continue
            ms = self.movieScreens[i]
            W = ms.get_width()
            H = ms.get_height()
            x = coor[0] + (i % per_row) * W
            y = coor[1] + (i // per_row) * H
            screen.blit(ms, (x, y))
            if titles is not None:
                centerText(screen, titles[i], x + W / 2, y + H - 30, colors[i], font)

    def drawMovieQuad(self, species):
        L = 4
        info = self.sim.species_info[species]
        a_name = species_to_name(info.ancestorID, self)
        s_name = species_to_name(species, self)
        titles = ["Ancestor", "First", "Apex", "Last"]
        mask = [True] * 4
        for i in range(L):
            if (info.ancestorID is None and i == 0) or (i >= 2 and info.getWhen(i) == info.getWhen(i - 1)):
                mask[i] = False
                continue
            stri = a_name if i == 0 else s_name
            performance = info.getPerformance(self.sim, i)
            titles[i] = f"G{info.getWhen(i)}: {titles[i]} {stri} ({dist_to_text(performance, True, self.sim.UNITS_PER_METER)})"
        coor = (self.CM_MARGIN1 + self.MS_WC, 0)
        self.drawMovieGrid(self.screen, coor, mask, titles, [self.GRAYISH] * L, self.tinyFont)
