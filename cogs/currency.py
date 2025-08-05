# cogs/currency.py
import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from typing import Optional

# 數據檔案
CURRENCY_DATA_FILE = 'currency.json'
CURRENCY_CONFIG_FILE = 'currency_config.json'

class Currency(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.currency_data_file = CURRENCY_DATA_FILE
        self.currency_config_file = CURRENCY_CONFIG_FILE
        self.config = self._load_currency_config()

    def _load_currency_data(self):
        """從檔案載入代幣數據。"""
        if os.path.exists(self.currency_data_file):
            with open(self.currency_data_file, 'r', encoding='utf-8') as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return {}
        return {}

    def _save_currency_data(self, data):
        """將代幣數據儲存到檔案。"""
        with open(self.currency_data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def _load_currency_config(self):
        """從檔案載入代幣設定，若無則使用預設值。"""
        default_config = {
            "transfer_fee_percentage": 5  # 預設轉帳手續費為 5%
        }
        if os.path.exists(self.currency_config_file):
            with open(self.currency_config_file, 'r', encoding='utf-8') as f:
                try:
                    return {**default_config, **json.load(f)}
                except json.JSONDecodeError:
                    return default_config
        return default_config
    
    def _save_currency_config(self):
        """將代幣設定儲存到檔案。"""
        with open(self.currency_config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=4, ensure_ascii=False)

    async def get_user_money(self, user_id: int) -> int:
        """獲取指定用戶的代幣數量。"""
        currency_data = self._load_currency_data()
        return currency_data.get(str(user_id), 0)

    async def deduct_user_money(self, user_id: int, amount: int) -> bool:
        """從指定用戶的代幣中扣除數量。"""
        currency_data = self._load_currency_data()
        user_id_str = str(user_id)
        current_money = currency_data.get(user_id_str, 0)
        
        if current_money < amount:
            return False
        
        currency_data[user_id_str] = current_money - amount
        self._save_currency_data(currency_data)
        return True

    async def add_user_money(self, user_id: int, amount: int):
        """為指定用戶增加代幣數量。"""
        currency_data = self._load_currency_data()
        user_id_str = str(user_id)
        current_money = currency_data.get(user_id_str, 0)
        
        currency_data[user_id_str] = current_money + amount
        self._save_currency_data(currency_data)

    @app_commands.command(name="查詢代幣", description="查詢成員的代幣數量")
    @app_commands.describe(member="要查詢的成員")
    async def get_currency_command(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.defer()
        amount = await self.get_user_money(member.id)
        await interaction.followup.send(f"{member.display_name} 目前有 {amount} 個代幣。")

    @app_commands.command(name="修改代幣", description="修改指定成員的代幣數量")
    @app_commands.describe(
        member="要修改的成員",
        amount="代幣數量 (正數為增加，負數為減少)"
    )
    @commands.has_permissions(manage_guild=True)
    async def modify_currency_command(self, interaction: discord.Interaction, member: discord.Member, amount: int):
        await interaction.response.defer(ephemeral=True)
        await self.add_user_money(member.id, amount)
        new_amount = await self.get_user_money(member.id)
        await interaction.followup.send(f"已將 {member.display_name} 的代幣修改為 {new_amount}。", ephemeral=True)

    @app_commands.command(name="轉帳", description="將代幣轉帳給其他成員")
    @app_commands.describe(
        member="轉帳的目標成員",
        amount="轉帳的數量"
    )
    async def transfer_command(self, interaction: discord.Interaction, member: discord.Member, amount: int):
        if amount <= 0:
            await interaction.response.send_message("轉帳金額必須大於零。", ephemeral=True)
            return

        if member.bot:
            await interaction.response.send_message("你不能轉帳給機器人！", ephemeral=True)
            return

        if member.id == interaction.user.id:
            await interaction.response.send_message("你不能轉帳給自己。", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        sender_money = await self.get_user_money(interaction.user.id)
        
        # 轉帳手續費計算
        fee_percentage = self.config.get("transfer_fee_percentage", 5)
        fee = int(amount * (fee_percentage / 100))
        total_deduct_amount = amount + fee

        if sender_money < total_deduct_amount:
            await interaction.followup.send(f"您的代幣不足。您需要 {total_deduct_amount} 個代幣（含手續費），但您只有 {sender_money} 個。", ephemeral=True)
            return

        # 執行轉帳
        await self.deduct_user_money(interaction.user.id, total_deduct_amount)
        await self.add_user_money(member.id, amount)
        
        sender_money_new = await self.get_user_money(interaction.user.id)
        receiver_money_new = await self.get_user_money(member.id)

        await interaction.followup.send(
            f"✅ 轉帳成功！您已將 {amount} 個代幣轉給 {member.display_name}。\n"
            f"手續費: {fee} 個代幣。\n"
            f"您目前剩餘 {sender_money_new} 個代幣。",
            ephemeral=False
        )

    @app_commands.command(name="設置轉帳手續費", description="設定轉帳手續費百分比（需管理權限）")
    @app_commands.describe(percentage="手續費百分比，例如輸入 5 代表 5%")
    @commands.has_permissions(manage_guild=True)
    async def set_transfer_fee_command(self, interaction: discord.Interaction, percentage: int):
        if not 0 <= percentage <= 100:
            await interaction.response.send_message("手續費百分比必須在 0 到 100 之間。", ephemeral=True)
            return
        
        self.config["transfer_fee_percentage"] = percentage
        self._save_currency_config()
        await interaction.response.send_message(f"✅ 轉帳手續費已成功設定為 **{percentage}%**。", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Currency(bot))