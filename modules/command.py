import nextcord
from nextcord.ext import commands
import requests
import json
from colorama import Fore
import matplotlib.pyplot as plt
import geopandas as gpd
import util
import os

with open('json/config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

with open('json/help.json', 'r', encoding='utf-8') as f:
    help_json = json.load(f)

color = nextcord.Colour(int(config['color'], 16))


# =========================
# 震源地名 → 都道府県変換
# =========================
def get_prefecture(hypocenter_name):

    prefectures = [
        "北海道",
        "青森県",
        "岩手県",
        "宮城県",
        "秋田県",
        "山形県",
        "福島県",
        "茨城県",
        "栃木県",
        "群馬県",
        "埼玉県",
        "千葉県",
        "東京都",
        "神奈川県",
        "新潟県",
        "富山県",
        "石川県",
        "福井県",
        "山梨県",
        "長野県",
        "岐阜県",
        "静岡県",
        "愛知県",
        "三重県",
        "滋賀県",
        "京都府",
        "大阪府",
        "兵庫県",
        "奈良県",
        "和歌山県",
        "鳥取県",
        "島根県",
        "岡山県",
        "広島県",
        "山口県",
        "徳島県",
        "香川県",
        "愛媛県",
        "高知県",
        "福岡県",
        "佐賀県",
        "長崎県",
        "熊本県",
        "大分県",
        "宮崎県",
        "鹿児島県",
        "沖縄県"
    ]

    for pref in prefectures:
        if pref in hypocenter_name:
            return pref

    return None


# =========================
# 地図生成
# =========================
def create_earthquake_map(prefecture_name, latitude, longitude):

    # 地図データ読み込み
    gdf = gpd.read_file("./images/japan.geojson")

    # 色設定
    gdf["color"] = "#4d4d4d"

    # 該当県を青に
    gdf.loc[gdf["nam_ja"] == prefecture_name, "color"] = "#1f5d8c"

    # 描画
    fig, ax = plt.subplots(figsize=(14, 10))

    # 背景色
    fig.patch.set_facecolor("#0a1110")
    ax.set_facecolor("#0a1110")

    # 地図描画
    gdf.plot(
        ax=ax,
        color=gdf["color"],
        edgecolor="white",
        linewidth=0.6
    )

    # 震源位置に × マーク
    ax.plot(
        longitude,
        latitude,
        marker='x',
        markersize=30,
        markeredgewidth=6,
        color='red'
    )

    # 数字ラベル
    target = gdf[gdf["name"] == prefecture_name]

    if not target.empty:
        point = target.geometry.centroid.iloc[0]

        ax.text(
            point.x,
            point.y,
            "1",
            fontsize=25,
            color="white",
            ha="center",
            va="center",
            bbox=dict(
                boxstyle="square",
                facecolor="#24577a",
                edgecolor="#17384f"
            )
        )

    # 軸消す
    ax.axis("off")

    # 保存
    plt.savefig(
        "earthquake.png",
        bbox_inches="tight",
        facecolor=fig.get_facecolor(),
        dpi=300
    )

    plt.close()


class command(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(Fore.BLUE + "|command       |" + Fore.RESET)

    # ==================================
    # 地震情報
    # ==================================
    @nextcord.slash_command(description="地震情報を表示します")
    async def eew(self, ctx):

        request = requests.get(
            "https://api.p2pquake.net/v2/history?codes=551&limit=1"
        )

        if request.status_code != 200:
            await ctx.send("APIリクエストでエラーが発生しました")
            return

        response = request.json()[0]

        data = response['earthquake']
        hypocenter = data['hypocenter']

        hypocenter_name = hypocenter['name']

        latitude = hypocenter['latitude']
        longitude = hypocenter['longitude']

        prefecture = get_prefecture(hypocenter_name)

        # 地図生成
        if prefecture is not None:
            create_earthquake_map(
                prefecture,
                latitude,
                longitude
            )

        # Embed
        embed = nextcord.Embed(
            title="地震情報",
            color=color
        )

        embed.add_field(
            name="震源地",
            value=hypocenter_name,
            inline=False
        )

        embed.add_field(
            name="最大震度",
            value=round(data['maxScale'] / 10),
            inline=False
        )

        embed.add_field(
            name="発生時刻",
            value=data['time'],
            inline=False
        )

        embed.add_field(
            name="マグニチュード",
            value=hypocenter['magnitude'],
            inline=False
        )

        embed.add_field(
            name="震源の深さ",
            value=f"{hypocenter['depth']}Km",
            inline=False
        )

        # 画像添付
        if os.path.exists("earthquake.png"):

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

        else:
            await ctx.send(embed=embed)


    @nextcord.slash_command(description="地震情報を表示します(文式)")
    async def eew2(self, ctx):

        request = requests.get(
            "https://api.p2pquake.net/v2/history?codes=551&limit=1"
        )

        if request.status_code != 200:
            await ctx.send("APIリクエストでエラーが発生しました")
            return

        response = request.json()[0]

        data = response['earthquake']
        hypocenter = data['hypocenter']

        hypocenter_name = hypocenter['name']

        latitude = hypocenter['latitude']
        longitude = hypocenter['longitude']

        prefecture = get_prefecture(hypocenter_name)

        # 地図生成
        if prefecture is not None:
            create_earthquake_map(
                prefecture,
                latitude,
                longitude
            )

        # Embed作成
        embed = nextcord.Embed(
            title="地震情報",
            color=color
        )

        embed.add_field(
            name=(
                f"{data['time']}頃、"
                f"**{hypocenter_name}**で"
                f"地震がありました"
            ),
            value=(
                f"最大震度は **{round(data['maxScale']/10)}**\n"
                f"震源の深さは **{hypocenter['depth']}Km**\n"
                f"マグニチュードは **{hypocenter['magnitude']}**"
            ),
            inline=False
        )

        # 画像添付
        if os.path.exists("earthquake.png"):

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

        else:
            await ctx.send(embed=embed)

    # ==================================
    # HELP
    # ==================================
    @nextcord.slash_command(description="botの情報やコマンドを表示します")
    async def help(self, ctx):

        creators = []

        for creator in help_json['owners']:
            creators.append(
                await self.bot.fetch_user(int(creator))
            )

        creators = "".join(
            f"\n`{x}`"
            for x in creators
        )

        commands_list = "".join(
            f"`{help_json['prefix']}{x}` "
            for x in help_json['commands_list']
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
