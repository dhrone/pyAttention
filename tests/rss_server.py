import sys

from aiohttp import web

app = web.Application()

rssText = """<?xml version="1.0" encoding="UTF-8"?>
<rss xmlns:atom="http://www.w3.org/2005/Atom" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:georss="http://www.georss.org/georss" version="2.0">
  <channel>
    <title>BBC Weather - Observations for  Manchester, GB</title>
    <link>https://www.bbc.co.uk/weather/2643123</link>
    <description>Latest observations for Manchester from BBC Weather, including weather, temperature and wind information</description>
    <language>en</language>
    <copyright>Copyright: (C) British Broadcasting Corporation, see http://www.bbc.co.uk/terms/additional_rss.shtml for more details</copyright>
    <pubDate>Sat, 03 Apr 2021 18:00:00 GMT</pubDate>
    <dc:date>2021-04-03T18:00:00Z</dc:date>
    <dc:language>en</dc:language>
    <dc:rights>Copyright: (C) British Broadcasting Corporation, see http://www.bbc.co.uk/terms/additional_rss.shtml for more details</dc:rights>
    <atom:link href="https://weather-service-thunder-broker.api.bbci.co.uk/en/observation/rss/2643123" type="application/rss+xml" rel="self" />
    <item>
      <title>Saturday - 19:00 BST: Not available, 10Â°C (50Â°F)</title>
      <link>https://www.bbc.co.uk/weather/2643123</link>
      <description>Temperature: 10Â°C (50Â°F), Wind Direction: North Easterly, Wind Speed: 6mph, Humidity: 53%, Pressure: 1032mb, Steady, Visibility: --</description>
      <pubDate>Sat, 03 Apr 2021 18:00:00 GMT</pubDate>
      <guid isPermaLink="false">https://www.bbc.co.uk/weather/2643123-2021-04-03T19:00:00.000+01:00</guid>
      <dc:date>2021-04-03T18:00:00Z</dc:date>
      <georss:point>53.4809 -2.2374</georss:point>
    </item>
  </channel>
</rss>"""


async def index(request):
    return web.Response(text=rssText, content_type="text/xml")


app.router.add_get("/", index)

## We kick off our server
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"{sys.argv[0]} <port>")
        sys.exit()
    web.run_app(app, port=int(sys.argv[1]))
