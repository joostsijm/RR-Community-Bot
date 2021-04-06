"""
Authentication handeler module
"""

import sys
import re
import time

import requests
import cfscrape

from rival_regions_wrapper import LOGGER
from rival_regions_wrapper.cookie_handler import CookieHandler
from rival_regions_wrapper.browser import Browser


class RRClientException(Exception):
    """RR exception"""
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)
        LOGGER.warning('RRClientException')


class SessionExpireException(Exception):
    """Raise when session has expired"""
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)
        LOGGER.warning('Session has expired')


class NoLogginException(Exception):
    """Raise exception when client isn't logged in"""
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)
        LOGGER.warning('Not logged in')


class NoCookieException(Exception):
    """Raise exception when there is no cookie found"""
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)
        LOGGER.warning('No cookie found')


def session_handler(func):
    """Handle expired sessions"""
    def wrapper(*args, **kwargs):
        instance = args[0]
        return try_run(instance, func, *args, **kwargs)

    def try_run(instance, func, *args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (SessionExpireException, ConnectionError, ConnectionResetError):
            CookieHandler.remove_cookie(instance.username)
            instance.login()
            return try_run(instance, func, *args, **kwargs)
        except NoLogginException:
            instance.login()
            return try_run(instance, func, *args, **kwargs)

    return wrapper


class AuthenticationHandler:
    """class for RR client"""
    cookie = None
    var_c = None
    login_method = None
    username = None
    password = None
    session = None

    def __init__(self, show_window=False):
        self.show_window = show_window
        LOGGER.info('Initialize authentication handler, show window: "%s"',
                    self.show_window)

    def set_credentials(self, credentials):
        """Set the credentials"""
        LOGGER.info('"%s": setting credentials', credentials['username'])
        self.login_method = credentials['login_method']
        self.username = credentials['username']
        self.password = credentials['password']
        self.login()

    def login(self):
        """Login user if needed"""
        LOGGER.info(
                '"%s": start login, method: "%s"',
                self.username, self.login_method
            )
        cookies = CookieHandler.get_cookies(self.username)
        if not cookies:
            cookies = []
            LOGGER.info(
                    '"%s": no cookie, new login, method "%s"',
                    self.username, self.login_method
                )

            login_methods = {
                'g': self.login_google,
                'google': self.login_google,
                'v': self.login_vk,
                'vk': self.login_vk,
                'f': self.login_facebook,
                'facebook': self.login_facebook,
            }

            auth_text = requests.get("https://rivalregions.com").text
            browser = Browser(showWindow=self.show_window)

            if self.login_method in login_methods:
                browser = login_methods[self.login_method](browser, auth_text)
            else:
                LOGGER.info(
                        '"%s": Invalid login method "%s"',
                        self.username, self.login_method
                    )
                sys.exit()

            LOGGER.info('"%s": Get PHPSESSID', self.username)
            browser_cookie = browser.get_cookie('PHPSESSID')
            if browser_cookie:
                expiry = browser_cookie.get('expiry', None)
                value = browser_cookie.get('value', None)
                LOGGER.info(
                        '"%s": "value": %s, "expiry": %s',
                        self.username, value, expiry
                    )
                cookie = CookieHandler.create_cookie(
                        'PHPSESSID',
                        expiry,
                        value
                    )
                cookies.append(cookie)
            else:
                raise NoCookieException()

            cookie_names = ['rr_f']
            for cookie_name in cookie_names:
                browser_cookie = browser.get_cookie(cookie_name)
                if browser_cookie:
                    LOGGER.info(
                        '"%s": Get %s',
                        self.username, cookie_name
                    )
                    expiry = browser_cookie.get('expiry', None)
                    value = browser_cookie.get('value', None)
                    cookies.append(
                        CookieHandler.create_cookie(
                            cookie_name,
                            expiry,
                            value
                        )
                    )
                    LOGGER.info(
                            '"%s": "value": %s, "expiry": %s',
                            self.username, value, expiry
                        )
                else:
                    raise NoCookieException()

            CookieHandler.write_cookies(self.username, cookies)
            LOGGER.debug('"%s": closing login tab', self.username)
            browser.close_current_tab()
        else:
            LOGGER.info('"%s": Cookies found', self.username)

        self.session = cfscrape.CloudflareScraper()
        for cookie in cookies:
            self.session.cookies.set(**cookie)

        LOGGER.debug('"%s": set the var_c', self.username)
        response = self.session.get('https://rivalregions.com/#overview')
        lines = response.text.split("\n")
        for line in lines:
            if re.match("(.*)var c_html(.*)", line):
                var_c = line.split("'")[-2]
                LOGGER.debug('"%s": got var_c: %s', self.username, var_c)
                self.var_c = line.split("'")[-2]

    # This is working
    def login_google(self, browser, auth_text):
        """login using Google"""
        LOGGER.info('"%s": Login method Google', self.username)
        auth_text1 = auth_text.split('\t<a href="')
        auth_text2 = auth_text1[1].split('" class="sa')
        time.sleep(1)
        browser.go_to(auth_text2[0])

        LOGGER.info('"%s": Typing in username', self.username)
        browser.type(self.username, into='Email')

        LOGGER.info('"%s": pressing next button', self.username)
        browser.click(css_selector="#next")
        time.sleep(2)

        LOGGER.info('"%s": Typing in password', self.username)
        browser.type(self.password, css_selector="input")

        LOGGER.info('"%s": pressing sign in button', self.username)
        browser.click(css_selector="#submit")
        time.sleep(3)

        # Some why it wont click and login immediately. This seems to work
        time.sleep(1)
        browser.go_to(auth_text2[0])
        time.sleep(1)
        browser.go_to(auth_text2[0])
        time.sleep(1)
        browser.click(
            css_selector="#sa_add2 > div:nth-child(4) > a.sa_link.gogo > div"
        )
        time.sleep(3)
        return browser

    # IDK if this is working
    def login_vk(self, browser, auth_text):
        """login using VK"""
        LOGGER.info('Login method VK')
        auth_text1 = auth_text.split("(\'.vkvk\').attr(\'url\', \'")
        auth_text2 = auth_text1[1].split('&response')

        browser.go_to(auth_text2[0])
        browser.type(self.username, into='email')
        browser.type(
                self.password,
                xpath="/html/body/div/div/div/div[2]/form/div/div/input[7]"
        )
        browser.click('Log in')
        return browser

    # IDK if this is working
    def login_facebook(self, browser, auth_text):
        """login using Facebook"""
        LOGGER.info('Login method Facebook')
        auth_text1 = \
            auth_text.split('">\r\n\t\t\t\t<div class="sa_sn imp float_left" ')
        auth_text2 = auth_text1[0].split('200px;"><a class="sa_link" href="')
        url = auth_text2[1]

        browser.go_to(url)
        browser.type(self.username, into='Email')
        browser.type(self.password, into='Password')
        browser.click('Log In')
        time.sleep(5)
        browser.click(css_selector='.sa_sn.imp.float_left')
        return browser

    @session_handler
    def get(self, path, add_var_c=False):
        """Send get request to Rival Regions"""
        if path[0] == '/':
            path = path[1:]

        params = {}
        if add_var_c:
            params['c'] = self.var_c

        LOGGER.info(
                '"%s": GET: "%s" var_c: %s', self.username, path, add_var_c
            )
        if self.session:
            response = self.session.get(
                url='https://rivalregions.com/{}'.format(path),
                params=params
            )
            self.check_response(response)
        else:
            raise NoLogginException()
        return response.text

    @session_handler
    def post(self, path, data=None):
        """Send post request to Rival Regions"""
        if path[0] == '/':
            path = path[1:]
        if not data:
            data = {}
        data['c'] = self.var_c

        LOGGER.info('"%s": POST: "%s"', self.username, path)
        if self.session:
            response = self.session.post(
                "https://rivalregions.com/{}".format(path),
                data=data
            )
            self.check_response(response)
        else:
            raise NoLogginException()
        return response.text

    @classmethod
    def check_response(cls, response):
        """Check resonse for authentication"""
        if "Session expired, please, reload the page" in response.text or \
                'window.location="https://rivalregions.com";' in response.text:
            raise SessionExpireException()
