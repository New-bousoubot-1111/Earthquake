import nextcord
from nextcord.ext import commands
import requests
import json
from colorama import Fore
import matplotlib.pyplot as plt
import geopandas as gpd
import util

with open('json/config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

with open('json/help.json', 'r', encoding='utf-8') as f:
    help_json = json.load(f)

color = nextcord.Colour(int(config['color'], 16))


# ==========================================
# 都道府県取得
# ==========================================
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
        "earthquake.png",
        bbox_inches="tight",
        facecolor=fig.get_facecolor(),
        dpi=300
    )

    plt.close()

def convert_scale(scale):

    scale_table = {
        10: "1",
        20: "2",
        30: "3",
        40: "4",
        45: "5弱",
        50: "5強",
        55: "6弱",
        60: "6強",
        70: "7"
    }

    return scale_table.get(scale, "不明")

class command(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(Fore.BLUE + "|command       |" + Fore.RESET)

    # ==========================================
    # 地震情報
    # ==========================================
    @nextcord.slash_command(
        description="地震情報を表示します"
    )
    async def eew(self, ctx):

        request = requests.get(
            "https://api.p2pquake.net/v2/history?codes=551&limit=1"
        )
        data = requests.get(f'https://api.p2pquake.net/v2/history?codes=551&limit=1').json()[0]["points"]
        if data[0]["isArea"] is False:
            isArea = "この地震による津波の心配はありません" if not data[0]["isArea"] else "この地震で津波が発生する可能性があります\n今後の情報に注意してください"

        if request.status_code != 200:

            await ctx.send(
                "APIリクエストでエラーが発生しました"
            )

            return

        response = request.json()[0]

        data = response["earthquake"]

        hypocenter = data["hypocenter"]

        latitude = hypocenter["latitude"]
        longitude = hypocenter["longitude"]

        max_scale = convert_scale(data["maxScale"])

        if max_scale in ["1", "2"]:
            embed_color = 0x6c757d

        elif max_scale == "3":
            embed_color = 0x28a745

        elif max_scale == "4":
            embed_color = 0xffc107

        elif max_scale in ["5弱", "5強"]:
            embed_color = 0xff7f00

        elif max_scale in ["6弱", "6強"]:
            embed_color = 0xdc3545

        elif max_scale == "7":
            embed_color = 0x6f42c1

        else:
            embed_color = 0x6c757d

        # 地図生成
        create_earthquake_map(
            latitude,
            longitude,
            response["points"]
        )

        # Embed
        embed = nextcord.Embed(
            title="地震情報",
            color=color
        )

        embed.add_field(
            name="震源地",
            value=hypocenter["name"],
            inline=False
        )

        embed.add_field(
            name="最大震度",
            value={max_scale},
            inline=False
        )

        embed.add_field(
            name="発生時刻",
            value=data["time"],
            inline=False
        )

        embed.add_field(
            name="マグニチュード",
            value=str(hypocenter["magnitude"]),
            inline=False
        )

        embed.add_field(
            name="震源の深さ",
            value=f"{hypocenter['depth']}Km\n\n{isArea}",
            inline=False
        )

        file = nextcord.File(
            "earthquake.png",
            filename="earthquake.png"
        )

        embed.set_image(
            url="attachment://earthquake.png"
        )

        await ctx.send(
            embed=embed,
            file=file
        )

    # ==========================================
    # 地震情報（文式）
    # ==========================================
    @nextcord.slash_command(
        description="地震情報を表示します(文式)"
    )
    async def eew2(self, ctx):

        request = requests.get(
            "https://api.p2pquake.net/v2/history?codes=551&limit=1"
        )
        data = requests.get(f'https://api.p2pquake.net/v2/history?codes=551&limit=1').json()[0]["points"]
        if data[0]["isArea"] is False:
            isArea = "この地震による津波の心配はありません" if not data[0]["isArea"] else "この地震で津波が発生する可能性があります\n今後の情報に注意してください"
        if request.status_code != 200:

            await ctx.send(
                "APIリクエストでエラーが発生しました"
            )

            return

        response = request.json()[0]

        data = response["earthquake"]

        hypocenter = data["hypocenter"]

        latitude = hypocenter["latitude"]
        longitude = hypocenter["longitude"]

        # 地図生成
        create_earthquake_map(
            latitude,
            longitude,
            response["points"]
        )

        embed = nextcord.Embed(
            title="地震情報",
            color=color
        )

        embed.add_field(
            name=(
                f"{data['time']}頃、"
                f"**{hypocenter['name']}**で"
                f"地震がありました。"
            ),
            value=(
                f"最大震度は"
                f"**{round(data['maxScale']/10)}**、"
                f"震源の深さは"
                f"**{hypocenter['depth']}Km**、"
                f"マグニチュードは"
                f"**{hypocenter['magnitude']}**です\n\n"
                f"{isArea}"
            ),
            inline=False
        )

        file = nextcord.File(
            "earthquake.png",
            filename="earthquake.png"
        )

        embed.set_image(
            url="attachment://earthquake.png"
        )

        await ctx.send(
            embed=embed,
            file=file
        )

    # ==========================================
    # HELP
    # ==========================================
    @nextcord.slash_command(
        description="botの情報やコマンドを表示します"
    )
    async def help(self, ctx):

        creators = []

        for creator in help_json["owners"]:

            creators.append(
                await self.bot.fetch_user(
                    int(creator)
                )
            )

        creators = "".join(
            f"\n`{x}`"
            for x in creators
        )

        commands_list = "".join(
            f"`{help_json['prefix']}{x}` "
            for x in help_json["commands_list"]
        )

        embed = nextcord.Embed(
            title="情報",
            color=color
        )

        embed.add_field(
            name="作成者",
            value=creators
        )

        embed.add_field(
            name="言語",
            value="Python"
        )

        embed2 = nextcord.Embed(
            title="コマンド",
            description=f"***{commands_list}***",
            color=color
        )

        await ctx.send(
            embed=embed,
            view=util.help_page(embed, embed2)
        )


def setup(bot):
    return bot.add_cog(command(bot))
