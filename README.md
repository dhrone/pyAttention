# pyAttention
A library to monitor information sources

![build](https://github.com/dhrone/pyAttention/actions/workflows/test.yml/badge.svg) [![codecov](https://codecov.io/gh/dhrone/pyAttention/branch/master/graph/badge.svg?token=ZCAT8XRG4W)](https://codecov.io/gh/dhrone/pyAttention)

## Key Features

* Retrieves data from TCP servers, socketIO services, RSS feeds, and SQL databases
* Retrieves basic system data from linux-based computers (disk space, IP address, temperatures)
* Provides a queue interface for retrieving received information
* Supports polling and asynchronous monitoring
* Sources can be run individually or monitored together as a collection
* Sources run in their own thread or can share a thread across a collection

## Installation

```shell
# Installation from pypi
pip pyAttention

# or
# Installation from github
$ git clone https://github.com/dhrone/pyAttention

# Install optional dependencies
# Databases
$ pip install sqlalchemy
$ pip install aiosqlite  # For sqlite database support
$ pip install asyncpg    # For PostgreSQL
$ pip install aiomysql   # For mySQL

# RSS Feeds
$ pip install httpx lxml beautifulsoup4

# socketIO services
$ pip install python-socketio[client]==4.6.* aiohttp

# Local system data
$ pip install psutil netifaces
```

## Quickstart

To retrieve data from a RSS feed

```python
from pyAttention.source import rss

# EXAMPLE: Pull 3 day forecast of Manchester, UK from the BBC News RSS feed
url = 'https://weather-broker-cdn.api.bbci.co.uk/en/forecast/rss/3day/2643123'
from pyAttention.source import rss
src = rss(url, frequency=21600)  # Query feed every 6 hours
weather = src.get()
```

To retrieve data from a socketIO service

```python
# EXAMPLE: monitor Volumio metadata from its socketIO API (see https://volumio.org)  
from pyAttention.source import socketIO
url = 'http://localhost:3000'
src = socketIO(url)

async def callback(data):
  await src.put(data)

src.subscribe('pushState', callback)
src.emit('getState')  # Command needed to get Volumio to send a pushState message
state = src.get()
```

To retrieve data from a database

```python
# EXAMPLE: pull data from a locally stored sqlite database
# Create test db
import sqlite3
con = sqlite3.connect('songs.db')
cur = con.cursor()
cur.execute('''CREATE TABLE songs (artist text, title text, album text)''')
cur.execute('''INSERT INTO songs VALUES ('Billie Eilish', 'bad guy', 'When We All Fall Asleep, Where Do We Go?')''')
cur.close()

from pyAttention.source import database
uri = 'sqlite+aiosqlite:///./songs.db'
src = database(uri, 'select * from songs')
songs = src.get()
```
