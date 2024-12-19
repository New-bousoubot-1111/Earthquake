import nextcord
from nextcord.ext import commands, tasks
import tomllib
import websockets
from websockets import client
import json
import datetime
import os
import sys
import traceback
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger('tasks')

with open('json/eew.toml','rb') as f:
  config = tomllib.load(f)

sindoMap = {
  -1: {
    'title': '不明',
    'color': 0x000000
  },
  10: {
    'title': '震度1',
    'color': 0xf2f2ff
  },
  20: {
    'title': '震度2',
    'color': 0x00aaff
  },
  30: {
    'title': '震度3',
    'color': 0x0040ff
  },
  40: {
    'title': '震度4',
    'color': 0xfae696
  },
  50: {
    'title': '震度5弱',
    'color': 0xffe600
  },
  55: {
    'title': '震度5強',
    'color': 0xff9900
  },
  60: {
    'title': '震度6弱',
    'color': 0xff2600
  },
  65: {
    'title': '震度6強',
    'color': 0xa50021
  },
  70: {
    'title': '震度7',
    'color': 0xb40069
  }
}

class Tasks(commands.Cog):
  def __init__(self,bot):
    self.bot = bot

  @commands.Cog.listener()
  async def on_ready(self):
    self.eewReport.start()

  @tasks.loop(seconds=1)
  async def eewReport(self):
    try:
      log.info('P2P地震情報WebSocketAPIに接続中です。')
      while True:
        async for websocket in client.connect('wss://api.p2pquake.net/v2/ws'):
          log.info('P2P地震情報WebSocketAPIに接続しました。')
          try:
            while True:
              received = await websocket.recv()
              data = json.loads(received)
              print(datetime.datetime.now())
              print(data['code'])
              if data['code'] == 551:
                sindo_data = sindoMap[data['earthquake']['maxScale']]
                time = datetime.datetime.strptime(data['earthquake']['time'],'%Y/%m/%d %H:%M:%S').timestamp()
                hypocenter = data['earthquake']['hypocenter']
                longitude_and_latitude = ''
                if hypocenter['latitude'] != -200 and hypocenter['longitude'] != -200:
                  longitude_and_latitude = f'(北緯{hypocenter["latitude"]}、東経{hypocenter["longitude"]})'
                if hypocenter['depth'] == 0:
                  depth = 'ごく浅い'
                else:
                  depth = f'{hypocenter["depth"]}km'

                embed = nextcord.Embed(
                  title='地震情報',
                  description=f'''<t:{time}:F>頃地震がありました。
                  震源地は、{hypocenter["name"]}{longitude_and_latitude}で、最大深度は{sindo_data["title"]}、震源の深さは{depth}、マグニチュードは{hypocenter["magnitude"]}と推定されます。
                  ''',
                  color=sindo_data['color']
                )
                embed.set_footer(text='Provided by p2pquake.net')
                await self.bot.get_channel(1316288751479033856).send(embed=embed)
          except websockets.ConnectionClosed:
            log.info('P2P地震情報WebSocketAPIとの接続が終了しました。再接続しています。')
            continue
          except:
            log.error(f'処理中にエラーが発生しました。\n{traceback.format_exc()}')
            pass
    except:
      log.error(traceback.format_exc())

def setup(bot):
  bot.add_cog(Tasks(bot))
