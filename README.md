# 2gPlus

Simple service for enforcing 2g+ rules at private gatherings

# Getting started

Install Python3.8 (or higher), zbar, popper

Install all dependencies with:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export FLASK_APP=twogplus FLASK_ENV=development
flask run
```

This launces a simple webserver which can only be accessed from the localhost.

**Note:** Don't use this server in production, it is insecure and low
performance.

## Deployment

How we deploy this app on Ubuntu.

Install the requirements with:

```bash
sudo apt -y install python3-venv python3-pip libzbar0 libxml2-dev libxmlsec1-dev libxmlsec1-openssl poppler-utils
```

Create a virtual env with:

```bash
python3 -m venv venv
```

Copy `instance/config_example.toml` to `instance/config.toml` and edit all
the fields in it.

Open `twogplus.service` and edit the username and all paths to the working
directory.

Start the systemd service with:

```bash
sudo cp twogplus.service /etc/systemd/system
sudo systemctl daemon-reload
sudo systemctl enable twogplus.service
sudo systemctl start twogplus.service
```

The service should now be up and running 🎉

To stop the service run:

```bash
sudo systemctl stop twogplus.service
```

To update the service to a new version (commit) run:

```bash
git pull
sudo systemctl restart twogplus.service
```
