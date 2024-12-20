import nextcord
from nextcord.ext import commands
import traceback
import json
from colorama import Fore
import os
import webserver
import util
import subprocess
import sys
import asyncio

try:
    # pip3 uninstall discord.py を実行
    subprocess.check_call(["python3", "-m", "pip", "uninstall", "discord.py", "-y"])
    print("discord.py のアンインストールに成功しました。")
except subprocess.CalledProcessError as e:
    print("アンインストール中にエラーが発生しました:", e)

with open('json/config.json', 'r') as f:
    config = json.load(f)

color = nextcord.Colour(int(config['color'],16))
CHANNEL_ID = 1073233143412301927

intents = nextcord.Intents.all()
intents.members = True
intents.message_content = True
bot = commands.Bot(
	help_command=None,
	intents=intents
)
for module in config['modules']:
    bot.load_extension(f"modules.{module}")

@bot.event
async def on_ready():
    print(Fore.GREEN + f"[Ready]\nbot:{bot.user.name}" + Fore.RESET)
    print(Fore.BLUE + "読み込みファイル" + Fore.RESET)
    print(Fore.BLUE + "----------------" + Fore.RESET)

@bot.event
async def on_application_command_error(ctx, error:Exception):
    if isinstance(error, commands.errors.CommandError):
      embed=nextcord.Embed(title='エラーが発生しました',description=f'原因不明です',color=0xff0000)
      await ctx.channel.send(embed=embed)
    else:
        embed=nextcord.Embed(title="エラーが発生しました",description=f"Error ID:`{ctx.id}`\n```py\n{error}\n```\nこのエラーは作成者に送信されました",color=0xff0000)
        embed2=nextcord.Embed(title="Error Log",description=f"Error ID:{ctx.id}") 
        embed2.add_field(name="実行者",value=ctx.user)
        embed2.add_field(name="実行サーバー",value=ctx.guild.name)
        embed2.add_field(name="エラー内容",value=f"```{error}```")
        await ctx.send(embed=embed)
        format_error = "".join(traceback.TracebackException.from_exception(error).format())
        embed3=nextcord.Embed(title="エラー内容",description=f"```{format_error}```")
        Error_Log = 1073233143412301927
        channel = bot.get_channel(Error_Log)
        await channel.send(embed=embed2,view=util.open_error(embed2,embed3))
        error2 = "".join(
            traceback.TracebackException.from_exception(error).format())
        with open(f'errorlogs/{str(ctx.message.id)}.errorlog', 'w') as f:
            f.write(error2)
        print(Fore.RED + f"[Error]{error2}" + Fore.RESET)


# エラー通知を送信する関数
async def send_error_message(error_message):
    channel = bot.get_channel(CHANNEL_ID)  # チャンネルIDを指定
    if channel:  # チャンネルが正しく取得できた場合のみメッセージ送信
        await channel.send(f"Bot Crashed/Error/Disconnected:\n{error_message}")
    else:
        print("Error: Invalid channel ID.")

# on_errorイベント: エラーが発生したときに通知
@bot.event
async def on_error(event, *args, **kwargs):
    error_message = f"An error occurred in {event}:\n"
    error_message += ''.join(traceback.format_exception(*sys.exc_info()))
    await send_error_message(error_message)

# on_disconnectイベント: Botがオフラインになったときに通知
@bot.event
async def on_disconnect():
    error_message = "Bot has been disconnected and is now offline."
    await send_error_message(error_message)

# sys.excepthookのカスタマイズ: クラッシュ時に通知
def handle_exception(exc_type, exc_value, exc_tb):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
    else:
        error_message = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
        asyncio.run(send_error_message(error_message))

# sys.excepthookにハンドラーをセット
sys.excepthook = handle_exception

webserver.start()
try:
    bot.run(os.getenv("token"))
except:
    os.system("kill 1")
