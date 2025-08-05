# cogs/shop.py
import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from typing import Optional, Literal

# 數據檔案
SHOP_DATA_FILE = 'shop_data.json'
CURRENCY_COG_NAME = "Currency"

class ShopView(discord.ui.View):
    """商店介面視圖，包含購買按鈕和分頁功能。"""
    def __init__(self, shop_cog, items, page=0):
        super().__init__(timeout=None)
        self.shop_cog = shop_cog
        self.items = items
        self.page = page
        self.items_per_page = 5
        
        if not self.items:
            self.total_pages = 1
        else:
            self.total_pages = (len(self.items) + self.items_per_page - 1) // self.items_per_page
        
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        start_index = self.page * self.items_per_page
        end_index = min(start_index + self.items_per_page, len(self.items))
        
        for i in range(start_index, end_index):
            item = self.items[i]
            # 只有當庫存大於 0 或為無限時，按鈕才啟用
            is_disabled = item.get('quantity') is not None and item.get('quantity') <= 0
            self.add_item(ShopButton(self.shop_cog, item, disabled=is_disabled))

        if self.total_pages > 1:
            self.add_item(self.prev_button)
            self.add_item(self.next_button)

    @discord.ui.button(label="上一頁", style=discord.ButtonStyle.secondary, row=4)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 0:
            self.page -= 1
            await self.shop_cog._send_shop_page(interaction, self.items, self.page, self)

    @discord.ui.button(label="下一頁", style=discord.ButtonStyle.secondary, row=4)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page < self.total_pages - 1:
            self.page += 1
            await self.shop_cog._send_shop_page(interaction, self.items, self.page, self)

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item) -> None:
        await interaction.response.send_message(f"發生了未知錯誤：{error}", ephemeral=True)


class ShopButton(discord.ui.Button):
    """商店中的購買按鈕。"""
    def __init__(self, shop_cog, item, disabled=False):
        super().__init__(label=f"購買 {item['name']}", style=discord.ButtonStyle.green, disabled=disabled)
        self.shop_cog = shop_cog
        self.item = item
        
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        user = interaction.user
        item_name = self.item['name']
        cost = self.item['cost']
        required_role_id = self.item.get('required_role_id')
        gained_role_id = self.item.get('gained_role_id')
        quantity = self.item.get('quantity')

        # 獲取貨幣 Cog
        currency_cog = self.shop_cog.bot.get_cog(CURRENCY_COG_NAME)
        if not currency_cog:
            await interaction.followup.send("錯誤：找不到貨幣系統。請聯繫管理員。", ephemeral=True)
            return

        # 檢查庫存
        if quantity is not None and quantity <= 0:
            await interaction.followup.send(f"商品 **{item_name}** 已售完。", ephemeral=True)
            return

        # 檢查是否滿足購買條件身分組
        if required_role_id:
            required_role = interaction.guild.get_role(int(required_role_id))
            if required_role and required_role not in user.roles:
                await interaction.followup.send(
                    f"您需要擁有身分組 **{required_role.name}** 才能購買此商品。",
                    ephemeral=True
                )
                return

        # 檢查代幣是否足夠
        user_money = await currency_cog.get_user_money(user.id)
        if user_money < cost:
            await interaction.followup.send(f"您的代幣不足，需要 {cost} 個代幣來購買 **{item_name}**。", ephemeral=True)
            return

        # 扣除代幣
        deducted = await currency_cog.deduct_user_money(user.id, cost)
        if not deducted:
            await interaction.followup.send("扣除代幣失敗，請稍後再試。", ephemeral=True)
            return

        # 扣除庫存並儲存
        if quantity is not None:
            self.item['quantity'] -= 1
            self.shop_cog._save_shop_data()

        # 給予身分組
        if gained_role_id:
            gained_role = interaction.guild.get_role(int(gained_role_id))
            try:
                if gained_role:
                    await user.add_roles(gained_role)
                await interaction.followup.send(
                    f"🎉 恭喜！您成功以 {cost} 個代幣購買了 **{item_name}**，並獲得了身分組 **{gained_role.name}**！",
                    ephemeral=False
                )
            except discord.Forbidden:
                await interaction.followup.send("我沒有足夠的權限來給予身分組，請聯繫管理員。", ephemeral=True)
                # 如果給予身分組失敗，將代幣退還並恢復庫存
                await currency_cog.add_user_money(user.id, cost)
                if quantity is not None:
                    self.item['quantity'] += 1
                    self.shop_cog._save_shop_data()
        else:
            await interaction.followup.send(
                f"🎉 恭喜！您成功以 {cost} 個代幣購買了 **{item_name}**！",
                ephemeral=False
            )
            
        # 重新發送商店頁面，以更新按鈕狀態和庫存顯示
        await self.shop_cog._send_shop_page(interaction, self.shop_cog.shop_items, self.shop_cog._last_page, self.view)

class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.shop_data_file = SHOP_DATA_FILE
        self.shop_items = self._load_shop_data()
        self._last_page = 0

    def _load_shop_data(self):
        if os.path.exists(self.shop_data_file):
            with open(self.shop_data_file, 'r', encoding='utf-8') as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return []
        return []

    def _save_shop_data(self):
        with open(self.shop_data_file, 'w', encoding='utf-8') as f:
            json.dump(self.shop_items, f, indent=4, ensure_ascii=False)

    @app_commands.command(name="上架商品", description="上架一個新的商店商品（需管理權限）")
    @app_commands.describe(
        名稱="商品名稱",
        價格="購買所需代幣數",
        獲得身分組="購買後獲得的身分組",
        所需身分組="購買前需要擁有的身分組",
        庫存="庫存數量 (留空為無限)"
    )
    @commands.has_permissions(manage_guild=True)
    async def add_shop_item(
        self, 
        interaction: discord.Interaction, 
        名稱: str, 
        價格: int, 
        獲得身分組: Optional[discord.Role],
        所需身分組: Optional[discord.Role] = None,
        庫存: Optional[int] = None
    ):
        if 價格 <= 0:
            await interaction.response.send_message("商品價格必須大於 0。", ephemeral=True)
            return
        if 庫存 is not None and 庫存 <= 0:
            await interaction.response.send_message("庫存數量必須大於 0。", ephemeral=True)
            return
            
        new_item = {
            "name": 名稱,
            "cost": 價格,
            "gained_role_id": str(獲得身分組.id) if 獲得身分組 else None,
            "required_role_id": str(所需身分組.id) if 所需身分組 else None,
            "quantity": 庫存
        }
        
        self.shop_items.append(new_item)
        self._save_shop_data()
        
        embed = discord.Embed(
            title="商品已上架",
            description=f"成功將商品 **{名稱}** 上架！",
            color=discord.Color.green()
        )
        embed.add_field(name="價格", value=f"{價格} 代幣")
        embed.add_field(name="庫存", value=f"{庫存 if 庫存 is not None else '無限'}")
        if 獲得身分組:
            embed.add_field(name="購買後獲得身分組", value=獲得身分組.mention, inline=False)
        if 所需身分組:
            embed.add_field(name="購買所需身分組", value=所需身分組.mention, inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="下架商品", description="下架一個商店商品（需管理權限）")
    @app_commands.describe(名稱="要下架的商品名稱")
    @commands.has_permissions(manage_guild=True)
    async def remove_shop_item(self, interaction: discord.Interaction, 名稱: str):
        original_count = len(self.shop_items)
        self.shop_items = [item for item in self.shop_items if item['name'] != 名稱]
        
        if len(self.shop_items) < original_count:
            self._save_shop_data()
            await interaction.response.send_message(f"✅ 商品 **{名稱}** 已成功下架！", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ 找不到名稱為 **{名稱}** 的商品。", ephemeral=True)
            
    async def _create_shop_embed(self, items, page, guild):
        items_per_page = 5
        start_index = page * items_per_page
        end_index = min(start_index + items_per_page, len(items))
        
        embed = discord.Embed(title="🛒 伺服器商店", color=discord.Color.blue())
        embed.set_footer(text=f"第 {page + 1} / {(len(items) + items_per_page - 1) // items_per_page} 頁")
        
        if not items:
            embed.description = "商店目前沒有任何商品。"
            return embed

        for i in range(start_index, end_index):
            item = items[i]
            
            gained_role_id = item.get('gained_role_id')
            required_role_id = item.get('required_role_id')
            quantity = item.get('quantity')
            
            gained_role_mention = "無"
            required_role_mention = "無"
            
            if gained_role_id:
                role = guild.get_role(int(gained_role_id))
                gained_role_mention = role.mention if role else "已刪除身分組"
            
            if required_role_id:
                role = guild.get_role(int(required_role_id))
                required_role_mention = role.mention if role else "已刪除身分組"

            stock_text = f"{quantity}" if quantity is not None else "無限"
            
            embed.add_field(
                name=f"**{item['name']}**",
                value=(
                    f"價格: `{item['cost']}` 代幣\n"
                    f"庫存: `{stock_text}`\n"
                    f"購買後獲得身分組: {gained_role_mention}\n"
                    f"購買所需身分組: {required_role_mention}"
                ),
                inline=False
            )
            
        return embed

    async def _send_shop_page(self, interaction, items, page, view):
        self._last_page = page
        view.page = page
        view.update_buttons()
        embed = await self._create_shop_embed(items, page, interaction.guild)
        await interaction.response.edit_message(embed=embed, view=view)


    @app_commands.command(name="查看商店", description="查看所有可購買的商品")
    async def view_shop(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        self.shop_items = self._load_shop_data()
        
        if not self.shop_items:
            embed = discord.Embed(title="🛒 伺服器商店", description="商店目前沒有任何商品。", color=discord.Color.blue())
            await interaction.followup.send(embed=embed)
            return
            
        self._last_page = 0
        view = ShopView(self, self.shop_items)
        embed = await self._create_shop_embed(self.shop_items, 0, interaction.guild)
        
        # 根據頁數調整分頁按鈕的啟用狀態
        if view.total_pages > 1:
            view.prev_button.disabled = True
            view.next_button.disabled = False
        else:
            view.prev_button.disabled = True
            view.next_button.disabled = True
        
        await interaction.followup.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Shop(bot))