from bottle import run, static_file, route, Bottle
from datetime import datetime
from sys import platform
import os, socket, threading, glob, json
from cheroot.wsgi import Server as CherryPyWSGIServer
version="1.2"

host=socket.gethostname()
status="stopped"

# Folderiai
if platform=="win32":
    folder='C:\\Users\\remote\\Desktop\\test\\'
    homefolder='C:\\Users\\remote\\Desktop\\'
else:
    folder='/home/pi/photos/'
    homefolder='/home/pi/'

# Bandomuoji nuotrauka patikrinti ar veikia kamera
os.system("rm "+homefolder+"test.jpg")
os.system("raspistill -o "+homefolder+"test.jpg &")
cameraStatus="Error"
if os.path.exists(homefolder+"test.jpg"):
    cameraStatus="Ready"

# Konfiguracija is failo arba sukurti nauja faila

def saveconfig():
    global config
    with open(homefolder+"config.json", 'w') as f:
         json.dump(config, f)

if os.path.exists(homefolder+"config.json"):
  with open(homefolder+"config.json") as f:
    config = json.load(f)
else:
    config= {'rotate': False}
    saveconfig()
    

# Signalas sustabdyti fotografavima
event=threading.Event()

# Padaryti viena nuotrauka ir irasyti i SD kortele
def takePhoto(path):
    params=""
    if config["rotate"]:
        params=params+"-vf -hf "
    os.system("raspistill "+params+" -o "+path)

# Daryti daug nuotrauku iki kol negautas signalas sustabdyti
def takeManyPhotos():
    while not event.is_set():
        file=host+"-"+datetime.now().strftime("%Y%m%d_%H_%M_%S")+".jpg"
        takePhoto(folder+file)
        print (file)
    global status
    status="stopped"
x = threading.Thread(target=takeManyPhotos, args=())
app=Bottle()

@app.get('/status')
def ping():
    return cameraStatus

@app.get('/getone')
def getone():
    try:
        file=os.path.basename(listFiles()[0])
    except:
        file="none"
    return file

@app.get('/preview')
def preview():
    os.system("rm "+homefolder+"test.jpg")
    takePhoto(homefolder+"test.jpg")
    return static_file("test.jpg", root=homefolder, download="test.jpg")

@app.get('/takephoto')
def takephoto():
    file=host+"-"+datetime.now().strftime("%Y%m%d_%H_%M_%S")+".jpg"
    takePhoto(folder+file)
    html='<html><body><img src="http://'+host+"/download/"+file+'" style="max-width: 100%;max-height: 100%;" alt=""></body></html>'
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
    os.system("sudo /home/pi/autoupdate &")
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
    global status
    status="started"
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
    if os.path.exists(folder+file):
        os.remove(folder+file)
        return ("deleted "+file)
    else:
        return ("can't find "+file)

@app.get('/deleteall')
def deleteall():
    os.system("rm /home/pi/photos/*")

@app.get('/sethostname/<host>')
def sethostname(host):
    os.system("sudo raspi-config nonint do_hostname "+host)
    return "Naujas pavadinimas: "+host

@app.get('/count')
def count():
    return str(len(listFiles()))

@app.get('/v')
def ver():
    return version

@app.get('/config')
def conf():
    global config
    return str(config)

@app.get('/getshootingstatus')
def getshootingstatus():
    return status

@app.get('/setrotate/<rotate>')
def setrotate(rotate):
    global config
    if rotate=='true':
        config['rotate']=True
    else:
         config['rotate']=False
    saveconfig()
    return str(config)

def listFiles():
    return  glob.glob(folder+'*.jpg')

server = CherryPyWSGIServer(
    ('0.0.0.0', 80),app,
    server_name='pi-cam',
    numthreads=10)

server.start()