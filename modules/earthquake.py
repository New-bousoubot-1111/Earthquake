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
import matplotlib.pyplot as plt
import geopandas as gpd

# 設定ファイルの読み込み
with open('json/config.json', 'r') as f:
    config = json.load(f)

color = nextcord.Colour(int(config['color'], 16))

def get_prefecture(text):

    prefectures = [
        "北海道", "青森県", "岩手県", "宮城県", "秋田県",
        "山形県", "福島県", "茨城県", "栃木県", "群馬県",
        "埼玉県", "千葉県", "東京都", "神奈川県", "新潟県",
        "富山県", "石川県", "福井県", "山梨県", "長野県",
        "岐阜県", "静岡県", "愛知県", "三重県", "滋賀県",
        "京都府", "大阪府", "兵庫県", "奈良県", "和歌山県",
        "鳥取県", "島根県", "岡山県", "広島県", "山口県",
        "徳島県", "香川県", "愛媛県", "高知県", "福岡県",
        "佐賀県", "長崎県", "熊本県", "大分県", "宮崎県",
        "鹿児島県", "沖縄県"
    ]

    for pref in prefectures:
        if pref in text:
            return pref

    return None


# ==========================================
# 地図生成
# ==========================================
def create_earthquake_map(latitude, longitude, points):

    # GeoJSON読み込み
    gdf = gpd.read_file("./images/japan.geojson")

    # 県名カラム
    NAME_COLUMN = "nam_ja"

    # 初期色
    gdf["color"] = "#4d4d4d"

    # ==========================================
    # 都道府県ごとの最大震度
    # ==========================================
    prefecture_scales = {}

    for point_data in points:

        scale = point_data["scale"]

        # 都道府県取得
        pref = point_data.get("pref")

        # prefが無い場合
        if pref is None:

            addr = point_data.get("addr", "")

            pref = get_prefecture(addr)

        if pref is None:
            continue

        # 震度
        intensity = round(scale / 10)

        # 最大震度保持
        if pref not in prefecture_scales:

            prefecture_scales[pref] = intensity

        else:

            if intensity > prefecture_scales[pref]:

                prefecture_scales[pref] = intensity

    # ==========================================
    # 色分け
    # ==========================================
    for pref, intensity in prefecture_scales.items():

        if intensity == 1:
            map_color = "#24577a"

        elif intensity == 2:
            map_color = "#2e8b57"

        elif intensity == 3:
            map_color = "#c9a227"

        elif intensity == 4:
            map_color = "#d97706"

        elif intensity >= 5:
            map_color = "#c0392b"

        else:
            map_color = "#4d4d4d"

        gdf.loc[
            gdf[NAME_COLUMN] == pref,
            "color"
        ] = map_color

    # ==========================================
    # 描画
    # ==========================================
    fig, ax = plt.subplots(figsize=(14, 10))

    fig.patch.set_facecolor("#020c0d")
    ax.set_facecolor("#020c0d")

    gdf.plot(
        ax=ax,
        color=gdf["color"],
        edgecolor="white",
        linewidth=0.8
    )

    # ==========================================
    # 震度表示
    # ==========================================
    for pref, intensity in prefecture_scales.items():

        target = gdf[
            gdf[NAME_COLUMN] == pref
        ]

        if target.empty:
            continue

        # centroidより安全
        point = target.geometry.representative_point().iloc[0]

        # 震源から近い県だけ表示
        distance = (
            (point.x - longitude) ** 2 +
            (point.y - latitude) ** 2
        ) ** 0.5

        if distance > 5:
            continue

        # 色
        if intensity == 1:
            text_bg = "#24577a"

        elif intensity == 2:
            text_bg = "#2e8b57"

        elif intensity == 3:
            text_bg = "#c9a227"

        elif intensity == 4:
            text_bg = "#d97706"

        else:
            text_bg = "#c0392b"

        ax.text(
            point.x,
            point.y,
            str(intensity),
            fontsize=18,
            color="white",
            ha="center",
            va="center",
            bbox=dict(
                boxstyle="square",
                facecolor=text_bg,
                edgecolor="#102433",
                alpha=0.95
            ),
            zorder=20
        )

    # ==========================================
    # 震源マーク
    # ==========================================
    ax.plot(
        longitude,
        latitude,
        marker='x',
        markersize=16,
        markeredgewidth=3,
        color='red',
        zorder=30
    )

    # ==========================================
    # ズーム
    # ==========================================
    zoom = 2.3

    ax.set_xlim(
        longitude - zoom,
        longitude + zoom
    )

    ax.set_ylim(
        latitude - zoom,
        latitude + zoom
    )

    # 軸削除
    ax.axis("off")

    # 保存
    plt.savefig(
        "earthquake2.png",
        bbox_inches="tight",
        facecolor=fig.get_facecolor(),
        dpi=300
    )

    plt.close()

class earthquake(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.id = None
        self.pool = None

    async def setup_db(self):

        DATABASE_URL = os.getenv("eew_cache_url")

        self.pool = await asyncpg.create_pool(
            dsn=DATABASE_URL,
            ssl="require",
            min_size=1,
            max_size=5
        )

        async with self.pool.acquire() as conn:

            # EEWキャッシュ
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS eew_cache (
                    key TEXT PRIMARY KEY,
                    value JSONB
                )
            """)

            # 地震情報ID
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS eew_id (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)

            print("PostgreSQL connected")
            

    async def get_cache(self, key):
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow(
                "SELECT value FROM eew_cache WHERE key = $1",
                key
            )
            if result:
                value = result["value"]
                if isinstance(value, str):
                    return json.loads(value)
                return value
            return None
        

    async def set_cache(self, key, value):

        async with self.pool.acquire() as conn:

            await conn.execute("""
                INSERT INTO eew_cache (key, value)
                VALUES ($1, $2::jsonb)
                ON CONFLICT (key)
                DO UPDATE SET value = EXCLUDED.value
            """, key, json.dumps(value))

    async def get_eew_id(self):

        async with self.pool.acquire() as conn:

            result = await conn.fetchrow(
                "SELECT value FROM eew_id WHERE key = $1",
                "eew_id"
            )

            if result:
                return result["value"]

            return None

    async def set_eew_id(self, eew_id):

        async with self.pool.acquire() as conn:

            await conn.execute("""
                INSERT INTO eew_id (key, value)
                VALUES ($1, $2)
                ON CONFLICT (key)
                DO UPDATE SET value = EXCLUDED.value
            """, "eew_id", str(eew_id))

            print(f"Saved eew_id: {eew_id}")

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
        if not self.eew_check.is_running():
           self.eew_check.start()
        if not self.eew_info.is_running():
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
                
            except Exception as e:
            
                print(f"eew_check error: {e}")

    #地震情報
    @tasks.loop(seconds=5)
    async def eew_info(self):
        try:
            request = requests.get(
            "https://api.p2pquake.net/v2/history?codes=551&limit=1"
        )
            if request.status_code != 200:
                return
            response = request.json()[0]
            current_id = str(response["id"])
            saved_id = await self.get_eew_id()
            if saved_id == current_id:
                return

            data = response["earthquake"]
    
            hypocenter = data["hypocenter"]

            points = response["points"]

            latitude = hypocenter.get("latitude")
            longitude = hypocenter.get("longitude")

            hypocenter_name = hypocenter.get("name")
            magnitude = hypocenter.get("magnitude")
            depth = hypocenter.get("depth")

            unknown_hypocenter = (
                hypocenter_name in [None, "", "不明"] or
                magnitude in [-1, "-1", None] or
                depth in [-1, "-1", None]
            )

            if not unknown_hypocenter:

                create_earthquake_map(
                    latitude,
                    longitude,
                    points
                )

            max_scale = round(data["maxScale"] / 10)

            if max_scale <= 2:
                embed_color = 0x6c757d

            elif max_scale == 3:
                embed_color = 0x28a745

            elif max_scale == 4:
                embed_color = 0xffc107

            elif max_scale == 5:
                embed_color = 0xff7f00

            elif max_scale == 6:
                embed_color = 0xdc3545

            else:
                embed_color = 0x6f42c1

            earthquake_time = parser.parse(data["time"])

            formatted_time = earthquake_time.strftime('%H時%M分')

            japan_timezone = pytz.timezone('Asia/Tokyo')

            current_time = datetime.now(
                japan_timezone
            ).strftime('%Y/%m/%d %H:%M')

            if unknown_hypocenter:
                embed = nextcord.Embed(
                    title="地震情報",
                    description=
                    f"{formatted_time}頃、"
                    f"最大震度**{max_scale}**を観測する地震がありました。\n"
                    f"震源・津波については現在調査中です。",
                    color=embed_color
                )
            else:
                if points[0]["isArea"] is False:
                    isArea = "この地震による津波の心配はありません"
                else:
                    isArea = (
                        "この地震で津波が発生する可能性があります\n"
                        "今後の情報に注意してください"
                    )
                embed = nextcord.Embed(
                    title="地震情報",
                    description=
                    f"{formatted_time}頃、"
                    f"最大震度**{max_scale}**の地震がありました。\n"
                    f"{isArea}",
                    color=embed_color
                )
                embed.add_field(
                    name="震源地",
                    value=str(hypocenter_name),
                    inline=False
                )
                embed.add_field(
                    name="マグニチュード",
                    value=str(magnitude),
                    inline=False
                )
                embed.add_field(
                    name="震源の深さ",
                    value=f"{depth}Km",
                    inline=False
                )
                file = nextcord.File(
                    "earthquake2.png",
                    filename="earthquake2.png"
                )
                embed.set_image(
                    url="attachment://earthquake2.png"
                )
            embed.set_footer(
                text=current_time
            )
            eew_channel2 = self.bot.get_channel(
                int(config['eew_channel2'])
            )
            if unknown_hypocenter:

                await eew_channel2.send(
                    embed=embed
                )
            else:
                await eew_channel2.send(
                    embed=embed,
                    file=file
                )
            await self.set_eew_id(current_id)

        except Exception as e:
            print(f"eew_info error: {e}")

def setup(bot):
    return bot.add_cog(earthquake(bot))
