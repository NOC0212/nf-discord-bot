# cogs/tickets.py

import discord
from discord.ext import commands
from discord import app_commands, ui
import datetime
import json
import os
from typing import Optional, Dict, Any, List

# 設定工單頻道類別的名稱
TICKET_CATEGORY_NAME = "tickets"
TICKET_DATA_FILE = "tickets.json" # 用於保存工單資訊的檔案

class TicketData:
    """用於管理工單數據的類別"""
    def __init__(self):
        self.file_path = TICKET_DATA_FILE
        self.data: Dict[str, Any] = self._load_data()

    def _load_data(self) -> Dict[str, Any]:
        if os.path.exists(self.file_path):
            with open(self.file_path, 'r', encoding='utf-8') as f:
                try:
                    return json.load(f)
                except (json.JSONDecodeError, FileNotFoundError):
                    return {}
        return {}
    
    def _save_data(self):
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=4, ensure_ascii=False)

    def get_guild_data(self, guild_id: int) -> Dict[str, Any]:
        guild_id_str = str(guild_id)
        if guild_id_str not in self.data:
            self.data[guild_id_str] = {
                "active_tickets": {},
                "panel_message_id": None,
                "panel_channel_id": None
            }
        return self.data[guild_id_str]
    
    def add_ticket(self, guild_id: int, ticket_channel_id: int, owner_id: int):
        guild_data = self.get_guild_data(guild_id)
        guild_data["active_tickets"][str(ticket_channel_id)] = {
            "owner_id": str(owner_id),
            "created_at": datetime.datetime.now().timestamp()
        }
        self._save_data()

    def remove_ticket(self, guild_id: int, ticket_channel_id: int):
        guild_data = self.get_guild_data(guild_id)
        guild_data["active_tickets"].pop(str(ticket_channel_id), None)
        self._save_data()

class TicketPanel(ui.View):
    """使用者點擊後建立工單的按鈕"""
    def __init__(self, bot, ticket_data: TicketData):
        super().__init__(timeout=None)
        self.bot = bot
        self.ticket_data = ticket_data

    @ui.button(label="建立工單", style=discord.ButtonStyle.secondary, emoji="✉️", custom_id="create_ticket_button")
    async def create_ticket_button(self, interaction: discord.Interaction, button: ui.Button):
        guild = interaction.guild
        owner = interaction.user

        guild_data = self.ticket_data.get_guild_data(guild.id)
        active_tickets = guild_data["active_tickets"]
        
        # 檢查使用者是否已經有開啟中的工單
        for ticket_id, ticket_info in active_tickets.items():
            if str(owner.id) == ticket_info["owner_id"]:
                try:
                    existing_channel = guild.get_channel(int(ticket_id))
                    if existing_channel:
                        await interaction.response.send_message(f"您已經有一個開啟中的工單：{existing_channel.mention}，請勿重複建立。", ephemeral=True)
                        return
                except (ValueError, TypeError):
                    pass

        # 尋找或建立工單類別
        ticket_category = discord.utils.get(guild.categories, name=TICKET_CATEGORY_NAME)
        if not ticket_category:
            try:
                ticket_category = await guild.create_category(TICKET_CATEGORY_NAME)
            except discord.Forbidden:
                await interaction.response.send_message("我沒有足夠的權限來建立工單類別，請檢查我的權限。", ephemeral=True)
                return
        
        # 覆寫權限，確保工單只有創建者和管理員可見
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            owner: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, attach_files=True)
        }
        
        manage_channels_roles = [role for role in guild.roles if role.permissions.manage_channels]
        for role in manage_channels_roles:
            overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

        try:
            ticket_channel = await guild.create_text_channel(
                f'ticket-{owner.name}',
                category=ticket_category,
                overwrites=overwrites
            )
            
            # 發送工單歡迎訊息
            ticket_embed = discord.Embed(
                title=f"工單已開啟",
                description="請在此描述您的問題。管理員將盡快回覆您。",
                color=discord.Color.green()
            )
            ticket_embed.add_field(name="工單創建者", value=owner.mention, inline=True)
            ticket_embed.add_field(name="工單編號", value=f"#{ticket_channel.name}", inline=True)
            ticket_embed.set_footer(text="要關閉此工單，請點擊下方的按鈕。")
            
            # 傳送工單歡迎訊息，並附加關閉按鈕
            view = TicketCloseView(self.bot, self.ticket_data)
            await ticket_channel.send(f"歡迎 {owner.mention}。", embed=ticket_embed, view=view)
            
            self.ticket_data.add_ticket(guild.id, ticket_channel.id, owner.id)
            
            await interaction.response.send_message(f"您的工單已建立：{ticket_channel.mention}", ephemeral=True)
            
        except discord.Forbidden:
            await interaction.response.send_message("我沒有足夠的權限來建立工單頻道，請檢查我的權限。", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"建立工單時發生未知錯誤：{e}", ephemeral=True)


class TicketCloseView(ui.View):
    """用於關閉工單的按鈕"""
    def __init__(self, bot, ticket_data: TicketData):
        super().__init__(timeout=None)
        self.bot = bot
        self.ticket_data = ticket_data
        
    @ui.button(label="關閉工單", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="close_ticket_button")
    async def close_ticket_button(self, interaction: discord.Interaction, button: ui.Button):
        channel = interaction.channel
        guild = interaction.guild

        guild_data = self.ticket_data.get_guild_data(guild.id)
        active_tickets = guild_data["active_tickets"]

        if str(channel.id) not in active_tickets:
            await interaction.response.send_message("這個頻道不是一個活躍的工單頻道。", ephemeral=True)
            return

        ticket_info = active_tickets[str(channel.id)]
        owner_id = int(ticket_info["owner_id"])
        
        # 檢查權限：只有工單創建者或有管理頻道權限的人可以關閉
        if interaction.user.id != owner_id and not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("您沒有權限關閉此工單。", ephemeral=True)
            return
        
        await interaction.response.send_message("正在關閉工單...", ephemeral=True)
        
        self.ticket_data.remove_ticket(guild.id, channel.id)
        await channel.delete()


class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.ticket_data = TicketData()
        self.ticket_panel_view = TicketPanel(self.bot, self.ticket_data)
        
    @commands.Cog.listener()
    async def on_ready(self):
        # 機器人啟動時，重新註冊按鈕事件
        self.bot.add_view(self.ticket_panel_view)
        self.bot.add_view(TicketCloseView(self.bot, self.ticket_data))

    @app_commands.command(name="ticket_panel", description="建立一個客製化的工單建立面板")
    @app_commands.describe(
        標題="面板的標題",
        描述="面板的描述內容",
        顏色="面板的16進位顏色代碼，例如：#FF5733"
    )
    @commands.has_permissions(manage_guild=True)
    @app_commands.guild_only()
    async def create_ticket_panel(self, interaction: discord.Interaction, 標題: str, 描述: str, 顏色: str):
        # 1. 回覆一個只有使用者自己看得到的訊息，告知正在處理
        await interaction.response.send_message("正在建立工單面板...", ephemeral=True)

        try:
            # 轉換16進位顏色代碼為整數
            color_value = int(顏色.replace("#", ""), 16)
            embed_color = discord.Color(color_value)
        except ValueError:
            await interaction.followup.send("無效的16進位顏色代碼。請提供像`#FF5733`這樣的格式。", ephemeral=True)
            return

        embed = discord.Embed(
            title=標題,
            description=描述,
            color=embed_color
        )
        
        # 2. 另外發送一個獨立的訊息到頻道，這是使用者都看得到的工單面板
        panel_message = await interaction.channel.send(embed=embed, view=self.ticket_panel_view)
        
        # 儲存面板訊息 ID，以便在機器人重啟時重新附加 View
        guild_data = self.ticket_data.get_guild_data(interaction.guild_id)
        guild_data["panel_message_id"] = str(panel_message.id)
        guild_data["panel_channel_id"] = str(interaction.channel_id)
        self.ticket_data._save_data()


async def setup(bot):
    await bot.add_cog(Tickets(bot))