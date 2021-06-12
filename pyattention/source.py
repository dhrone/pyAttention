# Source.py

import asyncio
import concurrent.futures
import logging
import time
import traceback

from pyattention.exception import ConnectionException
from pyattention.util import status, threadloop

DEFAULT_FREQUENCY = (
    60  # If not specified all source polling will occur once per minute
)


class source:
    def __init__(
        self,
        connectionTimeout=1,
        pollTimeout=5,
        cmdQueueTimeout=0.1,
        persistent=True,
        loop=None,
    ):

        self._connectionTimeout = connectionTimeout
        self._pollTimeout = pollTimeout
        self._cmdQueueTimeout = cmdQueueTimeout
        self._persistent = persistent

        # Initialize logging system
        self._logger = logging.getLogger("pyattention")

        if loop is None:
            self.tloop = threadloop()
            # Mark that a new tloop was created (for use in shutdown)
            self._tloopLocal = True
        elif isinstance(loop, threadloop):
            self.tloop = loop
            self._tloopLocal = False
        else:
            raise TypeError("Loop must be an instance of threadloop")
        self._loop = self.tloop.loop

        # Internal variables
        self._shutdownFlag = False
        self._connected = False  # Current status of connection
        self._activePolls = []  # Hold tasks for active polls

        # Create queues and lock.  Must be created as a callback from new thread.
        async def initAsyncVariables():
            self._dataQueue = (
                asyncio.Queue()
            )  # Queue to pass data back to requesting object
            self._cmdQueue = (
                asyncio.Queue()
            )  # Queue to submit commands to be sent to server
            self._connectingLock = (
                asyncio.Lock()
            )  # Lock to prevent asynchronous connection attempts

        future = asyncio.run_coroutine_threadsafe(
            initAsyncVariables(), self._loop
        )
        future.result(1)

        # Start command loop for this source
        self._cmdLoopTask = self._loop.create_task(self._commandLoop())

    async def _connect(self):
        """
        Connect to the data source (if needed)

        Must test self._shutdownFlag to see if the object is still active before
        opening a new connection

        Must test self._connected to see if the object is already connected to source

        Must set self._connected if connection attempt is successful.

        :returns: A boolean indicating whether the connection attempt succeeded or not
        :rtype: bool
        """
        if self._shutdownFlag:
            return False
        if not self._connected:
            self._connected = True
        return self._connected

    async def _close(self):
        """
        Close any active connections and perform any needed cleanup

        Must set self._connected to false
        """
        self._connected = False
        pass

    async def _shutdown(self):
        """Safely shutdown the source"""
        # If already shutdown, there is no action to take so return
        if self._shutdownFlag is True:
            return
        self._shutdownFlag = True
        self._logger.debug("Shutting down source")

        # Close any open streams
        await self._close()

        # Cancel the command loop
        self._cmdLoopTask.cancel()

        # Cancel any active polls
        if hasattr(self, "_activePolls"):
            for p in self._activePolls:
                p.cancel()

    async def _commandLoop(self):
        while not self._shutdownFlag:
            try:
                pollCoro = await asyncio.wait_for(
                    self._cmdQueue.get(), timeout=self._cmdQueueTimeout
                )
                self._cmdQueue.task_done()
                await pollCoro
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                return
            except ConnectionException as ex:
                self._logger.error(f"Connection exception: {ex}")
                await self._shutdown()
            except Exception as ex:
                self._logger.error(
                    f"Unexpected error during command processing: {ex}"
                )
                self._logger.error(traceback.format_exc())
                await self._shutdown()

    async def _poll(
        self, handler=None, frequency=DEFAULT_FREQUENCY, repeat=None, wait=None
    ):
        assert handler is not None, "Must provide a handler to poll with"
        assert type(frequency) in (
            float,
            int,
        ), "Frequency must be a valid number"
        assert frequency >= 0.1, "Minimum frequency is 1/10 of a sec"
        """ Add poll to connection """
        # If using default timeout, added a 10% buffer
        # This prevents premature exit if the handler is also using
        # the default timeout
        wait = wait or self._pollTimeout

        async def _pollExecution():
            """A coroutine to process one interaction with the source"""
            connected = await self._connect()

            if connected:
                # Try to run handler.  If it fails send exception on but make
                # sure to close the connection first if not in persistent mode
                try:
                    await asyncio.wait_for(handler(), timeout=wait)
                except:
                    raise
                finally:
                    if not self._persistent:
                        self._close()

        async def _pollItem():
            """A coroutine to issue execution requests for a poll into the command queue"""
            number = repeat

            while not self._shutdownFlag:
                await self._cmdQueue.put(_pollExecution())
                if number is not None:
                    number = number - 1
                    if number <= 0:
                        break
                if frequency is not None:
                    await asyncio.sleep(frequency)

        # Add new poll to loop
        self._activePolls.append(asyncio.create_task(_pollItem()))

    async def put(self, data, key=None):
        """
        Put timestamped data into dataQueue.

        :param data: value to place into key
        :param key: key for the value

        ..note:
            If key is none and the data is a dictionary it is placed unchanged
            into the queue.
            If key is none and the data is not a dictionary, it is placed into
            a dict using the key value 'data'
            e.g. {'data': data}
            If key contains a value, the data is placed into a dict
            e.g. {key}: data
        """

        # Place data in dictionary with `key` if provided
        if key is not None:
            data = {key: data}

        # Place data within dictionary if needed
        if type(data) is not dict:
            data = {"data": data}

        # Add timestamp
        data["__updated__"] = time.time()
        await self._dataQueue.put(data)

    # public methods.  Can be called from other threads
    def checkAlive(self):
        if self._shutdownFlag:
            raise RuntimeError("Source has already shutdown")

    def shutdown(self):
        self.checkAlive()
        fut = asyncio.run_coroutine_threadsafe(self._shutdown(), self._loop)
        fut.result(5)

    async def _get(self):
        result = await self._dataQueue.get()
        if result:
            self._dataQueue.task_done()
        return result

    async def _clear(self):
        while True:
            try:
                self._dataQueue.get_nowait()
                self._dataQueue.task_done()
            except asyncio.QueueEmpty:
                break

    def get(self, wait=1):
        self.checkAlive()
        future = asyncio.run_coroutine_threadsafe(self._get(), self._loop)
        try:
            result = future.result(wait)
        except concurrent.futures.TimeoutError:
            future.cancel()
        except Exception as ex:
            self._logger.warning(f"Get failed: {ex!r}")
        else:
            return result

    def clear(self):
        self.checkAlive()
        asyncio.run_coroutine_threadsafe(self._clear(), self._loop)

    def poll(
        self, handler=None, frequency=DEFAULT_FREQUENCY, repeat=None, wait=None
    ):
        """
        Register a new polling connection

        `poll` registers the provided handler as a function to interact with
        the source on a synchronous basis.  Once registered it will be called every
        `frequency` seconds.  If zero, it will be called continuously.

        Any message received from the handler will be placed in the sources data
        queue.

        If an error occurs during polling, a WARNING level log event will be
        generated but no attempt will be made to recover from the error.

        :param handler: The function that will interact with the source.  See
            `handler` documentation for more details.
        :type handler: `pyattention.handler`
        :param frequency: How often handler will be called in seconds.  Setting
            this to zero will cause the handler to be called continuously.  This
            should be avoided unless the handler spends some amount of time
            itself waiting for a response from the source.
        :type frequency: float
        :param repeat: The number of times the polling should be conducted.  If
        None, the polling will continue until the source is shut down.
        :type repeat: int
        :param wait: Amount of time poll request is allowed to take in seconds.  If
            a source doesn't respond in time, the poll will fail with a request timed out message.
            Set this to None if you are ok blocking until the poll completes.  This is only safe,
            if your handler already limits how long it will wait for a response from the source.
        :type wait: float
        """
        wait = wait or self._pollTimeout
        self.checkAlive()
        asyncio.run_coroutine_threadsafe(
            self._poll(
                handler=handler, frequency=frequency, repeat=repeat, wait=wait
            ),
            self._loop,
        )


class tcp(source):
    def __init__(
        self,
        host="127.0.0.1",
        port=None,
        connectionTimeout=1,
        pollTimeout=5,
        persistent=True,
        helloHandler=None,
        loop=None,
    ):
        self._host = host
        self._port = port
        self._helloHandler = helloHandler

        super().__init__(
            connectionTimeout=connectionTimeout,
            pollTimeout=pollTimeout,
            persistent=persistent,
            loop=loop,
        )

        # Internal variables
        self._reader = None
        self._writer = None
        self._helloData = None  # Dataset produced by `hello` handler (if any)

    async def _connect(self):
        """Connect to the data source (if needed).

        :returns: Connection status as a boolean
        """
        if self._shutdownFlag:
            return False

        if not self._connected:
            async with self._connectingLock:
                try:
                    self._reader, self._writer = await asyncio.wait_for(
                        asyncio.open_connection(self._host, self._port),
                        timeout=self._connectionTimeout,
                    )

                    if self._helloHandler:
                        self._helloData = await asyncio.wait_for(
                            self._helloHandler(),
                            timeout=self._connectionTimeout,
                        )

                        if self._helloData.status == status.SUCCESS:
                            self._connected = True
                        else:
                            self._logger.error(
                                f"Received invalid response on initial connection to {self._host}:{self._port}.  Response was {self._helloData}"
                            )
                    else:
                        self._connected = True

                except ConnectionRefusedError as ex:
                    raise ConnectionException(
                        f"Connection refused to {self._host}:{self._port}: {ex}"
                    )
                except TimeoutError as ex:
                    raise ConnectionException(
                        f"Timeout during connection attempt to  {self._host}:{self._port}: {ex}"
                    )
                except Exception as ex:
                    raise ConnectionException(
                        f"Unexpected error connecting to {self._host}:{self._port}: {ex}"
                    )

        return self._connected

    async def _close(self):
        if self._writer is not None:
            self._connected = False
            self._reader = None
            await self._writer.drain()
            self._writer.close()
            try:
                await self._writer.wait_closed()
            except AttributeError:
                pass
            self._writer = None

    # methods available for handlers to call
    async def write(self, data):
        self._writer.write(data.encode())
        await self._writer.drain()

    async def readline(self, wait=None):
        line = await asyncio.wait_for(self._reader.readline(), timeout=wait)
        return line.decode()

    async def readuntil(self, separator="\n", wait=None):
        line = await asyncio.wait_for(
            self._reader.readuntil(separator=separator.encode()), timeout=wait
        )
        return line.decode()


class socketIO(source):
    """
    Source to interact with Javascript SocketIO servers

    Supports Javascript SocketIO v1 and v2
    """

    def __init__(
        self,
        url="http://localhost:80",
        connectionTimeout=1,
        pollTimeout=5,
        persistent=True,
        loop=None,
    ):

        # Local import
        from socketio import AsyncClient, exceptions

        self._sioExceptions = exceptions
        self._url = url

        # Register message handlers
        self._sio = AsyncClient()
        self._default_register()
        super().__init__(
            connectionTimeout=connectionTimeout,
            pollTimeout=pollTimeout,
            persistent=persistent,
            loop=loop,
        )

    def _default_register(self):
        self._sio.on("connect", self._hConnect)
        self._sio.on("disconnect", self._hDisconnect)
        self._sio.on("connect_error", self._hConnectError)

    # Default Handlers
    async def _hConnect(self):
        self._connected = True

    async def _hConnectError(self, *args):
        self._connected = False

    async def _hDisconnect(self):
        self._connected = False

    # Connection managers
    async def _connect(self):
        """Connect to the data source (if needed).

        :returns: connection status as a boolean
        """
        if self._shutdownFlag:
            return False

        async with self._connectingLock:
            if not self._connected:
                try:
                    await self._sio.connect(self._url)
                    self._connected = True
                except self._sioExceptions.ConnectionError as ex:
                    self._logger.error(traceback.format_exc())
                    raise ConnectionException(
                        f"Connection refused to {self._url}: {ex}"
                    )
                except TimeoutError as ex:
                    raise ConnectionException(
                        f"Timed out during connection attempt to {self._url}: {ex}"
                    )
                except Exception as ex:
                    raise ConnectionException(
                        f"Unexpected error connecting to {self._url}: {ex}"
                    )

        return self._connected

    async def _close(self):
        if self._connected is not False:
            self._connected = False
            await self._sio.disconnect()

    async def _emit(self, event, data=None, namespace=None, callback=None):
        if await self._connect():
            await self._sio.emit(
                event, data=data, namespace=namespace, callback=callback
            )

    # User callable methods
    def add(
        self,
        event,
        data=None,
        namespace=None,
        callback=None,
        frequency=DEFAULT_FREQUENCY,
        repeat=None,
        wait=None,
    ):
        h = lambda: self._emit(
            event, data=data, namespace=namespace, callback=callback
        )
        self.poll(handler=h, frequency=frequency, repeat=repeat, wait=wait)

    def emit(self, event, data=None, namespace=None, callback=None):
        self.checkAlive()
        asyncio.run_coroutine_threadsafe(
            self._emit(
                event, data=data, namespace=namespace, callback=callback
            ),
            self._loop,
        )

    def subscribe(self, channel, handler=None, namespace=None):
        self.checkAlive()
        self._sio.on(channel, handler=handler, namespace=namespace)


class database(source):
    """
    Source to interace with SQL databases

    :param url: A url suitable to be used in a sqlalchemy create_engine_async call
    :type dbapi: str
    :param loop:  A threadloop to run the source within.  A local instance of a
        threadloop will be created if one is not supplied.
    :type loop: `pyattention.util.threadloop`



    ..note:
        You must use an async db-api client with this class

    ..example:
        `src = database('sqlite+aiosqlite:///test.db')`
    """

    def __init__(
        self,
        uri,
        query=None,
        name=None,
        frequency=DEFAULT_FREQUENCY,
        repeat=None,
        wait=None,
        loop=None,
    ):

        # Local import
        import sqlalchemy as db
        from sqlalchemy.ext.asyncio import create_async_engine

        self._db = db  # Make module accessible to other methods
        try:
            self._engine = create_async_engine(uri)
        except Exception as ex:
            raise RuntimeError(
                f"Unable to initalize database using uri: {uri}: {ex}"
            )

        super().__init__(loop=loop)

        if query is not None:
            self.add(
                query, name=name, frequency=frequency, repeat=repeat, wait=wait
            )

    def add(
        self,
        query,
        name=None,
        frequency=DEFAULT_FREQUENCY,
        repeat=None,
        wait=None,
    ):
        """
        Add query retrieve data from database

        Adds a query to poll the database with.  Can be run continuously or be
        limited to a fixed number of repetitions.

        :param query:  The SQL query used to search the database
        :type query: str
        :param name: If provided, the returned data will be placed in a dict
            with `name` as the key value.
        :type name: str
        :param frequency: How often in seconds the query will be executed
        :type frequency: float
        :param repeat: How many times the query will be repeated.  If not
            provided the query will be repeated continuously.
        :param wait: Amount of time request is allowed to take in seconds.  If
            a source doesn't respond in time, the retrieve will fail with a
            request timed out message.
            Set this to None if you are ok blocking until the poll completes.
        :type wait: float
        """
        h = lambda: self._handler(query, name)
        self.poll(handler=h, frequency=frequency, repeat=repeat, wait=wait)

    async def _handler(self, query, name=None):
        async with self._engine.connect() as conn:
            rp = await conn.execute(self._db.text(query))
            results = rp.fetchall()

        count = len(results)
        if count > 0:
            if count == 1:
                retv = self._dictFromRow(results[0])
            else:
                retv = []
                for row in results:
                    retv.append(self._dictFromRow(row))
            await self.put(retv, name)

    def _dictFromRow(self, row):
        retv = {}
        for k, v in row._mapping.items():
            retv[k] = v
        return retv


class system(source):
    def __init__(
        self,
        name=None,
        frequency=DEFAULT_FREQUENCY,
        repeat=None,
        wait=None,
        loop=None,
    ):
        super().__init__(loop=loop)

        # Local import
        import netifaces
        import psutil

        self._netifaces = netifaces
        self._psutil = psutil

        # Set up polling for system variables
        h = lambda: self._handler(name)
        self.poll(handler=h, frequency=frequency, repeat=repeat, wait=wait)

    async def _getTemp(self):
        """Get current system temperatures"""
        if not hasattr(self._psutil, "sensors_temperatures"):
            return
        temps = self._psutil.sensors_temperatures()
        retv = {}
        for source, temp in temps.items():
            # Only capture the first temperature entry for multi value sources
            retv[source] = temp[0][1]
        return retv

    async def _getDiskStats(self):
        """
        Get current disk utilization statistics.

        :returns: dictionary of disk statistics of the reporting system
        """
        du = self._psutil.disk_usage("/")
        return {"total": du[0], "used": du[1], "free": du[2], "percent": du[3]}

    async def _getIPAddress(self):
        """
        Get IP address for interface used in default route.

        :returns: Primary IP address for the system
        """
        return self._netifaces.gateways()["default"][self._netifaces.AF_INET][
            0
        ]

    async def _handler(self, name=None):
        retv = {}
        sources = {
            "temp": self._getTemp,
            "disk": self._getDiskStats,
            "ipaddr": self._getIPAddress,
        }

        for k, m in sources.items():
            try:
                val = await m()
                if val is not None:
                    retv[k] = val
            except:
                pass
        await self.put(retv, name)


class rss(source):
    """
    Source to interact with rss servers
    """

    def __init__(
        self,
        url=None,
        name=None,
        frequency=DEFAULT_FREQUENCY,
        repeat=None,
        wait=None,
        loop=None,
    ):
        super().__init__(loop=loop)
        self._url = url

        # Local Import
        import bs4
        import httpx

        self._httpx = httpx
        self._bs4 = bs4

        if url is not None:
            self.add(
                url, name=name, frequency=frequency, repeat=repeat, wait=wait
            )

    async def _handler(self, url, name=None):
        async with self._httpx.AsyncClient() as client:
            r = await client.get(url)

        soup = self._bs4.BeautifulSoup(r.content, "xml")
        items = soup.findAll("item")
        retv = []
        for item in items:
            reti = {}
            for e in item:
                if isinstance(e, self._bs4.element.Tag):
                    reti[e.name] = e.text
            retv.append(reti)
        await self.put(retv, name)

    def add(
        self,
        url,
        name=None,
        frequency=DEFAULT_FREQUENCY,
        repeat=None,
        wait=None,
    ):
        h = lambda: self._handler(url, name=name)
        self.poll(handler=h, frequency=frequency, repeat=repeat, wait=wait)
