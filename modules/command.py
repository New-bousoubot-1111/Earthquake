import nextcord
from nextcord.ext import commands
import requests
import json
from colorama import Fore
import util
import re

with open('json/config.json', 'r') as f:
    config = json.load(f)
with open('json/help.json', 'r') as f:
    help = json.load(f)

color = nextcord.Colour(int(config['color'], 16))

def is_japanese(str):
    return True if re.search(r'[ぁ-んァ-ン]', str) else False

class command(commands.Cog):
  def __init__(self, bot):
    self.bot = bot

  @commands.Cog.listener()
  async def on_ready(self):
    print(Fore.BLUE + "|command       |" + Fore.RESET)

  #eew
  @nextcord.slash_command(description="地震情報を表示します")
  async def eew(self,ctx):
    request = requests.get(f'https://api.p2pquake.net/v2/history?codes=551&limit=1')
    response = request.json()[0]
    data = response['earthquake']
    hypocenter = data['hypocenter']
    if request.status_code == 200:
      embed=nextcord.Embed(title="地震情報",color=color)
      embed.add_field(name="震源地",value=hypocenter['name'],inline=False)
      embed.add_field(name="最大震度",value=round(data['maxScale']/10),inline=False)
      embed.add_field(name="発生時刻",value=data['time'],inline=False)
      embed.add_field(name="マグニチュード",value=hypocenter['magnitude'],inline=False)
      embed.add_field(name="震源の深さ",value=f"{hypocenter['depth']}Km",inline=False)
      await ctx.send(embed=embed)
    else:
      await ctx.send("APIリクエストでエラーが発生しました")
  #eew2
  @nextcord.slash_command(description="地震情報を表示します(文式)")
  async def eew2(self,ctx):
    request = requests.get("https://api.p2pquake.net/v2/history?codes=551&limit=1")
    response = request.json()[0]
    data = response['earthquake']
    hypocenter = data['hypocenter']
    if request.status_code == 200:
      embed=nextcord.Embed(title="地震情報",color=color)
      embed.add_field(name=f"{data['time']}頃、**{hypocenter['name']}**で地震がありました",value=f"最大震度は**{round(data['maxScale']/10)}**、震源の深さは**{hypocenter['depth']}Km**、マグニチュードは**{hypocenter['magnitude']}**です",inline=False)
      await ctx.send(embed=embed)
    else:
      await ctx.send("APIリクエストでエラーが発生しました")
      
  @nextcord.slash_command(description="botの情報やコマンドを表示します")
  async def help(self,ctx):
    creators = []
    for creator in help['owners']:
      creators.append(await self.bot.fetch_user(int(creator)))
    creators = "".join(f"\n`{x}`" for x in creators)
    commands_list = "".join(f"`{help['prefix']}{x}` " for x in help['commands_list'])
    embed=nextcord.Embed(title="情報",color=color)
    embed.add_field(name=f"作成者",value=f"{creators}")
    embed.add_field(name=f"言語",value="Python")

    embed2=nextcord.Embed(title="コマンド",description=f"***{commands_list}***",color=color)
    await ctx.send(embed=embed,view=util.help_page(embed,embed2))

def setup(bot):
    return bot.add_cog(command(bot))
