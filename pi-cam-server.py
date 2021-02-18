from bottle import run, static_file, route, Bottle
from os import listdir
from os.path import isfile, join, exists
from datetime import datetime
from sys import platform
import os, socket, threading
from cheroot.wsgi import Server as CherryPyWSGIServer
version="2"

host=socket.gethostname()

if platform=="win32":
    folder='C:\\Users\\remote\\Desktop\\test\\'
else:
    folder='/home/pi/photos/'

event=threading.Event()

def takeManyPhotos():
    while not event.is_set():
        file=host+"-"+datetime.now().strftime("%Y%m%d_%H_%M_%S")+".jpg"
        os.system("raspistill -o "+folder+file)
        print (file)

x = threading.Thread(target=takeManyPhotos, args=())
app=Bottle()
@app.get('/ping')
def ping():
    return "pong"

@app.get('/getone')
def getone():
    file=listFiles()[0]
    return file

@app.get('/takephoto')
def takephoto():
    file=host+"-"+datetime.now().strftime("%Y%m%d_%H_%M_%S")+".jpg"
    os.system("raspistill -o "+folder+file)
    html='<html><body><img src="http://'+host+"/download/"+file+'" alt=""></body></html>'
    return html

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
    os.system("sudo /home/pi/updatescript &")
    return "updated"

@app.get('/startshooting')
def startshooting():
    global event
    event.clear()
    global x
    if not x.is_alive():
        try:
            x.start()
            print ("reusing thread")
        except RuntimeError: #occurs if thread is dead
            x = threading.Thread(target=takeManyPhotos, args=()) #create new instance if thread is dead
            x.start() #start thread
            print ("new thread")
    return "started"

@app.get('/stopshooting')
def stopshooting():
    event.set()
    return "stopped"

@app.get('/download/<file>')
def download(file):
    return static_file(file, root=folder, download=file)

@app.get('/delete/<file>')
def delete(file):
    if exists(folder+file):
        os.remove(folder+file)
        return ("deleted "+file)
    else:
        return ("can't find "+file)

@app.get('/deleteall')
def deleteall():
    os.system("rm /home/pi/photos/*")

@app.get('/count')
def count():
    return str(len(listFiles()))

@app.get('/v')
def ver():
    return version

def listFiles():
    return   [f for f in listdir(folder) if isfile(join(folder, f))]

server = CherryPyWSGIServer(
    ('0.0.0.0', 80),app,
    server_name='My_App',
    numthreads=30)

server.start()