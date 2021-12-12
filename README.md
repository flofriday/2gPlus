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
