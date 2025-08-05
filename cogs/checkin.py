# cogs/checkin.py
import discord
from discord import app_commands
from discord.ext import commands
import json
import time
import os
import random

class Checkin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.checkin_data_file = 'checkin_data.json'
        self.currency_data_file = 'currency_data.json'
        self.checkin_data = self.load_checkin_data()
        self.currency_data = self.load_currency_data()
        self.token_range = self.checkin_data.get('token_range', {'min': 1, 'max': 3})

    def load_checkin_data(self):
        if os.path.exists(self.checkin_data_file):
            with open(self.checkin_data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def save_checkin_data(self):
        with open(self.checkin_data_file, 'w', encoding='utf-8') as f:
            json.dump(self.checkin_data, f, indent=4)

    def load_currency_data(self):
        if os.path.exists(self.currency_data_file):
            with open(self.currency_data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def save_currency_data(self):
        with open(self.currency_data_file, 'w', encoding='utf-8') as f:
            json.dump(self.currency_data, f, indent=4)

    @app_commands.command(name="簽到", description="每日簽到，每24小時可簽到一次並領取代幣")
    async def checkin_command(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        current_time = int(time.time())

        if user_id in self.checkin_data and current_time - self.checkin_data[user_id] < 86400:
            remaining_time = 86400 - (current_time - self.checkin_data[user_id])
            hours = remaining_time // 3600
            minutes = (remaining_time % 3600) // 60
            await interaction.response.send_message(f"{interaction.user.mention}，你已經簽到過了！請在 {hours} 小時 {minutes} 分鐘後再來。", ephemeral=True)
        else:
            # 更新簽到時間
            self.checkin_data[user_id] = current_time
            self.save_checkin_data()

            # 隨機發放代幣
            tokens_to_add = random.randint(self.token_range['min'], self.token_range['max'])
            self.currency_data[user_id] = self.currency_data.get(user_id, 0) + tokens_to_add
            self.save_currency_data()

            await interaction.response.send_message(f"恭喜你，{interaction.user.mention}！你已成功簽到並獲得 {tokens_to_add} 枚代幣！")

    @app_commands.command(name="簽到代幣數量", description="設定簽到時可獲得的代幣數量範圍")
    @app_commands.describe(min_tokens="最少獲得的代幣數量", max_tokens="最多獲得的代幣數量")
    @commands.has_permissions(manage_guild=True)
    async def set_checkin_tokens(self, interaction: discord.Interaction, min_tokens: int, max_tokens: int):
        if min_tokens <= 0 or max_tokens <= 0:
            await interaction.response.send_message("代幣數量必須大於 0。", ephemeral=True)
            return
        if min_tokens > max_tokens:
            await interaction.response.send_message("最少數量不能大於最多數量。", ephemeral=True)
            return

        self.token_range = {'min': min_tokens, 'max': max_tokens}
        self.checkin_data['token_range'] = self.token_range
        self.save_checkin_data()
        
        await interaction.response.send_message(f"已將簽到代幣數量設定為 `{min_tokens}` 到 `{max_tokens}`。", ephemeral=True)
    
async def setup(bot):
    await bot.add_cog(Checkin(bot))
