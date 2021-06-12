import asyncio

from pyattention import parser
from pyattention.exception import MessageException, MessageTimeout
from pyattention.source import socketIO, tcp
from pyattention.util import message, status


class mpd(tcp):
    def __init__(
        self,
        host="127.0.0.1",
        port=6600,
        commandTimeout=1,
        idleTimeout=0.25,
        loop=None,
    ):
        super().__init__(
            host=host, port=port, helloHandler=self._mpdMessage, loop=loop
        )

        self._commandTimeout = commandTimeout
        self._idleTimeout = idleTimeout

        def collect(cmd, parser):
            return lambda: self._collectData(cmd, parser)

        # Get initial values
        self.poll(handler=collect("currentsong", parser.kvp), repeat=1)
        self.poll(handler=collect("status", parser.kvp), repeat=1)
        self.poll(
            handler=collect(
                "playlistinfo", lambda msg: parser.listOfKvp(msg, ":", "file")
            ),
            repeat=1,
        )

        # Listen for updates
        self.poll(handler=self._mpdIdle)

    def _command(self, cmd):
        h = lambda: self._mpdCommand(cmd)
        self.poll(handler=h, repeat=1)

    def play(self, number=None):
        cmd = f"play {number}\n" if number is not None else "play\n"

        self._command(cmd)

    def pause(self):
        self._command("pause\n")

    def stop(self):
        self._command("stop\n")

    def volume(self, val=None):
        if val is None:
            return
        if type(val) != int:
            raise TypeError("Volume value must be an integer")

        self._command(f"volume {val}\n")

    async def _mpdMessage(self, wait=0.25):
        """
        Read an MPD message until receiving either an OK or and ACK

        MPD messages are formated as a series of lines that end when a line
        is received that starts with either the string 'OK' or 'ACK'.  If 'ACK'
        there was some sort of error which is identified through the text that
        follows 'ACK'.

        Returns a message filled with the lines that were received not including the
        ending message

        :param wait: The amount of time that an interaction with the source should
            take before a TimeoutError is declared
        :type wait: float
        :returns: message received from source

        ..note::
            Handlers are required to take the actions necessary to process a particular
            protocol state.  Often these will be used to accept responses from an event
            and take the appropriate actions required for the event.

            Generically they
            * Interact with source
                - valid source methods include write, readline, and readuntil
            * Return a message instance which
                - Includes a status property (success, failure)
                - Includes a data instance if successful and relevant.  Data instance is one of
                    1. Scalar
                    2. List
                    3. Dictionary
        """
        source = self
        good = "OK"
        bad = "ACK"
        msgSize = 0
        growing = 0
        lines = []
        msg = message()
        msg.data = lines
        while True:
            try:
                line = await source.readuntil(wait=wait)
            except asyncio.TimeoutError:
                # If timeout occurs in the middle of receiving data
                # Allow for the receipt to finish
                if msgSize > 0:
                    if growing != msgSize:
                        growing = msgSize
                        continue
                msg.status = status.TIMEOUT
                raise MessageTimeout("No response from source", msg)

            msgSize += len(line)
            msg.status = (
                status.SUCCESS
                if line[0 : len(good)] == good
                else status.FAILED
                if line[0 : len(bad)] == bad
                else status.OVERFLOW
                if msgSize > message.MAXSIZE
                else None
            )

            if msg.status is not None:
                if msg.status in [status.SUCCESS, status.FAILED]:
                    msg.footer = line
                else:
                    lines.append(line)
                if status.SUCCESS:
                    return msg
                raise MessageException("Source returned error message", msg)

            lines.append(line)

    async def _mpdHello(self):
        """
        Receive MPD hello message

        This is a more opinonated version of mpdMessage.  Currently it is not being
        used by the mpd source module

        :returns: The response from the Hello message
        """
        source = self
        response = await self._mpdMessage(wait=source._connectionTimeout)
        try:
            ok, mpd, version = response.footer.split(" ")
            if ok != "OK" or mpd != "MPD":
                response.status = status.FAILED
                raise MessageException(
                    "Received unexpected header message", response
                )
        except ValueError:
            response.status = status.FAILED
            raise MessageException(
                "Received unexpected header message", response
            )
        return response

    async def _mpdCommand(self, command, parsefunc=None, wait=None):
        source = self
        wait = wait or self._commandTimeout
        if command is not None:
            await source.write(command)
        response = await self._mpdMessage(wait)
        if response.status == status.SUCCESS:
            if parsefunc is not None:
                response.data = parsefunc(response.data)
        return response

    async def _mpdIdle(self):
        """
        Handle IDLE message

        IDLE messages are MPDs way of informing a listening system that the state
        of the MPD daemon has changed.  This handler places the MPD system into idle mode and then if it receives in 'changed' notifications, queries
        the appropriate subsystems to gather updated state data from the daemon.

        :returns: received message
        """
        msg = message()
        # Issue idle command
        try:
            response = await self._mpdCommand(
                "idle\n", lambda x: parser.listOfKvp(x, ":", "changed")
            )
        except MessageTimeout:
            try:
                await self._mpdCommand("noidle\n")
            except MessageException as ex:
                raise MessageException(
                    f"Got unexpected error while attempting to leave idle mode: {ex.message}"
                )

            # Report Success but with no data as this is a normal exit for idle
            msg.status = status.SUCCESS
            return msg

        try:
            changed = [i["changed"] for i in response.data]
        except (ValueError, AttributeError):
            raise MessageException("Unable to parse idle message", response)

        # Based upon what subsystems have changed determine which command to issue
        # to get current system state
        commands = set()
        for item in changed:
            action = {
                "player": ("currentsong", "status"),
                "mixer": ("status",),
                "options": ("status",),
                "playlist": ("playlistinfo",),
            }.get(item, [])
            for a in action:
                commands.add(a)

        # Issue commands and collect results
        msg.data = {}
        for c in commands:
            parsefunc = {
                "currentsong": parser.kvp,
                "status": parser.kvp,
                "playlistinfo": lambda msg: parser.listOfKvp(msg, ":", "file"),
            }.get(c)
            await self._collectData(c, parsefunc)

    async def _collectData(self, cmd, parser):
        response = await self._mpdCommand(command=cmd + "\n", parsefunc=parser)
        if response.data is not None:
            await self.put(response.data, cmd)
            return response
        return None


class volumio(socketIO):
    def __init__(self, url="http://127.0.0.1:3000", loop=None):
        super().__init__(url=url, loop=loop)

        # Subscribe to useful channels
        self.subscribe("pushState", self._pushState)
        self.subscribe("pushQueue", self._pushQueue)
        self.subscribe("pushMultiRoomDevices", self._pushMultiRoomDevices)

        # Make sure that Volumio sends a pushState update
        # at least 3 times per minute
        self.add("getState", frequency=20)

        # Request pushQueue data on startup
        self.emit("getQueue")

    # Volumio Handlers
    async def _pushState(self, data):
        await self.put(data, "pushState")

    async def _pushQueue(self, data):
        await self.put(data, "pushQueue")

    async def _pushMultiRoomDevices(self, data):
        await self.put(data, "pushMultiRoomDevices")

    # Volumio Commands
    def play(self):
        self.emit("play")

    def pause(self):
        self.emit("pause")

    def stop(self):
        self.emit("stop")

    def volume(self, val=None):
        if val is None:
            return
        if type(val) != int:
            raise TypeError("Volume value must be an integer")

        self.emit("volume", data=val)
