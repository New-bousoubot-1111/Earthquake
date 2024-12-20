import nextcord
from nextcord.ext import commands
import datetime
import json

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
        self.previous_hypocenter = None  # 前回の震源地情報を保持

    @nextcord.slash_command(description="地震情報のテストを送信します")
    async def test_eew(self, interaction: nextcord.Interaction):
        """スラッシュコマンドでテスト地震情報を送信"""
        test_data = {
            'code': 551,
            'earthquake': {
                'time': '2024/12/20 10:00:00',
                'maxScale': 40,
                'hypocenter': {
                    'name': '',
                    'latitude': -200,
                    'longitude': -200,
                    'depth': 0,
                    'magnitude': 4.2,
                }
            }
        }
        await self.handle_eew_data(test_data, interaction.channel_id)
        await interaction.response.send_message("テスト用の地震情報を送信しました。", ephemeral=True)

    async def handle_eew_data(self, data, channel_id):
        """地震情報を処理して送信"""
        sindo_data = sindoMap[data['earthquake']['maxScale']]
        time = datetime.datetime.strptime(data['earthquake']['time'], '%Y/%m/%d %H:%M:%S').timestamp()
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

        # Embedの作成
        description = f'''<t:{time}:F>頃、{sindo_data["title"]}の地震がありました。'''
        if not hypocenter_name:
            description += "\n震源地は現在調査中です。"

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

        # メッセージを送信
        channel = self.bot.get_channel(channel_id)
        await channel.send(embed=embed)

        # 震源地情報を更新
        self.previous_hypocenter = hypocenter_name

def setup(bot):
  bot.add_cog(Test(bot))
