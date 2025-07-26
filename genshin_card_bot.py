import discord
from discord.ext import commands
import aiosqlite
import random
import asyncio
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

# Danh sách thẻ bài Genshin Impact
CARDS = [
    # Thẻ nhân vật
    {"name": "Arlecchino", "type": "character", "power": 90, "element": "Hỏa", "rarity": "Huyền Thoại", "image": "https://genshin.honeyhunterworld.com/img/char/arlecchino_035.webp"},
    {"name": "Diluc", "type": "character", "power": 85, "element": "Hỏa", "rarity": "Huyền Thoại", "image": "https://genshin.honeyhunterworld.com/img/char/diluc_002.webp"},
    {"name": "Keqing", "type": "character", "power": 80, "element": "Lôi", "rarity": "Hiếm", "image": "https://genshin.honeyhunterworld.com/img/char/keqing_007.webp"},
    {"name": "Fischl", "type": "character", "power": 70, "element": "Lôi", "rarity": "Hiếm", "image": "https://genshin.honeyhunterworld.com/img/char/fischl_012.webp"},
    {"name": "Noelle", "type": "character", "power": 65, "element": "Nham", "rarity": "Thường", "image": "https://genshin.honeyhunterworld.com/img/char/noelle_014.webp"},
    {"name": "Barbara", "type": "character", "power": 60, "element": "Thủy", "rarity": "Thường", "image": "https://genshin.honeyhunterworld.com/img/char/barbara_005.webp"},
    # Thẻ hành động
    {"name": "Paimon", "type": "action", "power": 10, "element": "None", "rarity": "Thường", "image": "https://genshin.honeyhunterworld.com/img/char/paimon_099.webp", "effect": "Tăng 10 sát thương cho thẻ nhân vật"},
    {"name": "Tiên Nhảy Tường", "type": "action", "power": 15, "element": "None", "rarity": "Hiếm", "image": "https://genshin.honeyhunterworld.com/img/item/delicious_jade_parcels_510.webp", "effect": "Tăng 15 sát thương cho toàn đội"},
    {"name": "Cộng Hưởng Hỏa", "type": "action", "power": 20, "element": "Hỏa", "rarity": "Hiếm", "image": "https://genshin.honeyhunterworld.com/img/item/pyro_regisvine_302.webp", "effect": "Tăng 20 sát thương nếu thẻ nhân vật là Hỏa"},
    {"name": "Lời Nguyện Gió", "type": "action", "power": 15, "element": "Phong", "rarity": "Hiếm", "image": "https://genshin.honeyhunterworld.com/img/item/anemo_hypostasis_301.webp", "effect": "Chuyển đổi thẻ nhân vật sang nguyên tố Phong"},
]

# Xác suất gacha theo độ hiếm
RARITY_PROBABILITIES = {
    "Huyền Thoại": 0.05,  # 5%
    "Hiếm": 0.25,         # 25%
    "Thường": 0.70        # 70%
}

async def init_db():
    async with aiosqlite.connect("cards.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_cards (
                user_id INTEGER,
                card_name TEXT,
                type TEXT,
                power INTEGER,
                element TEXT,
                rarity TEXT,
                image TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS cooldowns (
                user_id INTEGER,
                last_collect TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS selected_characters (
                user_id INTEGER PRIMARY KEY,
                card_name TEXT
            )
        """)
        await db.commit()

@bot.event
async def on_ready():
    print(f'Đã đăng nhập với tên {bot.user}')
    await init_db()

@bot.command(name="collect", help="Thu thập một thẻ bài ngẫu nhiên (cooldown 24 giờ)")
async def collect(ctx):
    async with aiosqlite.connect("cards.db") as db:
        async with db.execute("SELECT last_collect FROM cooldowns WHERE user_id = ?", (ctx.author.id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                last_collect = datetime.fromisoformat(row[0])
                if datetime.now() < last_collect + timedelta(hours=24):
                    remaining = last_collect + timedelta(hours=24) - datetime.now()
                    await ctx.send(f"{ctx.author.mention}, bạn phải đợi {remaining.seconds // 3600} giờ {remaining.seconds % 3600 // 60} phút để thu thập thẻ mới!")
                    return
            
        # Hệ thống gacha
        rarity = random.choices(
            list(RARITY_PROBABILITIES.keys()),
            weights=list(RARITY_PROBABILITIES.values()),
            k=1
        )[0]
        available_cards = [card for card in CARDS if card["rarity"] == rarity]
        if not available_cards:
            available_cards = CARDS  # Fallback nếu không có thẻ trong độ hiếm
        card = random.choice(available_cards)
        
        await db.execute(
            "INSERT INTO user_cards (user_id, card_name, type, power, element, rarity, image) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (ctx.author.id, card["name"], card["type"], card["power"], card["element"], card["rarity"], card["image"])
        )
        await db.execute(
            "INSERT OR REPLACE INTO cooldowns (user_id, last_collect) VALUES (?, ?)",
            (ctx.author.id, datetime.now().isoformat())
        )
        await db.commit()
        embed = discord.Embed(
            title="Thẻ bài mới!",
            description=f"{ctx.author.mention}, bạn đã thu thập được **{card['name']}**!",
            color=discord.Color.gold()
        )
        embed.add_field(
            name="Thông tin thẻ",
            value=f"Loại: {card['type'].capitalize()}\nSức mạnh: {card['power']}\nNguyên tố: {card['element']}\nĐộ hiếm: {card['rarity']}",
            inline=True
        )
        embed.set_image(url=card["image"])
        await ctx.send(embed=embed)

@bot.command(name="cards", help="Xem bộ sưu tập thẻ bài của bạn")
async def cards(ctx):
    async with aiosqlite.connect("cards.db") as db:
        async with db.execute("SELECT card_name, type, power, element, rarity, image FROM user_cards WHERE user_id = ?", (ctx.author.id,)) as cursor:
            cards = await cursor.fetchall()
            if not cards:
                await ctx.send(f"{ctx.author.mention}, bạn chưa có thẻ bài nào! Dùng `/collect` để thu thập.")
                return
            embed = discord.Embed(title=f"Bộ sưu tập của {ctx.author.name}", color=discord.Color.blue())
            for card in cards:
                embed.add_field(
                    name=card[0],  # Fixed: Changed 'nameirty' to 'name=card[0]'
                    value=f"Loại: {card[1].capitalize()}\nSức mạnh: {card[2]}\nNguyên tố: {card[3]}\nĐộ hiếm: {card[4]}",
                    inline=True
                )
            embed.set_thumbnail(url=cards[0][5])  # Hiển thị hình ảnh thẻ đầu tiên
            await ctx.send(embed=embed)

@bot.command(name="select_character", help="Chọn thẻ nhân vật để chiến đấu")
async def select_character(ctx, *, card_name):
    async with aiosqlite.connect("cards.db") as db:
        async with db.execute("SELECT card_name, type FROM user_cards WHERE user_id = ? AND card_name = ? AND type = 'character'", (ctx.author.id, card_name)) as cursor:
            card = await cursor.fetchone()
            if not card:
                await ctx.send(f"{ctx.author.mention}, bạn không sở hữu thẻ nhân vật **{card_name}** hoặc thẻ không phải nhân vật!")
                return
            await db.execute(
                "INSERT OR REPLACE INTO selected_characters (user_id, card_name) VALUES (?, ?)",
                (ctx.author.id, card_name)
            )
            await db.commit()
            await ctx.send(f"{ctx.author.mention}, bạn đã chọn **{card_name}** làm thẻ nhân vật chiến đấu!")

@bot.command(name="battle", help="Thách đấu người chơi khác với thẻ nhân vật đã chọn")
async def battle(ctx, opponent: discord.Member):
    if opponent == ctx.author:
        await ctx.send("Bạn không thể thách đấu chính mình!")
        return
    if opponent.bot:
        await ctx.send("Bạn không thể thách đấu bot!")
        return

    async with aiosqlite.connect("cards.db") as db:
        async with db.execute("SELECT card_name, type, power, element, image FROM user_cards WHERE user_id = ? AND card_name = (SELECT card_name FROM selected_characters WHERE user_id = ?)", (ctx.author.id, ctx.author.id)) as cursor:
            player_card = await cursor.fetchone()
        async with db.execute("SELECT card_name, type, power, element, image FROM user_cards WHERE user_id = ? AND card_name = (SELECT card_name FROM selected_characters WHERE user_id = ?)", (opponent.id, opponent.id)) as cursor:
            opponent_card = await cursor.fetchone()

        if not player_card:
            await ctx.send(f"{ctx.author.mention}, bạn chưa chọn thẻ nhân vật! Dùng `/select_character <tên thẻ>` để chọn.")
            return
        if not opponent_card:
            await ctx.send(f"{opponent.mention}, chưa chọn thẻ nhân vật! Dùng `/select_character <tên thẻ>` để chọn.")
            return

        # Tính toán sát thương với xúc xắc và thẻ hành động
        player_dice = random.randint(1, 8)
        opponent_dice = random.randint(1, 8)
        player_power = player_card[2]
        opponent_power = opponent_card[2]

        # Chọn thẻ hành động ngẫu nhiên từ bộ sưu tập
        async with db.execute("SELECT card_name, power, element, effect FROM user_cards WHERE user_id = ? AND type = 'action' ORDER BY RANDOM() LIMIT 1", (ctx.author.id,)) as cursor:
            player_action = await cursor.fetchone()
        async with db.execute("SELECT card_name, power, element, effect FROM user_cards WHERE user_id = ? AND type = 'action' ORDER BY RANDOM() LIMIT 1", (opponent.id,)) as cursor:
            opponent_action = await cursor.fetchone()

        # Áp dụng hiệu ứng thẻ hành động
        if player_action:
            if "Tăng" in player_action[3] and (player_action[2] == "None" or player_action[2] == player_card[3]):
                player_power += player_action[1]
            if "Chuyển đổi" in player_action[3]:
                player_card = list(player_card)
                player_card[3] = player_action[2]  # Thay đổi nguyên tố

        if opponent_action:
            if "Tăng" in opponent_action[3] and (opponent_action[2] == "None" or opponent_action[2] == opponent_card[3]):
                opponent_power += opponent_action[1]
            if "Chuyển đổi" in opponent_action[3]:
                opponent_card = list(opponent_card)
                opponent_card[3] = opponent_action[2]

        # Phản ứng nguyên tố
        if player_card[3] == "Hỏa" and opponent_card[3] == "Lôi":
            player_power += 10  # Phản ứng Quá Tải
        elif opponent_card[3] == "Hỏa" and player_card[3] == "Lôi":
            opponent_power += 10

        player_total = player_power + player_dice
        opponent_total = opponent_power + opponent_dice

        embed = discord.Embed(title="Trận chiến Thất Thánh Triệu Hồi!", color=discord.Color.red())
        embed.add_field(
            name=f"{ctx.author.name}",
            value=f"Thẻ: **{player_card[0]}** (Sức mạnh: {player_card[2]}, Nguyên tố: {player_card[3]})\nXúc xắc: +{player_dice}\nHành động: {player_action[0] if player_action else 'Không'}\nTổng: {player_total}",
            inline=True
        )
        embed.add_field(
            name=f"{opponent.name}",
            value=f"Thẻ: **{opponent_card[0]}** (Sức mạnh: {opponent_card[2]}, Nguyên tố: {opponent_card[3]})\nXúc xắc: +{opponent_dice}\nHành động: {opponent_action[0] if opponent_action else 'Không'}\nTổng: {opponent_total}",
            inline=True
        )
        embed.set_thumbnail(url=player_card[4])
        embed.set_image(url=opponent_card[4])

        if player_total > opponent_total:
            embed.add_field(name="Kết quả", value=f"{ctx.author.mention} chiến thắng!", inline=False)
        elif player_total < opponent_total:
            embed.add_field(name="Kết quả", value=f"{opponent.mention} chiến thắng!", inline=False)
        else:
            embed.add_field(name="Kết quả", value="Hòa!", inline=False)

        await ctx.send(embed=embed)

bot.run(TOKEN)