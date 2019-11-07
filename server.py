# --- SERVER CONFIGURATION ---
INTERFACE = "0.0.0.0"  # 0.0.0.0 to serve on all available interfaces
PORT = 31415
USERPASS = None  # "username:password" or None, overridden by sys args
# --- END SERVER CONFIGURATION --
VERSION = "0.1.1"

import base64
import http.server
import json
import logging
import signal
import sys
import threading

import RPi.GPIO as GPIO
import util


class IORequestHandler(http.server.BaseHTTPRequestHandler):

    def do_GET(self):
        """ Called when handling GET requests."""
        if not self._authenticate():
            self._send_response(401, 'UNAUTHORIZED')
            return
        resource, command = self._parse_path()
        if not resource:
            # top-level request
            try:
                self._send_response(200, self._get_status())
            except Exception as e:
                self.server.logger.error(e.args[0])
                self._send_response(500, 'ERROR GETTING GPIO STATUS')
            return
        # else, call `RESOURCE` and pass it `command`
        try:
            status, message = getattr(self, resource.upper())(command)
        except AttributeError:
            status = 400
            message = 'INVALID RESOURCE {}'.format(resource)
        self._send_response(status, message)

    def INPUTS(self, command):
        """ Called when handling the /inputs resource."""
        if not command:
            # read all inputs
            try:
                states = self._read_all_gpio(GPIO.IN)
                return 200, states
            except Exception as e:
                self.server.logger.error(e.args[0])
                return 500, 'ERROR READING ALL INPUTS'
        # else, read a specific channel
        try:
            channel = int(command[0])
        except ValueError:
            if not command[0]:
                # empty string, results from a trailing slash in url,
                # treat this as an empty path and read all
                try:
                    states = self._read_all_gpio(GPIO.IN)
                    return 200, states
                except Exception as e:
                    self.server.logger.error(e.args[0])
                    return 500, 'ERROR READING ALL INPUTS'
            # else, the value is not a number
            return 400, 'INVALID GPIO {}'.format(command[0])
        if channel not in util.channels:
            return 400, 'INVALID GPIO {}'.format(channel)
        try:
            # parse the method, raises IndexError if not given
            method = command[1]
            if method.lower() == 'enable':
                try:
                    # TO DO: pull up/down resistor settings
                    GPIO.setup(channel, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
                    return 200, 'OK'
                except Exception as e:
                    self.server.logger.error(e.args[0])
                    return 500, 'ERROR CONFIGURING INPUT {}'.format(channel)
            if method.lower() == 'disable':
                try:
                    GPIO.cleanup(channel)
                    return 200, 'OK'
                except Exception as e:
                    self.server.logger.error(e.args[0])
                    return 500, 'ERROR DISABLING INPUT {}'.format(channel)
            if method:
                # unrecognized method
                return 400, 'INVALID METHOD {}'.format(method)
        except IndexError:
            # method was not given, read the resource
            pass
        # if we've made it here, it's a read request
        try:
            state = bool(GPIO.input(channel))
            return 200, state
        except Exception as e:
            self.server.logger.error(e.args[0])
            return 500, 'ERROR READING INPUT {}'.format(channel)

    def log_message(self, _, *args):
        # this overridden method passes logs onto our custom logger
        endpoint = args[0].split(' ')[1]
        status = int(args[1])
        if status == 200:
            msg = '200 {}'.format(endpoint)
            self.server.logger.debug(msg)
        elif status == 500:
            msg = '500 Exception while handling {}'.format(endpoint)
            self.server.logger.error(msg)
        else:
            msg = '{} {}'.format(status, endpoint)
            self.server.logger.warning(msg)

    def OUTPUTS(self, command):
        """ Called when handling the /outputs resource."""
        if not command:
            # read all outputs
            try:
                states = self._read_all_gpio(GPIO.OUT)
                return 200, states
            except Exception as e:
                self.server.logger.error(e.args[0])
                return 500, 'ERROR READING ALL OUTPUTS'
        # else, read a specific channel
        try:
            channel = int(command[0])
        except ValueError:
            if not command[0]:
                # empty string, results from a trailing slash in url,
                # treat this as an empty path and read all
                try:
                    states = self._read_all_gpio(GPIO.OUT)
                    return 200, states
                except Exception as e:
                    self.server.logger.error(e.args[0])
                    return 500, 'ERROR READING ALL OUTPUTS'
            # else, the value is not a number
            return 400, 'INVALID GPIO: {}'.format(command[0])
        if channel not in util.channels:
            return 400, 'INVALID GPIO: {}'.format(channel)
        try:
            # parse the method, raises IndexError if not given
            method = command[1]
            if method.lower() == 'enable':
                try:
                    GPIO.setup(channel, GPIO.OUT)
                    return 200, 'OK'
                except Exception as e:
                    self.server.logger.error(e.args[0])
                    return 500, 'ERROR CONFIGURING OUTPUT {}'.format(channel)
            if method.lower() == 'disable':
                try:
                    GPIO.output(channel, False)
                    GPIO.cleanup(channel)
                    return 200, 'OK'
                except Exception as e:
                    self.server.logger.error(e.args[0])
                    return 500, 'ERROR DISABLING OUTPUT {}'.format(channel)
            if method.lower() == 'true':
                try:
                    GPIO.output(channel, True)
                    return 200, 'OK'
                except Exception as e:
                    self.server.logger.error(e.args[0])
                    return 500, 'ERROR SETTING OUTPUT {} HI'.format(channel)
            if method.lower() == 'false':
                try:
                    GPIO.output(channel, False)
                    return 200, 'OK'
                except Exception as e:
                    self.server.logger.error(e.args[0])
                    return 500, 'ERROR SETTING OUTPUT {} LO'.format(channel)
            if method.lower() == 'toggle':
                try:
                    state = GPIO.input(channel)
                    GPIO.output(channel, not state)
                    return 200, 'OK'
                except Exception as e:
                    self.server.logger.error(e.args[0])
                    return 500, 'ERROR TOGGLING OUTPUT {}'.format(channel)
            if method:
                # unrecognized method
                return 400, 'INVALID METHOD {}'.format(method)
        except IndexError:
            # method was not given, read the resource
            pass
        # if we've made it here, it's a read request
        try:
            state = bool(GPIO.input(channel))
            return 200, state
        except Exception as e:
            self.server.logger.error(e.args[0])
            return 500, 'ERROR READING OUTPUT {}'.format(channel)

    def _authenticate(self):
        if self.server.token is None:
            # no auth set
            return True
        if self.headers['Authorization'] != self.server.token:
            # user:pass is not a match
            return False
        # else, authorized!
        return True


    def _get_status(self):
        """ Get a JSON representation of device status."""
        gpio = dict()
        for channel, pin in util.channels.items():
            function = GPIO.gpio_function(channel)
            if function == GPIO.IN:
                # unconfigured channels show up as inputs for some reason,
                # test it to see if it's really an input
                try:
                    state = bool(GPIO.input(channel))
                except RuntimeError:
                    # this channel is not configured
                    gpio[channel] = {
                        'mode': None,
                        'pin': pin,
                        'state': None,
                    }
                    continue
                gpio[channel] = {
                    'mode': 'input',
                    'pin': pin,
                    'state': state,
                }
            elif function == GPIO.OUT:
                state = bool(GPIO.input(channel))
                gpio[channel] = {
                    'mode': 'output',
                    'pin': pin,
                    'state': state,
                }
            else:
                # this channel is configured as something else
                gpio[channel] = {
                    'mode': None,
                    'pin': pin,
                    'state': None,
                }
        status ={'GPIO': gpio}
        return status

    def _parse_path(self):
        path = self.path.split('/')
        path = path[1:]  # skip root in path
        resource = path[0]
        command = path[1:]
        return resource, command

    def _read_all_gpio(self, function):
        channels = {}
        for channel in util.channels:
            if GPIO.gpio_function(channel) != function:
                continue
            try:
                channels[channel] = bool(GPIO.input(channel))
            except RuntimeError:
                # unconfigured channels show up as inputs for some reason,
                # this channel is not configured, skip it
                continue
        return channels

    def _send_response(self, status, message):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        message = json.dumps(message)
        message = message.encode('utf-8')
        self.wfile.write(message)


class RESTberryPi(http.server.HTTPServer):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, RequestHandlerClass=IORequestHandler)
        self._thread = None
        self._token = None
        # handle OS signals
        signal.signal(signal.SIGINT, self.stop)
        signal.signal(signal.SIGTERM, self.stop)
        # setup logging
        self.logger = logging.getLogger('RESTberryPi')
        self.logger.setLevel(logging.INFO)
        formatter = logging.Formatter(
            fmt='%(asctime)s %(levelname)-8s %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S')
        file_handler = logging.FileHandler('server.log', mode='a+')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        screen_handler = logging.StreamHandler(stream=sys.stdout)
        screen_handler.setFormatter(formatter)
        self.logger.addHandler(screen_handler)

    @property
    def token(self):
        return self._token

    @property.setter
    def token(self, value):
        self._token = self.encode_token(value)

    def start(self):
        # set up GPIO
        GPIO.setmode(GPIO.BCM)
        # setup server
        address, port = self.server_address
        if address != '0.0.0.0':
            host = '{}:{}'.format(address, port)
        else:
            host = 'port {}'.format(port)
        msg = 'Running server on {}'.format(host)
        if self.token is not None:
            msg += ' with Basic Auth'
        self.logger.info(msg)
        self._thread = threading.Thread(target=self.serve_forever)
        self._thread.start()
        # block until server terminates, and reraise any exceptions
        try:
            self._thread.join()
        except KeyboardInterrupt:
            self.stop()
            self.logger.info('Exit.')

    def stop(self, signum, frame):
        logger.info('Shutting down')
        # set any outputs low before cleaning up
        for channel in util.channels:
            function = GPIO.gpio_function(channel)
            if function == GPIO.OUT:
                try:
                    GPIO.output(channel, False)
                except Exception as e:
                    # ignore exceptions, but log them for debugging
                    self.logger.debug(e.args[0])
        GPIO.cleanup()
        self.shutdown()
        server.logger.info('Exit')

    @staticmethod
    def encode_token(userpass):
        if userpass is None:
            return None
        userpass = userpass.encode('utf-8')
        userpass = base64.b64encode(userpass)
        userpass = userpass.decode('utf-8')
        token = 'Basic {}'.format(userpass)
        return token


if __name__ == '__main__':
    args = sys.argv[1:]  # first arg is this file
    try:
        port, auth = util.parse_sys_args(args)
    except Exception as e:
        sys.exit(e.args[0])
    # use values set at top of file if not overridden
    port = port or PORT
    auth = auth or USERPASS
    RESTberryPi.token = auth
    server = RESTberryPi(server_address=(INTERFACE, port))
    server.start()
