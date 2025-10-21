# main.py
import os, io, random, string, asyncio
from flask import Flask
from threading import Thread
from PIL import Image, ImageDraw, ImageFont
import discord
from discord.ext import commands

# ================== FLASK KEEP-ALIVE ==================
app = Flask('')

@app.route('/')
def home():
    return "✅ Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# ================== DISCORD BOT SETUP ==================
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ================== TẠO CAPTCHA ==================
def generate_captcha():
    text = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    img = Image.new('RGB', (200, 80), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    font = ImageFont.load_default()
    d.text((50, 25), text, font=font, fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return text, buf

# ================== SỰ KIỆN KHI BOT ONLINE ==================
@bot.event
async def on_ready():
    print(f"✅ Bot đã đăng nhập: {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"📁 Slash lệnh đã đồng bộ ({len(synced)})")
    except Exception as e:
        print(f"Lỗi sync slash: {e}")

# ================== KHI NGƯỜI MỚI THAM GIA ==================
@bot.event
async def on_member_join(member):
    channel = discord.utils.get(member.guild.text_channels, name="verify")
    if channel:
        await channel.send(
            f"👋 Chào {member.mention}! Vui lòng gõ `/verify` hoặc `!verify` để xác minh nhé."
        )

# ================== LỆNH PREFIX ==================
@bot.command()
async def verify(ctx):
    await start_verify(ctx.author, ctx.guild, prefix=True)

# ================== LỆNH SLASH ==================
@bot.tree.command(name="verify", description="Xác minh bạn không phải bot")
async def verify_slash(interaction: discord.Interaction):
    await interaction.response.send_message("📩 Kiểm tra DM để xác minh!", ephemeral=True)
    await start_verify(interaction.user, interaction.guild, prefix=False)

# ================== HÀM CHÍNH XÁC MINH ==================
async def start_verify(user, guild, prefix=False):
    # tạo hoặc tìm role Verified
    verified_role = discord.utils.get(guild.roles, name="✅ Verified")
    if not verified_role:
        verified_role = await guild.create_role(name="✅ Verified")

    # tạo captcha
    captcha_text, captcha_img = generate_captcha()
    file = discord.File(fp=captcha_img, filename="captcha.png")

    try:
        await user.send("🔒 Nhập lại chữ trong ảnh để xác minh:", file=file)
    except discord.Forbidden:
        msg = "❌ Bot không thể gửi DM. Hãy bật tin nhắn riêng trong server!"
        if prefix:
            ch = discord.utils.get(guild.text_channels, name="verify")
            if ch:
                await ch.send(f"{user.mention} {msg}")
        return

    def check_msg(m):
        return m.author == user and isinstance(m.channel, discord.DMChannel)

    try:
        msg = await bot.wait_for("message", check=check_msg, timeout=60)
        if msg.content.strip().upper() == captcha_text:
            await user.send("✅ Chính xác! Bạn đã được xác minh.")
            member = guild.get_member(user.id)
            if member:
                await member.add_roles(verified_role)
        else:
            await user.send("❌ Sai captcha. Hãy thử lại `/verify`.")
    except asyncio.TimeoutError:
        await user.send("⏰ Hết thời gian. Gõ `/verify` để thử lại.")

# ================== CHẠY BOT ==================
if __name__ == "__main__":
    keep_alive()  # chạy Flask giữ bot sống
    TOKEN = os.getenv("TOKEN")
    if not TOKEN:
        print("❌ Thiếu TOKEN! Vào Secrets thêm key=TOKEN value=<token bot>")
    else:
        bot.run(TOKEN)

