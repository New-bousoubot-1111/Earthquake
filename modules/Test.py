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
    'title': '最大震度1',
    'color': 0xf2f2ff
  },
  20: {
    'title': '最大震度2',
    'color': 0x00aaff
  },
  30: {
    'title': '最大震度3',
    'color': 0x0040ff
  },
  40: {
    'title': '最大震度4',
    'color': 0xfae696
  },
  50: {
    'title': '最大震度5弱',
    'color': 0xffe600
  },
  55: {
    'title': '最大震度5強',
    'color': 0xff9900
  },
  60: {
    'title': '最大震度6弱',
    'color': 0xff2600
  },
  65: {
    'title': '最大震度6強',
    'color': 0xa50021
  },
  70: {
    'title': '最大震度7',
    'color': 0xb40069
  }
}

class Test(commands.Cog):
  def __init__(self, bot):
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
                time_obj = datetime.datetime.strptime(data['earthquake']['time'], '%Y/%m/%d %H:%M:%S')
                time = time_obj.strftime('%d日 %H時%M分')
                hypocenter = data['earthquake']['hypocenter']
                longitude_and_latitude = ''
                if hypocenter['latitude'] != -200 and hypocenter['longitude'] != -200:
                  longitude_and_latitude = f'(北緯{hypocenter["latitude"]}、東経{hypocenter["longitude"]})'
                if hypocenter['depth'] == 0:
                  depth = 'ごく浅い'
                else:
                  depth = f'{hypocenter["depth"]}km'
                # 震源地が不明な場合
                if not hypocenter['name']:
                    hypocenter_name = None
                else:
                    hypocenter_name = hypocenter['name']

                # 国内津波の有無をチェック
                domestic_tsunami = data['earthquake'].get('domesticTsunami', 'None')

                # 津波情報のメッセージを設定
                if domestic_tsunami == 'None':
                    tsunami_message = '津波の心配はありません。'
                elif domestic_tsunami == 'Checking':
                    tsunami_message = '津波の情報は調査中です。'
                else:
                    tsunami_message = f"津波: {domestic_tsunami}"

                # 震源地と津波が両方不明の場合のメッセージ設定
                if not hypocenter_name and domestic_tsunami == 'None':
                    description = f'{time}頃、{sindo_data["title"]}の地震がありました。\n震源地・津波については現在調査中です。'
                else:
                    description = f'{time}頃、{sindo_data["title"]}の地震がありました。'
                    if not hypocenter_name:
                        description += "\n震源地は現在調査中です。"
                    description += f"\n{tsunami_message}"  # 津波情報をdescriptionに追加

                # Embedの作成
                embed = nextcord.Embed(
                    title='地震情報',
                    description=description,
                    color=sindo_data['color']
                )

                # 震源地がわかる場合のみフィールドを追加
                if hypocenter_name:
                    embed.add_field(name="震源地", value=f"{hypocenter_name}{longitude_and_latitude}", inline=False)
                embed.add_field(name="マグニチュード", value=hypocenter["magnitude"], inline=False)
                embed.add_field(name="震源の深さ", value=depth, inline=False)
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
  bot.add_cog(Test(bot))
