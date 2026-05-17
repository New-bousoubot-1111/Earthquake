import json
import requests
import os
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt

from shapely.geometry import MultiPolygon
from fuzzywuzzy import process
from colorama import Fore
from PIL import Image, ImageDraw, ImageFont

from nextcord.ext import commands, tasks
from nextcord import File, Embed

from dateutil import parser

with open('json/config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

GEOJSON_PATH = "./images/japan.geojson"
COASTLINE_PATH = "./images/coastline.geojson"

GEOJSON_REGION_FIELD = "nam_ja"

ALERT_COLORS = {
    "MajorWarning": "#800080",  # 大津波警報
    "Warning": "#ff0000",       # 津波警報
    "Watch": "#ffff00"          # 津波注意報
}


print("GeoJSON読み込み中...")

gdf = gpd.read_file(GEOJSON_PATH)
coastline_gdf = gpd.read_file(COASTLINE_PATH)

print("読み込み完了")


def split_tokyo_islands(gdf):

    tokyo_rows = gdf[gdf["nam_ja"] == "東京都"]

    if len(tokyo_rows) == 0:
        return gdf

    tokyo_idx = tokyo_rows.index[0]
    tokyo_geom = tokyo_rows.iloc[0].geometry

    # 元の東京都削除
    gdf = gdf.drop(tokyo_idx)

    new_rows = []

    if isinstance(tokyo_geom, MultiPolygon):

        for poly in tokyo_geom.geoms:

            centroid = poly.centroid

            lat = centroid.y

            # 小笠原
            if lat < 30:
                region_name = "小笠原諸島"

            # 伊豆諸島
            elif lat < 35:
                region_name = "伊豆諸島"

            # 東京本土
            else:
                region_name = "東京都"

            new_rows.append({
                "nam_ja": region_name,
                "geometry": poly
            })

    else:
        new_rows.append({
            "nam_ja": "東京都",
            "geometry": tokyo_geom
        })

    new_gdf = gpd.GeoDataFrame(
        new_rows,
        crs=gdf.crs
    )

    gdf = gpd.GeoDataFrame(
        pd.concat([gdf, new_gdf], ignore_index=True),
        crs=gdf.crs
    )

    return gdf


gdf = split_tokyo_islands(gdf)

def match_region(area_name, geojson_names):

    if area_name in geojson_names:
        return area_name

    best_match, score = process.extractOne(
        area_name,
        geojson_names
    )

    if score >= 80:
        return best_match

    return None


def create_embed(data):

    alert_levels = {
        "MajorWarning": {
            "title": "大津波警報",
            "color": 0x800080
        },
        "Warning": {
            "title": "津波警報",
            "color": 0xff0000
        },
        "Watch": {
            "title": "津波注意報",
            "color": 0xffff00
        }
    }

    embed_title = "津波情報"
    embed_color = 0x00ff00

    levels_in_data = [
        area.get("grade")
        for area in data.get("areas", [])
    ]

    for level in ["MajorWarning", "Warning", "Watch"]:

        if level in levels_in_data:
            embed_title = alert_levels[level]["title"]
            embed_color = alert_levels[level]["color"]
            break

    embed = Embed(
        title=embed_title,
        color=embed_color
    )

    tsunami_time = parser.parse(data["time"])

    embed.description = (
        f"{embed_title}が発表されました\n"
        f"安全な場所に避難してください"
    )

    embed.add_field(
        name="発表時刻",
        value=tsunami_time.strftime('%Y/%m/%d %H:%M'),
        inline=False
    )

    for area in data.get("areas", []):

        area_name = area["name"]

        max_height = area.get("maxHeight", {})
        first_height = area.get("firstHeight", {})

        arrival = first_height.get("arrivalTime", "不明")
        description = max_height.get("description", "不明")

        if arrival != "不明":

            try:
                arrival = parser.parse(arrival)
                arrival_text = arrival.strftime("%H:%M")

            except:
                arrival_text = "不明"

        else:
            arrival_text = "不明"

        embed.add_field(
            name=area_name,
            value=(
                f"到達予想: {arrival_text}\n"
                f"予想高さ: {description}"
            ),
            inline=False
        )

    return embed


def generate_map(tsunami_alert_areas):

    print("地図生成開始")

    geojson_names = gdf[GEOJSON_REGION_FIELD].tolist()

    gdf["color"] = "#767676"
    coastline_gdf["color"] = "#ffffff"

    tsunami_regions = []


    for area_name, alert_type in tsunami_alert_areas.items():

        matched = match_region(
            area_name,
            geojson_names
        )

        if not matched:
            print(f"一致なし: {area_name}")
            continue

        idx = gdf[
            gdf[GEOJSON_REGION_FIELD] == matched
        ].index[0]

        color = ALERT_COLORS.get(
            alert_type,
            "#ffffff"
        )

        gdf.at[idx, "color"] = color

        tsunami_regions.append((
            gdf.at[idx, "geometry"],
            color
        ))

    coastline_lines = coastline_gdf.boundary

    for coast_idx, coast in coastline_lines.items():

        for region_geom, color in tsunami_regions:

            if coast.intersects(region_geom):

                coastline_gdf.at[
                    coast_idx,
                    "color"
                ] = color

                break

    # =========================
    # 描画
    # =========================

    fig, ax = plt.subplots(figsize=(15, 18))

    fig.patch.set_facecolor("#2a2a2a")
    ax.set_facecolor("#2a2a2a")

    ax.set_xlim([122, 154])
    ax.set_ylim([20, 47])

    # 都道府県
    gdf.plot(
        ax=ax,
        color=gdf["color"],
        edgecolor="#d0d0d0",
        linewidth=0.5,
        zorder=1
    )

    # 海岸線
    coastline_gdf.boundary.plot(
        ax=ax,
        color=coastline_gdf["color"],
        linewidth=3,
        zorder=10
    )

    ax.set_axis_off()

    # 保存
    temp_path = "images/tsunami_temp.png"

    os.makedirs(
        os.path.dirname(temp_path),
        exist_ok=True
    )

    plt.savefig(
        temp_path,
        bbox_inches="tight",
        dpi=300,
        facecolor=fig.get_facecolor()
    )

    plt.close()

    return temp_path


class tsunami(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

        self.sent_ids = set()

        self.cache_file = "json/tsunami_id.json"

        self.load_ids()

    # ---------------------

    def load_ids(self):

        try:

            with open(self.cache_file, "r") as f:
                self.sent_ids = set(json.load(f))

        except:
            self.sent_ids = set()

    # ---------------------

    def save_ids(self):

        with open(self.cache_file, "w") as f:
            json.dump(list(self.sent_ids), f)

    # ---------------------

    @commands.Cog.listener()
    async def on_ready(self):

        print(Fore.BLUE + "|tsunami loaded|" + Fore.RESET)

        self.check_tsunami.start()

    # ---------------------

    @tasks.loop(minutes=1)
    async def check_tsunami(self):

        url = "https://api.p2pquake.net/v2/jma/tsunami"

        response = requests.get(url)

        if response.status_code != 200:
            return

        data = response.json()

        if not data:
            return

        tsunami_channel = self.bot.get_channel(
            int(config["eew_channel"])
        )

        if not tsunami_channel:
            return

        for tsunami_data in data:

            tsunami_id = tsunami_data.get("id")

            if tsunami_id in self.sent_ids:
                continue

            embed = create_embed(tsunami_data)

            tsunami_alert_areas = {

                area["name"]: area.get("grade")

                for area in tsunami_data.get("areas", [])
            }

            if tsunami_alert_areas:

                map_path = generate_map(
                    tsunami_alert_areas
                )

                embed.set_image(
                    url="attachment://tsunami.png"
                )

                with open(map_path, "rb") as file:

                    discord_file = File(
                        file,
                        filename="tsunami.png"
                    )

                    await tsunami_channel.send(
                        embed=embed,
                        file=discord_file
                    )

            else:

                await tsunami_channel.send(
                    embed=embed
                )

            self.sent_ids.add(tsunami_id)

            self.save_ids()

def setup(bot):
    bot.add_cog(tsunami(bot))
