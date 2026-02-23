import discord
from discord.ext import commands
import json
import os

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

DATA_FILE = "votes.json"
LIMIT_FILE = "limits.json"

CATEGORIES = {
    "テイスト": [
        "ガーリー","スポーティ","ネタ系","セクシー",
        "マリン","量産地雷系","清楚系","ギャル系"
    ],
    "形状（上）": [
        "ホルターネック","タンキニ","三角ビキニ","チューブトップ",
        "フリル付きビキニ","ワンショルダー","スポブラタイプ",
        "オフショル風","クロスデザイン","編み上げ"
    ],
    "形状（下）": [
        "パレオ付き","ショートパンツ","サイド紐","レイヤード",
        "ハイウエスト","フリル付き","スカート付き"
    ],
    "色": [
        "ピンク","オレンジ","黒","白",
        "ミントグリーン","水色","ラベンダー","赤","ヒョウ柄"
    ],
    "小物": [
        "サングラス","ビーチバッグ","首輪チョーカー",
        "足首アンクレット","シュシュ","パーカー羽織り",
        "麦わら帽子","日焼け後","太ももベルト"
    ]
}

CATEGORY_NAMES = list(CATEGORIES.keys())

for file in [DATA_FILE, LIMIT_FILE]:
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump({}, f)

def load_json(file):
    with open(file, "r") as f:
        return json.load(f)

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

class VoteView(discord.ui.View):
    def __init__(self, page=0):
        super().__init__(timeout=None)
        self.page = page
        self.create_buttons()

    def create_buttons(self):
        self.clear_items()
        category_name = CATEGORY_NAMES[self.page]
        options = CATEGORIES[category_name]

        for option in options:
            self.add_item(VoteButton(category_name, option))

        if self.page > 0:
            self.add_item(PrevButton())
        if self.page < len(CATEGORY_NAMES) - 1:
            self.add_item(NextButton())

        self.add_item(RemainingButton())

class VoteButton(discord.ui.Button):
    def __init__(self, category, option):
        super().__init__(label=option[:20], style=discord.ButtonStyle.primary)
        self.category = category
        self.option = option

    async def callback(self, interaction: discord.Interaction):
        votes = load_json(DATA_FILE)
        limits = load_json(LIMIT_FILE)
        user_id = str(interaction.user.id)

        if user_id not in limits:
            await interaction.response.send_message("上限未設定です。", ephemeral=True)
            return

        user_limit = limits[user_id]
        user_total = sum(votes.get(user_id, {}).values())

        if user_total + 1 > user_limit:
            await interaction.response.send_message("上限超過です。", ephemeral=True)
            return

        key = f"{self.category}:{self.option}"

        votes.setdefault(user_id, {})
        votes[user_id][key] = votes[user_id].get(key, 0) + 1
        save_json(DATA_FILE, votes)

        await interaction.response.send_message(
            f"【{self.category}】{self.option} に1票入れました！",
            ephemeral=True
        )

class PrevButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="◀", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        view = VoteView(page=self.view.page - 1)
        await interaction.response.edit_message(
            content=f"🏖 水着総選挙\n現在カテゴリー：{CATEGORY_NAMES[self.view.page - 1]}",
            view=view
        )

class NextButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="▶", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        view = VoteView(page=self.view.page + 1)
        await interaction.response.edit_message(
            content=f"🏖 水着総選挙\n現在カテゴリー：{CATEGORY_NAMES[self.view.page + 1]}",
            view=view
        )

class RemainingButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="残り票", style=discord.ButtonStyle.success)

    async def callback(self, interaction: discord.Interaction):
        votes = load_json(DATA_FILE)
        limits = load_json(LIMIT_FILE)
        user_id = str(interaction.user.id)

        if user_id not in limits:
            await interaction.response.send_message("上限未設定です。", ephemeral=True)
            return

        user_limit = limits[user_id]
        user_total = sum(votes.get(user_id, {}).values())

        await interaction.response.send_message(
            f"残り {user_limit-user_total} 票",
            ephemeral=True
        )

@bot.command()
async def startvote(ctx):
    await ctx.send(
        f"🏖 水着総選挙\n現在カテゴリー：{CATEGORY_NAMES[0]}",
        view=VoteView()
    )

@bot.command()
async def setlimit(ctx, member: discord.Member, limit: int):
    limits = load_json(LIMIT_FILE)
    limits[str(member.id)] = limit
    save_json(LIMIT_FILE, limits)
    await ctx.send(f"{member.display_name} の上限を {limit} 票に設定しました。")

@bot.command()
async def result_category(ctx):
    votes = load_json(DATA_FILE)

    if not votes:
        await ctx.send("まだ投票がありません。")
        return

    # 全体集計
    total = {}
    for user in votes:
        for key, count in votes[user].items():
            total[key] = total.get(key, 0) + count

    # カテゴリー別に分解
    category_totals = {}

    for key, count in total.items():
        if ":" in key:
            category, option = key.split(":", 1)
        else:
            category = "未分類"
            option = key

        if category not in category_totals:
            category_totals[category] = {}

        category_totals[category][option] = count

    # メッセージ作成
    message = "🏆 カテゴリー別結果 🏆\n\n"

    for category in category_totals:
        message += f"📌【{category}】\n"

        sorted_options = sorted(
            category_totals[category].items(),
            key=lambda x: x[1],
            reverse=True
        )

        for option, count in sorted_options:
            message += f"  {option} - {count}票\n"

        message += "\n"

    await ctx.send(message)    

import os

TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)
