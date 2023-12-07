#!/usr/bin/env python
# -*- coding: utf-8 -*-
import csv
import logging.config
import os
import pickle
import random
import re
import requests
import time
from datetime import datetime, timedelta
from multiprocessing import freeze_support
from pathlib import Path
from time import sleep
import ntplib
import pandas as pd
import pyfiglet
from PIL import Image, ImageFont, ImageDraw
import base64
from io import BytesIO
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


# Captcha solver for CoinMarketCap
def solve_captcha(self):
    self.clear_downloads_directory(self.directory_downloads)
    LOGGER.info(f'Solving captcha')
    scr_shot_path = self.directory_downloads + '/screenshot.png'
    slice_path = self.directory_downloads + '/CMC_captcha_slice.png'
    captcha_path = self.directory_downloads + '/CMC_captcha.png'
    for i in range(1, 5):
        LOGGER.info(f'Attempt {i}')
        self.driver.save_screenshot(scr_shot_path)
        sleep(3)
        self.wait_until_visible(driver=self.driver, css_selector='.css-jyuqmw', duration=10)
        image = self.driver.find_element(By.CSS_SELECTOR, '.css-jyuqmw').screenshot(scr_shot_path)
        sleep(1)
        image = Image.open(scr_shot_path)
        width, height = image.size
        image_slice = image.crop((0, 0, 60, 192))
        image_slice.save(slice_path)
        image_bg = image.crop((60, 0, width, height))
        draw = ImageDraw.Draw(image_bg)
        font = ImageFont.truetype(self.fonts_path, 15)
        draw.text(xy=(10, 0), text="CLICK ON TOP RIGHT PUZZLE\nCORNER", fill='white', font=font, align='center', spacing=2)
        draw.text(xy=(10.5, 0), text="CLICK ON TOP RIGHT PUZZLE\nCORNER", fill='white', font=font, align='center', spacing=2)
        draw.text(xy=(11, 0), text="CLICK ON TOP RIGHT PUZZLE\nCORNER", fill='white', font=font, align='center', spacing=2)
        image_bg.save(captcha_path)
        textinstructions = 'Click-on-top-right-puzzle-corner'
        with open(captcha_path, "rb") as image_file:
            encoded_captcha_image = base64.b64encode(image_file.read())
        params = {'coordinatescaptcha': 1, 'textinstructions': textinstructions, 'body': encoded_captcha_image,
                  'key': self.api_key, 'method': 'base64'}
        post_response = requests.post(url='http://2captcha.com/in.php', data=params)
        sleep(5)
        LOGGER.info(f'POST response: {post_response.text}')
        if 'OK' in post_response.text:
            txt = post_response.text
            resp_id = txt.split('|')[1].strip()
            LOGGER.info(f'Waiting for captcha to be solved')
            sleep(20)
            get_params = {'key': self.api_key, 'action': 'get', 'id': resp_id}
            while True:
                get_response = requests.get(url='http://2captcha.com/res.php', params=get_params)
                LOGGER.info(f'GET response: {get_response.text}')
                if 'OK' in get_response.text:
                    puzzle_positions = re.findall(pattern=r'x=(\d*)', string=get_response.text)
                    if len(puzzle_positions) == 0:
                        puzzle_positions = re.findall(pattern=r'\|(\d*)', string=get_response.text)
                    LOGGER.info(f'Puzzle position: {puzzle_positions}')
                    time.sleep(1)
                    offset = 33
                    puzzle_pos = int(puzzle_positions[0]) + offset
                    if puzzle_pos < 5 or puzzle_pos == '' or puzzle_pos is None:
                        break
                    LOGGER.info(f'Moving the puzzle to {puzzle_pos}')
                    slider = self.driver.find_element(By.CSS_SELECTOR, ".css-1w5k7wg")
                    ActionChains(self.driver).drag_and_drop_by_offset(slider, puzzle_pos, 0).perform()
                    try:
                        self.wait_until_visible(driver=self.driver, css_selector='.avatar-img ', duration=10)
                        LOGGER.info("Login successful")
                        return True
                    except:
                        LOGGER.info("Captcha error")
                        break
                elif 'CAPCHA_NOT_READY' in get_response.text:
                    LOGGER.info("Waiting for captcha to be solved")
                    sleep(10)
                    LOGGER.info("Repeating GET request")
                elif 'ERROR_CAPTCHA_UNSOLVABLE' in get_response.text:
                    break
        elif 'ERROR_TOO_BIG_CAPTCHA_FILESIZE' in post_response.text:
            return False

