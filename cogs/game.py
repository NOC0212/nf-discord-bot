import discord
from discord.ext import commands
from discord import app_commands
import random
from typing import Literal

# 新增一個用於處理猜測輸入的 Modal
class GuessModal(discord.ui.Modal):
    def __init__(self, game_cog, digits: int):
        super().__init__(title=f"猜測你的{digits}位數字")
        self.game_cog = game_cog
        self.digits = digits
        
        self.guess_input = discord.ui.TextInput(
            label=f"請輸入一個不重複的{digits}位數字",
            placeholder=f"例如：{''.join(map(str, range(digits)))}",
            max_length=digits,
            min_length=digits,
        )
        self.add_item(self.guess_input)

    async def on_submit(self, interaction: discord.Interaction):
        user_id_str = str(interaction.user.id)
        if user_id_str not in self.game_cog.games:
            await interaction.response.send_message("請先使用 `/開始遊戲` 指令來開始一局新的遊戲。", ephemeral=True)
            return

        secret_number = self.game_cog.games[user_id_str]["secret"]
        attempts = self.game_cog.games[user_id_str]["attempts"]
        guess = self.guess_input.value
        digits = self.digits

        if not guess.isdigit() or len(set(guess)) != digits or len(guess) != digits:
            await interaction.response.send_message(
                f"輸入格式不正確！請輸入一個不重複的{digits}位數字。",
                ephemeral=True
            )
            return

        # 遊戲邏輯：計算 A 和 B
        a = sum(1 for i in range(digits) if guess[i] == secret_number[i])
        b = sum(1 for digit in guess if digit in secret_number) - a
        
        attempts += 1
        self.game_cog.games[user_id_str]["attempts"] = attempts

        if a == digits:
            # 猜對了！
            response = f"恭喜你！🎉 你用 {attempts} 次猜對了數字 **{secret_number}**！"
            del self.game_cog.games[user_id_str]
            await interaction.response.send_message(response)
        else:
            # 猜錯了
            response = f"你的猜測是：`{guess}`，結果是 **{a}A{b}B**！\n你已經猜了 {attempts} 次。"
            await interaction.response.send_message(response, view=GuessButtonView(self.game_cog))

# 猜數字按鈕
class GuessButton(discord.ui.Button):
    def __init__(self, game_cog):
        super().__init__(label="猜數字", style=discord.ButtonStyle.primary)
        self.game_cog = game_cog

    async def callback(self, interaction: discord.Interaction):
        user_id_str = str(interaction.user.id)
        if user_id_str not in self.game_cog.games:
            await interaction.response.send_message("你還沒有開始遊戲！請先使用 `/開始遊戲`。", ephemeral=True)
            return
        
        digits = self.game_cog.games[user_id_str]["digits"]
        await interaction.response.send_modal(GuessModal(self.game_cog, digits))

class GuessButtonView(discord.ui.View):
    def __init__(self, game_cog):
        super().__init__(timeout=None)
        self.add_item(GuessButton(game_cog))

class Game(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # 儲存遊戲狀態，新增 'digits' 欄位
        # {"user_id": {"secret": "1234", "attempts": 0, "digits": 4}}
        self.games = {}

    def _generate_secret_number(self, digits: int):
        if not 1 <= digits <= 10:
            raise ValueError("數字位數必須在 1 到 10 之間。")
        
        nums = list(range(10))
        random.shuffle(nums)
        secret = "".join(map(str, nums[:digits]))
        return secret

    @app_commands.command(name="開始遊戲", description="開始一局新的 1a2b 數字猜謎遊戲")
    @app_commands.describe(
        digits="選擇要猜測的數字位數 (4或6)"
    )
    async def start_game(self, interaction: discord.Interaction, digits: Literal[4, 6]):
        user_id_str = str(interaction.user.id)
        
        try:
            secret_number = self._generate_secret_number(digits)
        except ValueError as e:
            await interaction.response.send_message(f"錯誤：{e}", ephemeral=True)
            return

        self.games[user_id_str] = {
            "secret": secret_number,
            "attempts": 0,
            "digits": digits
        }
        
        await interaction.response.send_message(
            f"遊戲開始！我已經想好了一個不重複的**{digits}位數字**。請點擊下面的「猜數字」按鈕開始猜測。", 
            ephemeral=True, 
            view=GuessButtonView(self)
        )

    @app_commands.command(name="結束遊戲", description="結束當前的 1a2b 遊戲")
    async def end_game(self, interaction: discord.Interaction):
        user_id_str = str(interaction.user.id)
        if user_id_str in self.games:
            secret_number = self.games.pop(user_id_str)["secret"]
            await interaction.response.send_message(f"遊戲已結束。秘密數字是 **{secret_number}**。", ephemeral=True)
        else:
            await interaction.response.send_message("你目前沒有正在進行的遊戲。", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Game(bot))