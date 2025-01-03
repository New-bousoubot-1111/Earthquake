import nextcord
from nextcord.ext import commands, tasks
import json
import requests
from colorama import Fore
import asyncio
import asyncpg
import util
import os
from dateutil import parser
from datetime import datetime
import pytz

# 設定ファイルの読み込み
with open('json/config.json', 'r') as f:
    config = json.load(f)

color = nextcord.Colour(int(config['color'], 16))

class earthquake(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.id = None
        self.pool = None

    async def setup_db(self):
        """PostgreSQLとの接続プールを作成します"""
        self.pool = await asyncpg.create_pool(dsn=os.getenv("DATABASE_URL"))

        # 初回起動時にテーブルを作成
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS eew_cache (
                    key TEXT PRIMARY KEY,
                    value JSONB
                )
            """)

        # 初回起動時にeew_id用のテーブル作成
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS eew_id (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)

    async def get_cache(self, key):
        """キャッシュからデータを取得"""
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow("SELECT value FROM eew_cache WHERE key = $1", key)
            return json.loads(result['value']) if result else None

    async def set_cache(self, key, value):
        """キャッシュにデータを保存"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO eew_cache (key, value)
                VALUES ($1, $2)
                ON CONFLICT (key)
                DO UPDATE SET value = EXCLUDED.value
            """, key, json.dumps(value))

    async def get_eew_id(self):
        """PostgreSQLからeew_idを取得"""
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow("SELECT value FROM eew_id WHERE key = $1", "eew_id")
            return result['value'] if result else None

    async def set_eew_id(self, eew_id):
        """PostgreSQLにeew_idを保存"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO eew_id (key, value)
                VALUES ($1, $2)
                ON CONFLICT (key)
                DO UPDATE SET value = EXCLUDED.value
            """, "eew_id", eew_id)

    def safe_parse_time(time_str, default="不明"):
        try:
            dt = parser.parse(time_str)
            return dt.strftime('%Y/%m/%d %H時%M分')
        except (ValueError, TypeError):
            return default

    @commands.Cog.listener()
    async def on_ready(self):
        print(Fore.BLUE + "|earthquake    |" + Fore.RESET)
        await self.setup_db()
        self.eew_check.start()
        self.eew_info.start()

    @tasks.loop(seconds=2)
    async def eew_check(self):
        now = util.eew_now()
        if now == 0:
            return
        res = requests.get(f"http://www.kmoni.bosai.go.jp/webservice/hypo/eew/{now}.json")
        if res.status_code == 200:
            data = res.json()
            cache = await self.get_cache("cache") or {}

            if data['result']['message'] == "":
                if cache.get('report_time') != data['report_time']:
                    eew_channel = self.bot.get_channel(int(config['eew_channel']))
                    image = False
                    if data['is_training']:
                        return
                    if data['is_cancel']:
                        embed = nextcord.Embed(
                            title="緊急地震速報がキャンセルされました",
                            description="先ほどの緊急地震速報はキャンセルされました",
                            color=color
                        )
                        await eew_channel.send(embed=embed)
                        return

                    if data['alertflg'] == "予報":
                        start_text = ""
                        if not data['is_final']:
                            title = f"緊急地震速報 第{data['report_num']}報(予報)"
                            color2 = 0x00ffee  # ブルー
                        else:
                            title = f"緊急地震速報 最終報(予報)"
                            color2 = 0x00ffee  # ブルー
                            image = True
                        if data['calcintensity'] in ["5強", "6弱", "6強", "7"]:
                            start_text = ""

                    if data['alertflg'] == "警報":
                        start_text = "**誤報を含む情報の可能性があります。\n今後の情報に注意してください**\n"
                        if not data['is_final']:
                            title = f"緊急地震速報 第{data['report_num']}報(警報)"
                            color2 = 0xff0000  # レッド
                        else:
                            title = f"緊急地震速報 最終報(警報)"
                            color2 = 0xff0000  # レッド
                            image = True

                    time = util.eew_time()
                    time2 = util.eew_origin_time(data['origin_time'])
                    embed = nextcord.Embed(
                        title=title,
                        description=f"{start_text}{time}{time2}頃、**{data['region_name']}**で地震が発生しました。\n"
                                    f"最大予想震度は**{data['calcintensity']}**、震源の深さは**{data['depth']}**、"
                                    f"マグニチュードは**{data['magunitude']}**と推定されます。",
                        color=color2
                    )
                    await eew_channel.send(embed=embed)
                    if data['report_num'] == "1":
                        image = True
                    if image:
                        await util.eew_image(eew_channel)
                await self.set_cache("cache", data)

    #地震情報
    @tasks.loop(seconds=2)
    async def eew_info(self):
        eew_id = await self.get_eew_id()
        data = requests.get(f'https://api.p2pquake.net/v2/history?codes=551&limit=1').json()[0]["points"]
        if data[0]["isArea"] is False:
            isArea = "この地震による津波の心配はありません" if not data[0]["isArea"] else "この地震で津波が発生する可能性があります\n今後の情報に注意してください"
        request = requests.get(f'https://api.p2pquake.net/v2/history?codes=551&limit=1')
        response = request.json()[0]
        data = response['earthquake']
        hypocenter = data['hypocenter']
        if request.status_code == 200:
            if eew_id != response['id']:
                # 震度に応じた色の設定
                max_scale = round(data['maxScale'] / 10)
                if max_scale == 1:
                    color = 0x6c757d  # グレー
                    image = "images/shindo1.png"
                elif max_scale == 2:
                    color = 0x6c757d  # グレー
                    image = "images/shindo2.png"
                elif max_scale == 3:
                    color = 0x28a745  # 緑色
                    image = "images/shindo3.png"
                elif max_scale == 4:
                    color = 0xffc107  # 黄色
                    image = "images/shindo4.png"
                elif max_scale == 5:
                    color = 0xff7f00  # オレンジ色
                    image = "images/shindo5.png"
                elif max_scale == 6:
                    color = 0xdc3545  # 赤色
                    image = "images/shindo6.png"
                elif max_scale == 7:
                    color = 0x6f42c1  # 紫色
                    image = "images/shindo7.png"
                else:
                    color = 0x6c757d  # デフォルト色

                earthquake_time = parser.parse(data['time'])
                formatted_time = earthquake_time.strftime('%H時%M分')
                japan_timezone = pytz.timezone('Asia/Tokyo')
                current_time = datetime.now(japan_timezone).strftime('%Y/%m/%d %H:%M')
                embed = nextcord.Embed(title="地震情報", description=f"{formatted_time}頃、最大震度**{round(data['maxScale'] / 10)}**の地震がありました。\n{isArea}", color=color)
                embed.add_field(name="震源地", value=hypocenter['name'], inline=False)
                embed.add_field(name="マグニチュード", value=hypocenter['magnitude'], inline=False)
                embed.add_field(name="震源の深さ", value=f"{hypocenter['depth']}Km", inline=False)
                embed.set_footer(text=current_time)
                eew_channel = self.bot.get_channel(int(config['eew_channel']))
                await eew_channel.send(embed=embed)
                
                # Update eew_id in PostgreSQL
                await self.set_eew_id(response['id'])
            else:
                return

def setup(bot):
    return bot.add_cog(earthquake(bot))
