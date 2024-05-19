import socketio
from aiohttp import web

sio = socketio.AsyncServer()
app = web.Application()
sio.attach(app)

# async def index(request):
#    with open('index.html') as f:
#        return web.Response(text=f.read(), content_type='text/html')


## If we wanted to create a new websocket endpoint,
## use this decorator, passing in the name of the
## event we wish to listen out for
@sio.on("getState")
async def pushState(*args):
    print(args)

    state = {
        "status": "stop",
        "position": 0,
        "title": "Oh! You Pretty Things",
        "artist": "Lisa Hannigan",
        "album": "Oh! You Pretty Things",
        "trackType": "spotify",
        "seek": 0,
        "duration": 235,
        "samplerate": "320Kbps",
        "bitdepth": "16 bit",
        "random": None,
        "repeat": None,
        "repeatSingle": False,
        "consume": False,
        "volume": 51,
        "disableVolumeControl": False,
        "mute": False,
        "stream": "spotify",
        "updatedb": False,
        "volatile": False,
        "service": "spop",
    }

    await sio.emit("pushState", {"pushState": state})


## We bind our aiohttp endpoint to our app
## router
# app.router.add_get('/', index)

## We kick off our server
if __name__ == "__main__":
    web.run_app(app, port=20202)
