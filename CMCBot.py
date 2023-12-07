#!/usr/bin/env python3
"""
    *******************************************************************************************
    CMCBot: CoinMarketCap Captcha Solver Bot
    Developer: Ali Toori, Full-Stack Python Developer
    Founder: https://boteaz.com/
    *******************************************************************************************
"""
import os
import pickle
import re
import json
import random
import logging.config
import time
import zipfile
from time import sleep
import pandas as pd
import pyfiglet
import concurrent.futures
from pathlib import Path
from datetime import datetime
from multiprocessing import freeze_support

import requests
from PIL import Image
from selenium import webdriver

from selenium.common import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support.select import Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.service import Service
from twocaptcha import TwoCaptcha


class CMCBot:
    def __init__(self):
        self.PROJECT_ROOT = Path(os.path.abspath(os.path.dirname(__file__)))
        self.file_settings = str(self.PROJECT_ROOT / 'BotRes/Settings.json')
        self.directory_downloads = str(self.PROJECT_ROOT / 'BotRes/Downloads/')
        self.url_cmc = "https://www.coinmarketcap.com/"
        self.user_agents = self.get_user_agents()
        self.settings = self.get_settings()
        self.twocaptcha_api_key = self.settings["Settings"]["2CaptchaAPIKey"]
        self.twocaptcha_solver = TwoCaptcha(apiKey=self.twocaptcha_api_key)
        self.LOGGER = self.get_logger()
        self.logged_in = False
        driver = None

    # Get self.LOGGER
    @staticmethod
    def get_logger():
        """
        Get logger file handler
        :return: LOGGER
        """
        logging.config.dictConfig({
            "version": 1,
            "disable_existing_loggers": False,
            'formatters': {
                'colored': {
                    '()': 'colorlog.ColoredFormatter',  # colored output
                    # --> %(log_color)s is very important, that's what colors the line
                    'format': '[%(asctime)s,%(lineno)s] %(log_color)s[%(message)s]',
                    'log_colors': {
                        'DEBUG': 'green',
                        'INFO': 'cyan',
                        'WARNING': 'yellow',
                        'ERROR': 'red',
                        'CRITICAL': 'bold_red',
                    },
                },
                'simple': {
                    'format': '[%(asctime)s,%(lineno)s] [%(message)s]',
                },
            },
            "handlers": {
                "console": {
                    "class": "colorlog.StreamHandler",
                    "level": "INFO",
                    "formatter": "colored",
                    "stream": "ext://sys.stdout"
                },
                "file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "level": "INFO",
                    "formatter": "simple",
                    'encoding': 'utf-8',
                    "filename": "CMCBot.log",
                    "maxBytes": 5 * 1024 * 1024,
                    "backupCount": 1
                },
            },
            "root": {"level": "INFO",
                     "handlers": ["console", "file"]
                     }
        })
        return logging.getLogger()

    @staticmethod
    def enable_cmd_colors():
        # Enables Windows New ANSI Support for Colored Printing on CMD
        from sys import platform
        if platform == "win32":
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)

    @staticmethod
    def banner():
        pyfiglet.print_figlet(text='____________ CMCBot\n', colors='RED')
        print('CMCBot: CoinMarketCap Captcha Solver Bot\n'
              'Developer: Ali Toori, Full-Stack Python Developer\n'
              'Founder: https://boteaz.com/\n'
              '************************************************************************')

    def get_settings(self):
        """
        Creates default or loads existing settings file.
        :return: settings
        """
        if os.path.isfile(self.file_settings):
            with open(self.file_settings, 'r') as f:
                settings = json.load(f)
            return settings
        settings = {"Settings": {
            "NumberOfInstancesToRun": 1
        }}
        with open(self.file_settings, 'w') as f:
            json.dump(settings, f, indent=4)
        with open(self.file_settings, 'r') as f:
            settings = json.load(f)
        return settings

    # Get random user agent
    def get_user_agents(self):
        file_uagents = str(self.PROJECT_ROOT / 'BotRes/user_agents.txt')
        with open(file_uagents) as f:
            content = f.readlines()
        return [x.strip() for x in content]

    # Loads web driver with configurations
    def get_driver(self, proxy=True, headless=False):
        driver_bin = str(self.PROJECT_ROOT / "BotRes/bin/chromedriver.exe")
        service = Service(executable_path=driver_bin)
        options = webdriver.ChromeOptions()
        options.add_argument("--start-maximized")
        # options.add_argument("--disable-extensions")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-blink-features")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-gpu")
        options.add_argument("--dns-prefetch-disable")
        options.add_argument('--ignore-ssl-errors')
        options.add_argument('--ignore-certificate-errors')
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        prefs = {"directory_upgrade": True,
                 "credentials_enable_service": False,
                 "profile.password_manager_enabled": False,
                 "profile.default_content_settings.popups": False,
                 # "profile.managed_default_content_settings.images": 2,
                 f"download.default_directory": f"{self.directory_downloads}",
                 "profile.default_content_setting_values.geolocation": 2
                 }
        options.add_experimental_option("prefs", prefs)
        options.add_argument(F'--user-agent={random.choice(self.user_agents)}')
        driver = webdriver.Chrome(service=service, options=options)
        return driver

    @staticmethod
    def wait_until_visible(driver, css_selector=None, element_id=None, name=None, class_name=None, tag_name=None, duration=10000, frequency=0.01):
        if css_selector:
            WebDriverWait(driver, duration, frequency).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, css_selector)))
        elif element_id:
            WebDriverWait(driver, duration, frequency).until(EC.visibility_of_element_located((By.ID, element_id)))
        elif name:
            WebDriverWait(driver, duration, frequency).until(EC.visibility_of_element_located((By.NAME, name)))
        elif class_name:
            WebDriverWait(driver, duration, frequency).until(
                EC.visibility_of_element_located((By.CLASS_NAME, class_name)))
        elif tag_name:
            WebDriverWait(driver, duration, frequency).until(EC.visibility_of_element_located((By.TAG_NAME, tag_name)))

    # Captcha solver for reCaptcha V2
    def solve_captcha(self, driver):
        # Check if captcha is appeared
        try:
            self.wait_until_visible(driver=driver, css_selector='[class="g-recaptcha"]', duration=1)
        except:
            return
        self.LOGGER.info(f'Solving captcha')
        captcha_page_url = "https://www.coinmarketcap.com/"

        # Solve GeeTest challenge
        captcha_response = self.twocaptcha_solver.geetest(gt='f1ab2cdefa3456789012345b6c78d90e', challenge='12345678abc90123d45678ef90123a456b', url=captcha_page_url)

        captcha_token = captcha_response["code"]
        self.LOGGER.info(f'Captcha token: {captcha_token}')
        self.LOGGER.info(f'Submitting captcha')
        # self.wait_until_visible(driver=driver, css_selector='[id="g-recaptcha-response"]')
        driver.execute_script(f'document.getElementById("g-recaptcha-response").innerHTML="{captcha_token}";')
        driver.execute_script(f"___grecaptcha_cfg.clients['0']['V']['V']['callback']('{captcha_token}');")
        self.LOGGER.info(f'Captcha submitted successfully')
        try:
            self.wait_until_visible(driver=driver, css_selector='[class="alert alert-warn"]', duration=3)
            alert = driver.find_element(By.CSS_SELECTOR, '[class="alert alert-warn"]').text[:-2]
            sleep(1)
            if 'A system error has occurred' in alert:
                self.LOGGER.info(f'An Error occurred: {alert}')
        except:
            pass

    # Solve GeeTest Puzzle using Pillow and OpenCV
    def solve_puzzle(self, driver, image_url):
        response = requests.get(image_url)
        s = int(time.time())

        file_path = os.path.join('puzzles', f'{s}.png')
        with open(file_path, 'wb') as f:
            f.write(response.content)

        img = Image.open(file_path)
        img1 = np.array(img.convert('RGB'))
        img_blur = cv2.GaussianBlur(img1, (3, 3), 0)
        img_gray = cv2.cvtColor(img_blur, cv2.COLOR_BGR2GRAY)
        img_canny = cv2.Canny(img_gray, 250, 250)
        img_edges = Image.fromarray(img_canny)
        captcha = img_edges.crop((0, 0, 59, 192))
        bbox = captcha.getbbox()
        captcha = captcha.crop(bbox)
        remaining = img_edges.crop((61, 0, img.width, 192))

        img_rgb = np.stack((remaining,) * 3, axis=-1)
        template = np.stack((captcha,) * 3, axis=-1)
        w, h = template.shape[:-1]

        res = cv2.matchTemplate(img_rgb, template, cv2.TM_CCOEFF_NORMED)
        for i in range(10, 1, -1):

            threshold = i / 10
            loc = np.where(res >= threshold)
            if len(loc[0]) > 0:
                break
        loc = np.where(res >= threshold)
        for pt in zip(*loc[::-1]):
            cv2.rectangle(img_rgb, pt, (pt[0] + w, pt[1] + h), (0, 0, 255), 2)

        offset = loc[1][0]
        # scrollBar = driver.find_element(By.CSS_SELECTOR, 'div.bs-slide-thumb')
        print(f'Moving the puzzle to {offset}')
        slider = driver.find_element(By.CSS_SELECTOR, '[class="bs-slide-thumb-arrow"]')
        ActionChains(driver).drag_and_drop_by_offset(slider, offset, 0).perform()
        try:
            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, '.avatar-img ')))
            print("Login successful")
        except:
            print("Captcha error")
        driver.save_screenshot('screenshot.png')
        return offset

    # Login to the CoinMarketCap
    def login_coinmarketcap(self, driver, email, password):
        self.LOGGER.info(f'Signing-in to CoinMarketCap account: {email}')
        self.LOGGER.info(f'Requesting CoinMarketCap: {str(self.url_cmc)} Account: {email}')
        driver.get(self.url_cmc)
        self.LOGGER.info('Filling credentials')
        sleep(3)
        try:
            # Click Login Button
            self.wait_until_visible(driver=driver, css_selector='[data-btnname="Log In"]', duration=5)
            driver.find_element(By.CSS_SELECTOR, '[data-btnname="Log In"]').click()

            # Enter Email
            self.wait_until_visible(driver=driver, css_selector='input[type="email"]', duration=5)
            driver.find_element(By.CSS_SELECTOR, 'input[type="email"]').send_keys(email)
            sleep(1)

            # Enter Password
            driver.find_element(By.CSS_SELECTOR, 'input[type="password"]').send_keys(password)

            # Click Login
            driver.find_element(By.CSS_SELECTOR, '[class="sc-a4a6801b-0 dPXqEb"]').click()
            sleep(5000)
            self.LOGGER.info(f'Login clicked')
            self.wait_until_visible(driver=driver, css_selector='.css-jyuqmw', duration=10)
            self.LOGGER.info(f'Captcha found')
            captcha_img_url = driver.find_element(By.CSS_SELECTOR, '[class="bs-main-image"]').get_attribute('style').split('"')[1]
            sleep(1)
            self.solve_puzzle(driver=driver, image_url=captcha_img_url)
        except:
            pass
        try:
            self.wait_until_visible(driver=driver, css_selector='.avatar-img ', duration=10)
            self.LOGGER.info('Successful sign-in')
        except:
            pass

    # Main method to handle all the functions
    def main(self):
        freeze_support()
        self.enable_cmd_colors()
        self.banner()
        self.LOGGER.info(f'CMCBot launched')
        email = self.settings["Settings"]["Email"]
        password = self.settings["Settings"]["Password"]
        driver = self.get_driver()
        self.login_coinmarketcap(driver=driver, email=email, password=password)


if __name__ == '__main__':
    CMCBot().main()
