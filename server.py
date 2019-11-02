# --- SERVER CONFIGURATION ---
INTERFACE = '0.0.0.0'  # 0.0.0.0 to serve on all available interfaces
PORT = 31415
USERPASS = None  # "username:password" or None, overridden by sys args
# --- END SERVER CONFIGURATION --
VERSION = '0.1.0'

import base64
import http.server
import json
import logging
import sys

import RPi.GPIO as GPIO


class IORequestHandler(http.server.BaseHTTPRequestHandler):

    channels = {
        4: 7,
        5: 29,
        6: 31,
        12: 32,
        13: 33,
        16: 36,
        17: 11,
        18: 12,
        19: 35,
        20: 38,
        21: 40,
        22: 15,
        23: 16,
        24: 18,
        25: 22,
        26: 37,
        27: 13,
    }
    logger = logging.getLogger('RESTberryPi')

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
                self.logger.error(e.args[0])
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
                self.logger.error(e.args[0])
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
                    self.logger.error(e.args[0])
                    return 500, 'ERROR READING ALL INPUTS'
            # else, the value is not a number
            return 400, 'INVALID GPIO {}'.format(command[0])
        if channel not in self.channels:
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
                    self.logger.error(e.args[0])
                    return 500, 'ERROR CONFIGURING INPUT {}'.format(channel)
            if method.lower() == 'disable':
                try:
                    GPIO.cleanup(channel)
                    return 200, 'OK'
                except Exception as e:
                    self.logger.error(e.args[0])
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
            self.logger.error(e.args[0])
            return 500, 'ERROR READING INPUT {}'.format(channel)

    def log_message(self, _, *args):
        endpoint = args[0].split(' ')[1]
        status = int(args[1])
        if status == 200:
            msg = '200 {}'.format(endpoint)
            self.logger.debug(msg)
        elif status == 500:
            msg = '500 Exception while handling {}'.format(endpoint)
            self.logger.warning(msg)
        else:
            msg = '{} {}'.format(status, endpoint)
            self.logger.warning(msg)

    def OUTPUTS(self, command):
        """ Called when handling the /outputs resource."""
        if not command:
            # read all outputs
            try:
                states = self._read_all_gpio(GPIO.OUT)
                return 200, states
            except Exception as e:
                self.logger.error(e.args[0])
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
                    self.logger.error(e.args[0])
                    return 500, 'ERROR READING ALL OUTPUTS'
            # else, the value is not a number
            return 400, 'INVALID GPIO: {}'.format(command[0])
        if channel not in self.channels:
            return 400, 'INVALID GPIO: {}'.format(channel)
        try:
            # parse the method, raises IndexError if not given
            method = command[1]
            if method.lower() == 'enable':
                try:
                    GPIO.setup(channel, GPIO.OUT)
                    return 200, 'OK'
                except Exception as e:
                    self.logger.error(e.args[0])
                    return 500, 'ERROR CONFIGURING OUTPUT {}'.format(channel)
            if method.lower() == 'disable':
                try:
                    GPIO.output(channel, False)
                    GPIO.cleanup(channel)
                    return 200, 'OK'
                except Exception as e:
                    self.logger.error(e.args[0])
                    return 500, 'ERROR DISABLING OUTPUT {}'.format(channel)
            if method.lower() == 'true':
                try:
                    GPIO.output(channel, True)
                    return 200, 'OK'
                except Exception as e:
                    self.logger.error(e.args[0])
                    return 500, 'ERROR SETTING OUTPUT {} HI'.format(channel)
            if method.lower() == 'false':
                try:
                    GPIO.output(channel, False)
                    return 200, 'OK'
                except Exception as e:
                    self.logger.error(e.args[0])
                    return 500, 'ERROR SETTING OUTPUT {} LO'.format(channel)
            if method.lower() == 'toggle':
                try:
                    state = GPIO.input(channel)
                    GPIO.output(channel, not state)
                    return 200, 'OK'
                except Exception as e:
                    self.logger.error(e.args[0])
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
            self.logger.error(e.args[0])
            return 500, 'ERROR READING OUTPUT {}'.format(channel)

    def _authenticate(self):
        try:
            if self.headers['Authorization'] != self.token:
                # user:pass is not a match
                return False
            # else, authorized!
            return True
        except AttributeError:
            # no auth set
            return True

    def _get_status(self):
        """ Get a JSON representation of device status."""
        gpio = dict()
        for channel in self.channels:
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
                        'pin': self.channels[channel],
                        'state': None,
                    }
                    continue
                gpio[channel] = {
                    'mode': 'input',
                    'pin': self.channels[channel],
                    'state': state,
                }
            elif function == GPIO.OUT:
                state = bool(GPIO.input(channel))
                gpio[channel] = {
                    'mode': 'output',
                    'pin': self.channels[channel],
                    'state': state,
                }
            else:
                # this channel is configured as something else
                gpio[channel] = {
                    'mode': None,
                    'pin': self.channels[channel],
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
        for channel in self.channels:
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


if __name__ == '__main__':

    def get_token(key):
        key = key.encode('utf-8')
        key = base64.b64encode(key)
        key = key.decode('utf-8')
        token = 'Basic {}'.format(key)
        return token

    # parse command line args
    help = 'INVALID ARGS, TRY: python3 server.py 31415 username:password'
    args = sys.argv[1:]  # first arg is this file
    if not args:
        pass
    elif len(args) == 1:
        # either a port (int), or key (contains ':')
        try:
            PORT = int(args[0])
        except ValueError:
            # not a number, must be the key
            if ':' not in args[0]:
                # not the expected user:pass either
                print(help)
                sys.exit()
            # it is a key, encode and store it in a class attribute
            IORequestHandler.token =  get_token(args[0])
    elif len(args) == 2:
        # both port and key passed
        try:
            PORT = int(args[0])
            assert ':' in args[1]
        except (ValueError, AssertionError):
            print(help)
            sys.exit()
        # encode and store the token in a class attribute
        IORequestHandler.token = get_token(args[0])
    else:
        print(help)
        sys.exit()
    if USERPASS and not hasattr(IORequestHandler, 'token'):
        # Auth was set in this file, and not overridden by command line args,
        # encode and store the token in a class attribute
        IORequestHandler.token = get_token(USERPASS)

    # setup logging
    logger = logging.getLogger('RESTberryPi')
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        fmt='%(asctime)s %(levelname)-8s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S')
    # log to file
    file_handler = logging.FileHandler('server.log', mode='a+')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    # log to stdout, for example when running in a terminal
    screen_handler = logging.StreamHandler(stream=sys.stdout)
    screen_handler.setFormatter(formatter)
    logger.addHandler(screen_handler)

    # create and run server
    httpd = http.server.HTTPServer(
        server_address=(INTERFACE, PORT),
        RequestHandlerClass=IORequestHandler)
    GPIO.setmode(GPIO.BCM)
    if INTERFACE != '0.0.0.0':
        host = '{}:{}'.format(INTERFACE, PORT)
    else:
        host = 'port {}'.format(PORT)
    msg = 'Running server on {}'.format(host)
    if USERPASS or hasattr(IORequestHandler, 'token'):
        msg += ' with Basic Auth'
    logger.info(msg)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        # running inside terminal, catch this to shut down cleanly,
        # and feed an emtpy line just so it's pretty
        print()
    # set any outputs low before cleaning up
    for channel in IORequestHandler.channels:
        function = GPIO.gpio_function(channel)
        if function == GPIO.OUT:
            try:
                GPIO.output(channel, False)
            except Exception as e:
                self.logger.debug(e.args[0])
    GPIO.cleanup()
