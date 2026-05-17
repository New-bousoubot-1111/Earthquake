import nextcord
from nextcord.ext import commands
import requests
import json
import os
import re
from colorama import Fore
import geopandas as gpd
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw
import util

with open('json/config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

with open('json/help.json', 'r', encoding='utf-8') as f:
    help = json.load(f)

color = nextcord.Colour(int(config['color'], 16))

JAPAN_GEOJSON = "./images/japan.geojson"

gdf = gpd.read_file(JAPAN_GEOJSON)

def is_japanese(string):
    return True if re.search(r'[ぁ-んァ-ン]', string) else False

def generate_earthquake_map(lat, lon):

    fig, ax = plt.subplots(figsize=(10, 12))

    fig.patch.set_facecolor("#2a2a2a")
    ax.set_facecolor("#2a2a2a")

    gdf.plot(
        ax=ax,
        color="#767676",
        edgecolor="#d0d0d0",
        linewidth=0.5
    )

    ax.plot(
        lon,
        lat,
        marker='x',
        markersize=25,
        markeredgewidth=5,
        color='red'
    )

    ax.set_xlim([122, 154])
    ax.set_ylim([20, 47])

    ax.set_axis_off()

    output_path = "images/earthquake_map.png"

    os.makedirs(
        os.path.dirname(output_path),
        exist_ok=True
    )

    plt.savefig(
        output_path,
        bbox_inches='tight',
        dpi=300,
        facecolor=fig.get_facecolor()
    )

    plt.close()

    image = Image.open(output_path)

    draw = ImageDraw.Draw(image)

    width, height = image.size

    draw.rectangle(
        [(30, 30), (650, 170)],
        fill=(255, 255, 255),
        outline=(255, 0, 0),
        width=8
    )

    image.save(output_path)

    return output_path

class command(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(Fore.BLUE + "|command       |" + Fore.RESET)


    @nextcord.slash_command(
        description="地震情報を表示します"
    )
    async def eew(self, ctx):

        request = requests.get(
            'https://api.p2pquake.net/v2/history?codes=551&limit=1'
        )

        response = request.json()[0]

        data = response['earthquake']

        hypocenter = data['hypocenter']

        if request.status_code == 200:

            lat = hypocenter['latitude']
            lon = hypocenter['longitude']

            # 地図生成
            map_path = generate_earthquake_map(
                lat,
                lon
            )

            embed = nextcord.Embed(
                title="地震情報",
                color=color
            )

            embed.add_field(
                name="震源地",
                value=hypocenter['name'],
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

            # 地図画像
            file = nextcord.File(
                map_path,
                filename="earthquake_map.png"
            )

            embed.set_image(
                url="attachment://earthquake_map.png"
            )

            await ctx.send(
                embed=embed,
                file=file
            )

        else:
            await ctx.send(
                "APIリクエストでエラーが発生しました"
            )

    @nextcord.slash_command(
        description="地震情報を表示します(文式)"
    )
    async def eew2(self, ctx):

        request = requests.get(
            "https://api.p2pquake.net/v2/history?codes=551&limit=1"
        )

        response = request.json()[0]

        data = response['earthquake']

        hypocenter = data['hypocenter']

        if request.status_code == 200:

            lat = hypocenter['latitude']
            lon = hypocenter['longitude']

            # 地図生成
            map_path = generate_earthquake_map(
                lat,
                lon
            )

            embed = nextcord.Embed(
                title="地震情報",
                color=color
            )

            embed.add_field(
                name=f"{data['time']}頃、{hypocenter['name']}で地震がありました",
                value=(
                    f"最大震度は{round(data['maxScale']/10)}\n"
                    f"震源の深さは{hypocenter['depth']}Km\n"
                    f"マグニチュードは{hypocenter['magnitude']}"
                ),
                inline=False
            )

            file = nextcord.File(
                map_path,
                filename="earthquake_map.png"
            )

            embed.set_image(
                url="attachment://earthquake_map.png"
            )

            await ctx.send(
                embed=embed,
                file=file
            )

        else:
            await ctx.send(
                "APIリクエストでエラーが発生しました"
            )

    @nextcord.slash_command(
        description="botの情報やコマンドを表示します"
    )
    async def help(self, ctx):

        creators = []

        for creator in help['owners']:
            creators.append(
                await self.bot.fetch_user(int(creator))
            )

        creators = "".join(
            f"\n`{x}`"
            for x in creators
        )

        commands_list = "".join(
            f"`{help['prefix']}{x}` "
            for x in help['commands_list']
        )

        embed = nextcord.Embed(
            title="情報",
            color=color
        )

        embed.add_field(
            name="作成者",
            value=f"{creators}"
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
