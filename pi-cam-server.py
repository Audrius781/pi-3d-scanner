from bottle import run, static_file, route, Bottle
from datetime import datetime
import os, socket, threading, glob, json, sys
from cheroot.wsgi import Server as CherryPyWSGIServer

version="1.4.7"

host=socket.gethostname()
status="stopped"

# Folderiai
if sys.platform=="win32": #windows - tik testavimui
    folder='C:\\Users\\remote\\Desktop\\test\\'
    homefolder='C:\\Users\\remote\\Desktop\\'
else:  #Raspberry pi
    folder='/home/pi/photos/'
    homefolder='/home/pi/'

# Bandomuoji nuotrauka patikrinti ar veikia kamera
os.system("rm "+homefolder+"test.jpg")
os.system("raspistill -t 1000 -o "+homefolder+"test.jpg &")
cameraStatus="Error"

# Loginti kas vyksta
def log(lg):
    print (lg)

# Gauti failu sarasa
def listFiles():
    types = ('*.jpg', '*.h264','*.mp4') # the tuple of file types
    files_grabbed = []
    for filetype in types:
         files_grabbed.extend(glob.glob(folder+filetype))
    return  files_grabbed

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

if not ("parameters" in config.keys()):
    config['parameters']="-t 1000"
if not ("videoparameters" in config.keys()):
    config['videoparameters']="-t 600000"
saveconfig()
    

# Signalas sustabdyti fotografavima
event=threading.Event()

# Pagrindines fotografavimo funkcijos

# Padaryti viena nuotrauka ir irasyti i SD kortele
def takePhoto(path):
    os.system("raspistill "+config["parameters"]+" -o "+path)

# Daryti daug nuotrauku iki kol negautas signalas sustabdyti
def takeManyPhotos():
    log ("takeManyPhotos starting")
    while not event.is_set():
        file=host+"-"+datetime.now().strftime("%Y%m%d_%H_%M_%S")+".jpg"
        log ("takePhoto "+file)
        takePhoto(folder+file)
    global status
    log ("takeManyPhotos status=stopped")
    status="stopped"
x = threading.Thread(target=takeManyPhotos, args=())
app=Bottle()

# Padaryti viena video i SD kortele
def takeVideo(path):
    os.system("raspivid "+config["videoparameters"]+" -o "+path)


# WEB SERVER FUNKCIJOS -----------------------------------------------------------

# Fotografavimas

@app.get('/preview')
def preview():
    os.system("rm "+homefolder+"preview.jpg")
    takePhoto(homefolder+"preview.jpg")
    return static_file("preview.jpg", root=homefolder, download="preview.jpg")

@app.get('/takephoto')
def takephoto():
    file=host+"-"+datetime.now().strftime("%Y%m%d_%H_%M_%S")+".jpg"
    takePhoto(folder+file)
    html='<html><body><img src="http://'+host+"/download/"+file+'" style="max-width: 100%;max-height: 100%;" alt=""></body></html>'
    return html

@app.get('/takevideo')
def takevideo():
    global status
    rt="camera_busy"
    if status=="stopped" or status=="vercia i MP4":
        file=host+"-"+datetime.now().strftime("%Y%m%d_%H_%M_%S")+".mp4"
        status="filmuoja"
        log ("/takevideo status=started_video")
        log ("/takevideo takeVideo video.h264")
        takeVideo(homefolder+"video.h264")
        log ("/takevideo status=stopped")
        status="vercia i MP4"
        log ("/takevideo MP4Box")
        os.system("MP4Box -add "+homefolder+"video.h264 "+homefolder+"video.mp4")
        status="stopped"
        os.system("mv "+homefolder+"video.mp4 "+folder+file)
        rt="video_taken"
    log("/takevideo "+rt)
    return rt

@app.get('/startshooting')
def startshooting():
    global event, status
    if status=="stopped" or status=="vercia i MP4":
        event.clear()
        global x
        if not x.is_alive():
            try:
                x.start()
                log ("reusing thread")
            except RuntimeError: #occurs if thread is dead
                x = threading.Thread(target=takeManyPhotos, args=()) #create new instance if thread is dead
                x.start() #start thread
                log ("new thread")
        status="started"
        log ("/startshooting status=started")
    return "started"

# Sustabdyti fotografavima arba video
@app.get('/stopshooting')
def stopshooting():
    log ("/stopshooting")
    os.system("sudo pkill raspivid") #video
    event.set() #fotografavima
    return "stopped"

# Failu siuntimas ir trynimas

@app.get('/getone')
def getone():
    try:
        file=os.path.basename(listFiles()[0])
    except:
        file="none"
    return file

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

# Busena

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

@app.get('/status')
def ping():
    global cameraStatus
    if os.path.exists(homefolder+"test.jpg"):
        cameraStatus="Ready"
    return cameraStatus

@app.get('/getshootingstatus')
def getshootingstatus():
    return status

# Rasperry pi kontrole ir konfiguracija

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
    #Instaliuoti MP4Box - jei nera
    if not(os.path.exists('/usr/bin/MP4Box')):
        log ("/update installing gpac")
        global version
        oldversion=version
        version="updating..."
        os.system("sudo apt-get update")
        os.system("sudo apt-get -y install gpac")
        version=oldversion
    
    #Paleisti autoupdate
    log ("/update autoupdate")
    os.system("sudo /home/pi/autoupdate &")
    return "updated"

@app.get('/sethostname/<host>')
def sethostname(host):
    os.system("sudo raspi-config nonint do_hostname "+host)
    return "Naujas pavadinimas: "+host

@app.get('/setrotate/<rotate>')
def setrotate(rotate):
    global config
    if rotate=='true':
        config['rotate']=True
    else:
         config['rotate']=False
    saveconfig()
    return str(config)

@app.get('/setparameters/<parameters>')
def setparameters(parameters):
    global config
    config['parameters']=parameters
    saveconfig()
    return str(config)

@app.get('/setvideoparameters/<parameters>')
def setvideoparameters(parameters):
    global config
    config['videoparameters']=parameters
    saveconfig()
    return str(config)


# Serverio paleidimas -----------

server = CherryPyWSGIServer(
    ('0.0.0.0', 80),app,
    server_name='pi-cam',
    numthreads=10)

server.start()