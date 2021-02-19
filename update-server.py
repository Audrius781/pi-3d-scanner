from bottle import run, static_file, route, Bottle
import os
from cheroot.wsgi import Server as CherryPyWSGIServer


app=Bottle()
@app.get('/ping')
def ping():
    return "pong"

@app.get('/halt')
def halt():
    os.system("sudo halt")
    return "halt"

@app.get('/reboot')
def reboot():
    os.system("sudo reboot")
    return "reboot"

@app.get('/update')
def update():
    os.system("sudo /home/pi/autoupdate &")
    return "updated"


server = CherryPyWSGIServer(
    ('0.0.0.0', 81),app,
    server_name='My_App',
    numthreads=1)

server.start()