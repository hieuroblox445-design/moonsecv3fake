from flask import Flask, render_template
from threading import Thread
import discord
from discord.ext import commands
from discord import app_commands
import os
import asyncio
import datetime
import time

# Flask app for keeping bot alive
app = Flask(__name__)

@app.route('/')
def index():
    return {
        "status": "online",
        "bot": "Discord Vote Bot",
        "uptime": f"{int(time.time() - start_time)} seconds",
        "timestamp": datetime.datetime.now().isoformat()
    }

@app.route('/health')
def health():
    return "OK", 200

@app.route('/status')
def status():
    return {
        "status": "running",
        "server": "Render",
        "bot_ready": bot.is_ready() if 'bot' in globals() else False
    }

def run_flask():
    app.run(host='0.0.0.0', port=8080)

# Discord Bot
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# Lưu trữ dữ liệu vote
vote_data = {}
start_time = time.time()

class VoteView(discord.ui.View):
    def __init__(self, vote_id, options, timeout=300):
        super().__init__(timeout=timeout)
        self.vote_id = vote_id
        self.options = options
        
        # Tạo buttons cho mỗi option
        for i, option in enumerate(options):
            self.add_item(VoteButton(option, i, vote_id))

class VoteButton(discord.ui.Button):
    def __init__(self, option, index, vote_id):
        super().__init__(
            label=option[:80],  # Giới hạn độ dài label
            style=discord.ButtonStyle.primary,
            custom_id=f"vote_{vote_id}_{index}"
        )
        self.option = option
        self.index = index
        self.vote_id = vote_id
    
    async def callback(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        
        # Kiểm tra nếu vote đã kết thúc
        if self.vote_id not in vote_data:
            await interaction.response.send_message(" Vote này đã kết thúc!", ephemeral=True)
            return
        
        vote_info = vote_data[self.vote_id]
        
        # Kiểm tra nếu user đã vote
        if user_id in vote_info['voters']:
            await interaction.response.send_message(" Bạn đã vote rồi!", ephemeral=True)
            return
        
        # Ghi nhận vote
        vote_info['votes'][self.index] += 1
        vote_info['voters'][user_id] = self.index
        
        await interaction.response.send_message(f" Bạn đã vote cho: **{self.option}**", ephemeral=True)
        
        # Cập nhật embed
        await update_vote_embed(interaction.message, vote_info)

async def update_vote_embed(message, vote_info):
    try:
        embed = message.embeds[0]
        
        # Tính tổng số vote
        total_votes = sum(vote_info['votes'])
        
        # Cập nhật description
        description = f"**{vote_info['question']}**\n\n"
        
        for i, option in enumerate(vote_info['options']):
            votes = vote_info['votes'][i]
            percentage = (votes / total_votes * 100) if total_votes > 0 else 0
            
            # Tạo thanh progress bar
            bars = int(percentage / 10)
            progress_bar = "█" * bars + "░" * (10 - bars)
            
            description += f"**{option}**\n"
            description += f"`{progress_bar}` {votes} votes ({percentage:.1f}%)\n\n"
        
        description += f"**Tổng số vote:** {total_votes}"
        description += f"\n**Kết thúc:** <t:{int(vote_info['end_time'].timestamp())}:R>"
        
        embed.description = description
        await message.edit(embed=embed)
    except Exception as e:
        print(f"Lỗi cập nhật embed: {e}")

@bot.event
async def on_ready():
    print(f' {bot.user} đã kết nối thành công!')
    print(f' Số server: {len(bot.guilds)}')
    
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching, 
            name="!vote để tạo vote"
        )
    )
    
    try:
        synced = await bot.tree.sync()
        print(f" Đã đồng bộ {len(synced)} slash command(s)")
    except Exception as e:
        print(f" Lỗi đồng bộ slash commands: {e}")

@bot.command(name='vote')
async def create_vote(ctx, *, question_and_options: str = None):
    """Tạo vote mới với cú pháp: !vote "Câu hỏi" "Option 1" "Option 2" ..."""
    if not question_and_options:
        embed = discord.Embed(
            title=" Thiếu thông tin",
            description="**Cú pháp:** `!vote \"Câu hỏi\" \"Option 1\" \"Option 2\" ...`\n\n**Ví dụ:**\n`!vote \"Màu yêu thích?\" \"Đỏ\" \"Xanh\" \"Vàng\"`",
            color=0xff0000
        )
        await ctx.send(embed=embed)
        return
    
    try:
        parts = parse_quoted_strings(question_and_options)
        if len(parts) < 3:
            await ctx.send(" Cần ít nhất 1 câu hỏi và 2 options!")
            return
        
        question = parts[0]
        options = parts[1:]
        
        if len(options) > 10:
            await ctx.send(" Tối đa 10 options!")
            return
        
    except Exception as e:
        await ctx.send(f" Lỗi cú pháp: {str(e)}")
        return
    
    # Tạo vote ID
    vote_id = f"{ctx.message.id}_{ctx.channel.id}"
    
    # Lưu thông tin vote
    vote_data[vote_id] = {
        'question': question,
        'options': options,
        'votes': [0] * len(options),
        'voters': {},
        'creator': ctx.author.id,
        'end_time': datetime.datetime.now() + datetime.timedelta(minutes=10),
        'message_id': None
    }
    
    # Tạo embed
    embed = discord.Embed(
        title="🗳️ BỎ PHIẾU",
        color=0x00ff00,
        timestamp=datetime.datetime.now()
    )
    
    description = f"**{question}**\n\n"
    for option in options:
        description += f"**{option}**\n`░░░░░░░░░░` 0 votes (0.0%)\n\n"
    
    description += f"**Tổng số vote:** 0"
    description += f"\n**Kết thúc:** <t:{int(vote_data[vote_id]['end_time'].timestamp())}:R>"
    
    embed.description = description
    embed.set_footer(text=f"Tạo bởi {ctx.author.display_name}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
    
    # Gửi message với buttons
    view = VoteView(vote_id, options, timeout=600)
    message = await ctx.send(embed=embed, view=view)
    
    # Lưu message ID
    vote_data[vote_id]['message_id'] = message.id

def parse_quoted_strings(text):
    """Parse các chuỗi trong dấu ngoặc kép"""
    parts = []
    current = ""
    in_quote = False
    
    for char in text:
        if char == '"':
            if in_quote:
                if current.strip():
                    parts.append(current.strip())
                current = ""
            in_quote = not in_quote
        elif in_quote:
            current += char
        elif char == " " and not current:
            continue
        else:
            current += char
    
    if current.strip():
        parts.append(current.strip())
    
    return parts

@bot.tree.command(name="vote", description="Tạo vote mới bằng slash command")
@app_commands.describe(
    question="Câu hỏi vote",
    option1="Option 1",
    option2="Option 2",
    option3="Option 3 (tùy chọn)",
    option4="Option 4 (tùy chọn)",
    option5="Option 5 (tùy chọn)"
)
async def slash_vote(
    interaction: discord.Interaction,
    question: str,
    option1: str,
    option2: str,
    option3: str = None,
    option4: str = None,
    option5: str = None
):
    """Slash command tạo vote"""
    options = [option1, option2]
    if option3: options.append(option3)
    if option4: options.append(option4)
    if option5: options.append(option5)
    
    # Tạo vote ID
    vote_id = f"{interaction.id}_{interaction.channel_id}"
    
    # Lưu thông tin vote
    vote_data[vote_id] = {
        'question': question,
        'options': options,
        'votes': [0] * len(options),
        'voters': {},
        'creator': interaction.user.id,
        'end_time': datetime.datetime.now() + datetime.timedelta(minutes=10),
        'message_id': None
    }
    
    # Tạo embed
    embed = discord.Embed(
        title="🗳️ BỎ PHIẾU",
        color=0x00ff00,
        timestamp=datetime.datetime.now()
    )
    
    description = f"**{question}**\n\n"
    for option in options:
        description += f"**{option}**\n`░░░░░░░░░░` 0 votes (0.0%)\n\n"
    
    description += f"**Tổng số vote:** 0"
    description += f"\n**Kết thúc:** <t:{int(vote_data[vote_id]['end_time'].timestamp())}:R>"
    
    embed.description = description
    embed.set_footer(text=f"Tạo bởi {interaction.user.display_name}", icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
    
    # Gửi message với buttons
    view = VoteView(vote_id, options, timeout=600)
    await interaction.response.send_message(embed=embed, view=view)
    
    # Lưu message ID
    message = await interaction.original_response()
    vote_data[vote_id]['message_id'] = message.id

@bot.command(name='quickvote')
async def quick_vote(ctx, *, question: str):
    """Tạo vote nhanh với 2 options Yes/No"""
    options = ["✅ Yes", "❌ No"]
    
    vote_id = f"{ctx.message.id}_{ctx.channel.id}"
    
    vote_data[vote_id] = {
        'question': question,
        'options': options,
        'votes': [0] * len(options),
        'voters': {},
        'creator': ctx.author.id,
        'end_time': datetime.datetime.now() + datetime.timedelta(minutes=5),
        'message_id': None
    }
    
    embed = discord.Embed(
        title="🗳️ VOTE NHANH",
        color=0xffff00,
        timestamp=datetime.datetime.now()
    )
    
    description = f"**{question}**\n\n"
    for option in options:
        description += f"**{option}**\n`░░░░░░░░░░` 0 votes (0.0%)\n\n"
    
    description += f"**Tổng số vote:** 0"
    description += f"\n**Kết thúc:** <t:{int(vote_data[vote_id]['end_time'].timestamp())}:R>"
    
    embed.description = description
    embed.set_footer(text=f"Tạo bởi {ctx.author.display_name}")
    
    view = VoteView(vote_id, options, timeout=300)
    message = await ctx.send(embed=embed, view=view)
    vote_data[vote_id]['message_id'] = message.id

@bot.command(name='endvote')
async def end_vote(ctx):
    """Kết thúc vote sớm (chỉ người tạo vote)"""
    vote_id = None
    for vid, vote_info in vote_data.items():
        if str(ctx.channel.id) in vid and vote_info['creator'] == ctx.author.id:
            vote_id = vid
            break
    
    if not vote_id:
        await ctx.send(" Bạn không có vote nào đang diễn ra trong channel này!")
        return
    
    vote_info = vote_data[vote_id]
    total_votes = sum(vote_info['votes'])
    
    embed = discord.Embed(
        title="🏁 KẾT QUẢ VOTE CUỐI CÙNG",
        color=0xffa500,
        timestamp=datetime.datetime.now()
    )
    
    description = f"**{vote_info['question']}**\n\n"
    
    for i, option in enumerate(vote_info['options']):
        votes = vote_info['votes'][i]
        percentage = (votes / total_votes * 100) if total_votes > 0 else 0
        
        bars = int(percentage / 10)
        progress_bar = "█" * bars + "░" * (10 - bars)
        
        description += f"**{option}**\n"
        description += f"`{progress_bar}` {votes} votes ({percentage:.1f}%)\n\n"
    
    description += f"**Tổng số vote:** {total_votes}"
    
    embed.description = description
    embed.set_footer(text="Đã kết thúc sớm")
    
    await ctx.send(embed=embed)
    
    # Xóa vote khỏi memory
    if vote_id in vote_data:
        del vote_data[vote_id]

@bot.command(name='ping')
async def ping(ctx):
    """Kiểm tra độ trễ"""
    latency = round(bot.latency * 1000)
    embed = discord.Embed(
        title=" PING!",
        description=f"**Độ trễ:** {latency}ms\n**Uptime:** {int(time.time() - start_time)} giây",
        color=0x00ff00
    )
    await ctx.send(embed=embed)

@bot.command(name='helpvote')
async def help_vote(ctx):
    """Hướng dẫn sử dụng bot vote"""
    embed = discord.Embed(
        title=" BOT VOTE - HƯỚNG DẪN",
        color=0x0099ff,
        description="Bot tạo vote với buttons interactive"
    )
    
    embed.add_field(
        name=" LỆNH CHÍNH",
        value="""`!vote "Câu hỏi" "Option1" "Option2" ...` - Tạo vote mới
`/vote` - Tạo vote bằng slash command
`!quickvote <câu hỏi>` - Vote nhanh Yes/No
`!endvote` - Kết thúc vote sớm
`!ping` - Kiểm tra độ trễ
`!helpvote` - Hiển thị hướng dẫn""",
        inline=False
    )
    
    embed.add_field(
        name=" TÍNH NĂNG",
        value="""• Buttons interactive
• Progress bar trực quan
• Chống vote nhiều lần
• Timestamp kết thúc
• Slash command support""",
        inline=False
    )
    
    embed.add_field(
        name="📊 VÍ DỤ",
        value="""`!vote "Màu yêu thích?" "Đỏ" "Xanh" "Vàng"`
`!quickvote Có nên update server không?`
`/vote question:"Ăn gì trưa nay?" option1:"Phở" option2:"Cơm" option3:"Bún`""",
        inline=False
    )
    
    await ctx.send(embed=embed)

@bot.event
async def on_view_timeout(view: VoteView):
    """Xử lý khi vote timeout"""
    if view.vote_id in vote_data:
        # Có thể gửi kết quả cuối cùng ở đây
        print(f"Vote {view.vote_id} đã timeout")
        # Giữ vote trong memory để xem kết quả

# Khởi chạy Flask trong thread
flask_thread = Thread(target=run_flask, daemon=True)
flask_thread.start()

# Chạy bot
if __name__ == "__main__":
    token = os.environ.get('TOKEN')
    if not token:
        print(" Lỗi: TOKEN không được tìm thấy!")
        exit(1)
    
    print("🚀 Đang khởi động Discord Vote Bot...")
    print("🌐 Flask server đang chạy trên port 8080")
    bot.run(token)
