# create a virtual environment to run inside
pip3 install virtualenv --user
virtualenv -p python3 env
source env/bin/activate


# install requirements
pip3 install --upgrade -r requirements.txt


# create systemd service
echo \
'[Unit]
Description=RESTberryPi
After=network.target

[Service]
Type=idle
WorkingDirectory='$(pwd)'
ExecStart='$(pwd)'/env/bin/python3 server.py
StandardOutput=null
StandardError=journal

[Install]
WantedBy=multi-user.target' > RESTberryPi.service
sudo mv RESTberryPi.service /etc/systemd/system/


# start server
sudo systemctl daemon-reload
sudo systemctl enable RESTberryPi.service
sudo systemctl start RESTberryPi.service
