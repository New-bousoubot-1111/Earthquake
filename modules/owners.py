import nextcord
from nextcord.ext import commands
import json
import os
import sys
import time
import datetime
from colorama import Fore
import util
import eval

with open('json/config.json','r') as f:
	config = json.load(f)
with open('json/help.json','r') as f:
	help = json.load(f)

color = nextcord.Colour(int(config['color'],16))

class owners(commands.Cog):
  def __init__(self, bot):
    self.bot = bot
		
  @commands.Cog.listener()
  async def on_ready(self):
    print(Fore.BLUE + "|owner         |" + Fore.RESET)
    global start_time
    start_time = time.time()

  #再起動
  @nextcord.slash_command(description="再起動をする")
  async def restart(self,ctx):
    if ctx.user.id in config['owners']:
        now = datetime.datetime.utcnow()
        embed=nextcord.Embed(title="再起動中...",description=f"再起動時間\n<t:{round(now.timestamp())}:F>",color=color)
        await ctx.send(embed=embed, ephemeral=True)
        print(Fore.GREEN + f"[Rebooting]{now}" + Fore.RESET)
        res = sys.executable
        os.execl(res,res,*sys.argv)
    else:
        embed=util.creator_only()
        await ctx.send(embed=embed,ephemeral=True)
      
  #BOT-INFO
  @nextcord.slash_command(description="BOT-INFO")
  async def owners(self,ctx):
    if ctx.user.id in config['owners']:
        embed=nextcord.Embed(title="開発メニュー",color=color)
        embed.add_field(name="ツール",value="Python")
        embed.add_field(name="作成者",value="ぼうそうBOT")
        embed.add_field(name="起動経過時間",value=f"`{util.sec_formatter(time.time() - start_time)}`")
        modules = []
        for module in self.bot.extensions:
          modules.append(module)
        embed.add_field(name="読み込まれているモジュール",value="\n".join(f"`{x}`" for x in modules),inline=False)
        await ctx.send(embed=embed,view=eval.devmenu_view())
    else:
        embed=util.creator_only()
        await ctx.send(embed=embed,ephemeral=True)

  #メッセージ削除(指定)
  @nextcord.slash_command(description="指定してメッセージを削除します")
  async def clear(self, ctx, amount : int=nextcord.SlashOption(name="数値",description="削除したい数を書いて下さい")):
    em=nextcord.Embed(title="メッセージを削除しています",color=0x08e2b7)
    await ctx.send(embed=em)
    if ctx.user.guild_permissions.administrator:
      em=nextcord.Embed(title="削除", description=f"{amount}件のメッセージを削除しました",color=0x08e2b7)
      await ctx.channel.purge(limit=amount)
      await ctx.send(embed=em)
    else:
      em=nextcord.Embed(title="Error", description="このコマンドは管理者専用です",color=0xff0000)
      await ctx.send(embed=em)
  #メッセージ削除(全て)
  @nextcord.slash_command(description="全てのメッセージを削除します")
  async def clear_all(self, ctx):
    em=nextcord.Embed(title="メッセージを削除しています",color=0x08e2b7)
    await ctx.send(embed=em)
    if ctx.user.guild_permissions.administrator:
      em=nextcord.Embed(title="削除", description="全てのメッセージを削除しました",color=0x08e2b7)
      await ctx.channel.purge(limit=None)
      await ctx.send(embed=em)
    else:
      em=nextcord.Embed(title="Error", description="このコマンドは管理者専用です",color=0xff0000)
      await ctx.send(embed=em)

def setup(bot):
  return bot.add_cog(owners(bot))
