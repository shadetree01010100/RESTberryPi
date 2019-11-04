# RESTberryPi

A simple, RESTful API for IO on the Raspberry Pi

---

## Easy Setup

In your Pi's terminal (or ssh), clone this repository and run the included script to automatically:
- install requirements into a virtual environment
  - installs and uses [virtualenv](https://virtualenv.pypa.io/en/latest/)
- configure a [systemd service](https://wiki.debian.org/systemd) to start with the Pi
- start the HTTP server

```
cd ~
git clone git@github.com:shadetree01010100/RESTberryPi.git
cd RESTberryPi
sh setup.sh
```

The installed `systemd` service will start automatically with the Pi, and can be controlled using systemd commands:

```
sudo systemctl <restart|start|status|stop> RESTberryPi.service
```

---

## API Usage

Resources are organized following the pattern `/resource/instance/method`, and are not case-sensitive. Top-level `GET` requests (`http://<host>:<port>`) return a JSON representation of the available IO, including the 17 GPIO pins that are available for general use. For example:

```
curl raspberrypi.local:31415
  {
    "GPIO": {
      "4": {
        "mode": <"input"|"output"|null>,
        "pin": 7,
        "state": <true|false|null>
      },
      ...
    }
  }
```

For each GPIO, `mode` and `state` will both be `null` if the channel has not been enabled; `state` is otherwise a boolean and `mode` a string. The integer `pin` is a mapping to the physical pin number of the Pi's 40-pin GPIO header, included only for convenience.

Each available channel is exposed through the `/input` and `/output` resources, and can be accessed and controlled using `GET` requests. Note that a GPIO must be enabled before it can be used, and inputs are configured with a pull-down resistor. A `true` value means the pin's voltage to ground (logic-level) is high.

```
GET /inputs
# 200 {}

GET /inputs/4
# 500 "ERROR READING INPUT 4"

GET /inputs/4/enable
# 200 "OK"

GET /inputs
# 200 {"4": false}

GET /inputs/4
# 200 false

GET /inputs/4/disable
# 200 "OK"

GET /inputs/3
# 400 "INVALID GPIO 3"
```

Outputs follow the same pattern, and in addition they can be set high or low with the `/true` and `/false` methods, respectively:

```
GET /outputs/5/enable
# 200 "OK"

GET /outputs/5
# 200 false

GET /outputs/5/true
# 200 "OK"

GET /outputs
# 200 {"5": true}
```

Outputs are set low when disabled, and when the server exits.

### Resources

| Resource 	| Methods                      	|
|----------	|------------------------------	|
| inputs   	| enable, disable              	|
| outputs  	| enable, disable, true, false 	|

Header pin mapping:

| GPIO Channel 	| Pin # |
|--------------	|-----	|
| 4            	| 7   	|
| 5            	| 29  	|
| 6            	| 31  	|
| 12           	| 32  	|
| 13           	| 33  	|
| 16           	| 36  	|
| 17           	| 11  	|
| 18           	| 12  	|
| 19           	| 35  	|
| 20           	| 38  	|
| 21           	| 40  	|
| 22           	| 15  	|
| 23           	| 16  	|
| 24           	| 18  	|
| 25           	| 22  	|
| 26           	| 37  	|
| 27           	| 13  	|

---

## Authentication

Basic Authorization is provided, to configure it open `server.py` find the server configuration at the top of the file:

```
# --- SERVER CONFIGURATION ---
INTERFACE = '0.0.0.0'
PORT = 31415
USERPASS = None
# --- END SERVER CONFIGURATION --
```

Set the username and password, including punctuation:

```
USERPASS = "username:password"
```

Restart the server for changes to take effect:

```
sudo systemctl restart RESTberryPi.service`.
```

When running inside a terminal (see below) you can pass an optional value to override this setting.

---

## Manual Setup and Run

To run in your terminal using Python3, you will first need to install the requirements. Currently the only module used that is not part of the standard library is [RPi.GPIO](https://pypi.org/project/RPi.GPIO/).

```
cd ~
git clone git@github.com:shadetree01010100/RESTberryPi.git
cd RESTberryPi
pip3 install -r requirements.txt --user
python3 server.py
```

Or, if you ran `setup.sh`, this is already done for you, and you can simply activate and use the [virtual environment](https://virtualenv.pypa.io/en/latest/userguide/#activate-script):

```
cd ~/RESTberryPi
source env/bin/activate
python3 server.py
deactivate
```

Or, instead of activating the virtual environment, you can use its Python3 executable directly:

```
cd ~/RESTberryPi
env/bin/python3 server.py
```

Press `[CTRL] + [C]` to exit.

`server.py` also accepts two optional command line arguments setting the server port and authorization. These values override any configuration inside `server.py`:

```
python3 server.py 31415 username:password
```

---

## To Do

- Save state to disk, and load it when started
- Include metadata (version) in response
- Move script contents into a more competent structure
- Implement other HTTP methods, for example `DELETE /inputs/4` should be synonymous with `GET /inputs/4/disable`
- Webhooks for asynchronous IO?
- Add `/serial`, etc. resources?
