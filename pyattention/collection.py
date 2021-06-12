import asyncio

from pyattention.source import source


class collection(source):
    def __init__(self, loop=None):
        self._srcTaskList = {}
        self._last = {}

        super().__init__(loop=loop)

    async def _monitor(self, name, source):
        while not self._shutdownFlag:
            try:
                data = await source._get()
                if data is not None:
                    await self.put(data, name)
                    self._last[name] = {**self._last[name], **data}
            except asyncio.CancelledError:
                break

        # Shutdown monitored source
        await source._shutdown()

    async def _shutdown(self):
        if self._shutdownFlag is True:
            return
        for n, tsk in self._srcTaskList.items():
            tsk.cancel()
        await super()._shutdown()

    async def _register(self, name, source):
        """
        Register a new source with the collection

        :param name: The name of the source
        :param source: The source to register
        """
        self._last[name] = {}

        self._srcTaskList[name] = asyncio.create_task(
            self._monitor(name, source)
        )

    def __getitem__(self, key):
        return self._last[key]

    def __len__(self):
        return len(self._last)

    def __repr__(self):
        return repr(self._last)

    def register(self, name, source):
        self.checkAlive()
        asyncio.run_coroutine_threadsafe(
            self._register(name, source), self._loop
        )
