import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import asyncio
import datetime
import random
from typing import Optional, List, Dict, Any, Tuple

from .giveaway_data import load_giveaway_data, save_giveaway_data, get_guild_data
from .giveaway_utils import parse_duration

class Giveaways(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.giveaway_data: Dict[str, Any] = load_giveaway_data()
        self.active_giveaway_tasks: Dict[str, asyncio.Task] = {}
        self.bot.loop.create_task(self.check_unfinished_giveaways())

    async def check_unfinished_giveaways(self):
        await self.bot.wait_until_ready()
        print("機器人已就緒，檢查是否有未處理的抽獎活動。")
        now = datetime.datetime.now(datetime.timezone.utc)
        
        for guild_id_str, guild_data in list(self.giveaway_data.items()):
            if "active_giveaways" not in guild_data:
                continue
            
            for message_id_str, giveaway_info in list(guild_data["active_giveaways"].items()):
                if giveaway_info["status"] == "active" and now >= datetime.datetime.fromtimestamp(giveaway_info["end_time"], tz=datetime.timezone.utc):
                    print(f"偵測到抽獎 {message_id_str} (伺服器: {guild_id_str}) 在機器人離線期間已過期，立即處理。")
                    
                    guild = self.bot.get_guild(int(guild_id_str))
                    if not guild:
                        giveaway_info["status"] = "ended"
                        del guild_data["active_giveaways"][message_id_str]
                        save_giveaway_data(self.giveaway_data)
                        continue
                    
                    channel = guild.get_channel(giveaway_info["channel_id"])
                    if not channel:
                        giveaway_info["status"] = "ended"
                        del guild_data["active_giveaways"][message_id_str]
                        save_giveaway_data(self.giveaway_data)
                        continue
                    
                    giveaway_message = None
                    try:
                        giveaway_message = await channel.fetch_message(int(message_id_str))
                        if giveaway_message:
                            await self._end_giveaway(guild, channel, giveaway_message, giveaway_info)
                    except (discord.NotFound, discord.Forbidden):
                        print(f"警告: 找不到抽獎訊息 {message_id_str} 或機器人無權限。將其標記為結束。")
                        giveaway_info["status"] = "ended"
                        del guild_data["active_giveaways"][message_id_str]
                        save_giveaway_data(self.giveaway_data)
                    except Exception as e:
                        print(f"處理過期抽獎 {message_id_str} 時發生未知錯誤: {e}。")
                        giveaway_info["status"] = "ended"
                        del guild_data["active_giveaways"][message_id_str]
                        save_giveaway_data(self.giveaway_data)

    @app_commands.command(name="建立獎池", description="建立一個新的抽獎獎池")
    @app_commands.describe(
        名稱="獎池的名稱",
        消耗代幣數量="參與抽獎每次需要消耗的代幣數量",
        所需身分組="參與此抽獎所需擁有的身分組"
    )
    @commands.has_permissions(manage_guild=True)
    async def create_prize_pool(
        self,
        interaction: discord.Interaction,
        名稱: str,
        消耗代幣數量: app_commands.Range[int, 0],
        所需身分組: Optional[discord.Role] = None
    ):
        await interaction.response.defer(ephemeral=True)
        guild_data = get_guild_data(self.giveaway_data, interaction.guild_id)

        if 名稱 in guild_data["prize_pools"]:
            await interaction.followup.send(f"獎池 `{名稱}` 已存在，請使用其他名稱。")
            return

        guild_data["prize_pools"][名稱] = {
            "cost_token": 消耗代幣數量,
            "required_role_id": str(所需身分組.id) if 所需身分組 else None,
            "items": []
        }
        save_giveaway_data(self.giveaway_data)
        await interaction.followup.send(
            f"已成功建立獎池 `{名稱}`，每次參與需消耗 `{消耗代幣數量}` 代幣。"
            + (f" (需身分組: {所需身分組.mention})" if 所需身分組 else "")
        )

    @app_commands.command(name="查詢獎池", description="查詢伺服器中所有已建立的抽獎獎池")
    async def list_prize_pools(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        guild_data = get_guild_data(self.giveaway_data, interaction.guild_id)

        prize_pools_info = []
        for name, pool_data in guild_data["prize_pools"].items():
            item_count = len(pool_data.get("items", []))
            cost = pool_data.get("cost_token", 0)
            role_info = ""
            if pool_data.get("required_role_id"):
                role = interaction.guild.get_role(int(pool_data["required_role_id"]))
                role_info = f", 需身分組: {role.name}" if role else ", 需未知身分組"

            prize_pools_info.append(
                f"- `{name}` (物品: {item_count}個, 參與消耗: {cost}代幣{role_info})"
            )

        if not prize_pools_info:
            await interaction.followup.send("此伺服器目前沒有任何獎池。")
        else:
            embed = discord.Embed(
                title="✨ 現有抽獎獎池 ✨",
                description="\n".join(prize_pools_info),
                color=discord.Color.blue()
            )
            await interaction.followup.send(embed=embed)

    @app_commands.command(name="刪除獎池", description="刪除一個抽獎獎池及其所有物品")
    @app_commands.describe(名稱="要刪除的獎池名稱")
    @commands.has_permissions(manage_guild=True)
    async def delete_prize_pool(self, interaction: discord.Interaction, 名稱: str):
        await interaction.response.defer(ephemeral=True)
        guild_data = get_guild_data(self.giveaway_data, interaction.guild_id)

        if 名稱 not in guild_data["prize_pools"]:
            await interaction.followup.send(f"獎池 `{名稱}` 不存在。")
            return

        del guild_data["prize_pools"][名稱]
        save_giveaway_data(self.giveaway_data)
        await interaction.followup.send(f"已成功刪除獎池 `{名稱}` 及其所有物品。")

    @app_commands.command(name="新增獎池物品", description="向指定獎池添加新的獎品")
    @app_commands.describe(
        獎池="獎品所屬的獎池名稱",
        名稱="獎品的名稱",
        數量="獎品的數量",
        機率="抽中此獎品的機率"
    )
    @commands.has_permissions(manage_guild=True)
    async def add_prize_pool_item(
        self,
        interaction: discord.Interaction,
        獎池: str,
        名稱: str,
        數量: app_commands.Range[int, 1],
        機率: app_commands.Range[int, 0, 100]
    ):
        await interaction.response.defer(ephemeral=True)
        guild_data = get_guild_data(self.giveaway_data, interaction.guild_id)

        if 獎池 not in guild_data["prize_pools"]:
            await interaction.followup.send(f"獎池 `{獎池}` 不存在。請先使用 `/建立獎池` 創建。")
            return

        prize_pool = guild_data["prize_pools"][獎池]

        for item in prize_pool["items"]:
            if item["item_name"] == 名稱:
                await interaction.followup.send(f"獎池 `{獎池}` 中已存在名為 `{名稱}` 的物品。")
                return

        item_data = {
            "item_name": 名稱,
            "quantity": 數量,
            "probability": 機率
        }
        prize_pool["items"].append(item_data)
        save_giveaway_data(self.giveaway_data)
        await interaction.followup.send(
            f"已成功將獎品 `{名稱}` (數量: {數量}, 機率: {機率}%) 添加到獎池 `{獎池}`。"
        )

    @app_commands.command(name="刪除獎池物品", description="從指定獎池中刪除某個獎品")
    @app_commands.describe(
        獎池="獎品所屬的獎池名稱",
        名稱="要刪除的獎品名稱"
    )
    @commands.has_permissions(manage_guild=True)
    async def delete_prize_pool_item(self, interaction: discord.Interaction, 獎池: str, 名稱: str):
        await interaction.response.defer(ephemeral=True)
        guild_data = get_guild_data(self.giveaway_data, interaction.guild_id)

        if 獎池 not in guild_data["prize_pools"]:
            await interaction.followup.send(f"獎池 `{獎池}` 不存在。")
            return

        prize_pool = guild_data["prize_pools"][獎池]
        item_found = False
        new_items = []
        for item in prize_pool["items"]:
            if item["item_name"] == 名稱:
                item_found = True
            else:
                new_items.append(item)
        
        if not item_found:
            await interaction.followup.send(f"獎池 `{獎池}` 中找不到名為 `{名稱}` 的物品。")
            return
        
        prize_pool["items"] = new_items
        save_giveaway_data(self.giveaway_data)
        await interaction.followup.send(f"已成功從獎池 `{獎池}` 中刪除物品 `{名稱}`。")

    @app_commands.command(name="查詢獎池物品", description="查詢指定獎池中的所有獎品及其詳細資訊")
    @app_commands.describe(獎池="要查詢的獎池名稱")
    async def list_prize_pool_items(self, interaction: discord.Interaction, 獎池: str):
        await interaction.response.defer(ephemeral=False)
        guild_data = get_guild_data(self.giveaway_data, interaction.guild_id)

        if 獎池 not in guild_data["prize_pools"]:
            await interaction.followup.send(f"獎池 `{獎池}` 不存在。")
            return

        prize_pool = guild_data["prize_pools"][獎池]
        items = prize_pool["items"]

        if not items:
            await interaction.followup.send(f"獎池 `{獎池}` 中目前沒有任何獎品。")
            return

        embed = discord.Embed(
            title=f"🏆 獎池 `{獎池}` 中的獎品列表 🏆",
            color=discord.Color.gold()
        )
        for item in items:
            embed.add_field(
                name=f"**{item['item_name']}**",
                value=f"數量: `{item['quantity']}`\n機率: `{item['probability']}%`",
                inline=True
            )
        
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="抽獎", description="開始一個新的抽獎活動")
    @app_commands.describe(
        獎池="要用於抽獎的獎池名稱",
        持續時間="抽獎的持續時間 (例如: 10s, 10m, 1h, 1d)",
        抽獎訊息="抽獎活動的簡短說明或標題",
        參與反應="使用者點擊此反應符號即可參與抽獎",
        所需等級="參與抽獎所需的最低等級",
        參與人數上限="最多允許參與抽獎的人數"
    )
    @commands.has_permissions(manage_guild=True)
    async def start_giveaway(
        self,
        interaction: discord.Interaction,
        獎池: str,
        持續時間: str,
        抽獎訊息: Optional[str] = "點擊 🎉 參與抽獎！",
        參與反應: Optional[str] = "🎉",
        所需等級: app_commands.Range[int, 0] = 0,
        參與人數上限: app_commands.Range[int, 0] = 100
    ):
        await interaction.response.defer(ephemeral=True)
        guild_data = get_guild_data(self.giveaway_data, interaction.guild_id)

        if 獎池 not in guild_data["prize_pools"]:
            await interaction.followup.send(f"獎池 `{獎池}` 不存在。")
            return
        
        prize_pool_data = guild_data["prize_pools"][獎池]
        if not prize_pool_data["items"]:
            await interaction.followup.send(f"獎池 `{獎池}` 中沒有任何獎品，無法開始抽獎。")
            return

        duration = parse_duration(持續時間)
        if duration is None:
            await interaction.followup.send("無效的持續時間格式。請使用 '10s', '10m', '1h', '1d' 等格式。")
            return
        
        end_time = datetime.datetime.now(datetime.timezone.utc) + duration
        cost_token = prize_pool_data.get("cost_token", 0)
        required_entry_role_id = prize_pool_data.get("required_role_id")
        required_entry_role = interaction.guild.get_role(int(required_entry_role_id)) if required_entry_role_id else None

        embed = discord.Embed(
            title=f"🎁 抽獎活動：{獎池} 🎁",
            description=(
                f"{抽獎訊息}\n\n"
                f"獎池：`{獎池}`\n"
                f"結束時間：<t:{int(end_time.timestamp())}:R>\n"
                + (f"最多參與人數：`{參與人數上限}`\n" if 參與人數上限 > 0 else "參與人數：`無限制`\n")
                + f"參與反應：{參與反應}\n"
                + (f"每次參與需消耗：`{cost_token}` 代幣\n" if cost_token > 0 else "")
                + (f"所需身分組：{required_entry_role.mention}\n" if required_entry_role else "")
                + (f"所需等級：`{所需等級}` 等級\n" if 所需等級 > 0 else "")
            ),
            color=discord.Color.green()
        )
        embed.set_footer(text="點擊下面的反應符號參與！")

        prizes_list = []
        for item in prize_pool_data["items"]:
            prizes_list.append(f"- {item['item_name']} x{item['quantity']} (機率: {item['probability']}%)")
        embed.add_field(name="獎品列表", value="\n".join(prizes_list), inline=False)

        try:
            giveaway_message = await interaction.channel.send(embed=embed)
            await giveaway_message.add_reaction(參與反應)
        except discord.Forbidden:
            await interaction.followup.send("我沒有足夠的權限在該頻道發送訊息或添加反應符號。")
            return
        except Exception as e:
            await interaction.followup.send(f"發送抽獎訊息時發生錯誤：{e}")
            return
        
        giveaway_info = {
            "prize_pool_name": 獎池,
            "channel_id": interaction.channel.id,
            "end_time": end_time.timestamp(),
            "entry_emoji": 參與反應,
            "cost_token": cost_token,
            "required_entry_role_id": required_entry_role_id,
            "required_entry_level": 所需等級,
            "participants": [],
            "status": "active",
            "max_participants": 參與人數上限
        }
        guild_data["active_giveaways"][str(giveaway_message.id)] = giveaway_info
        save_giveaway_data(self.giveaway_data)

        await interaction.followup.send(f"抽獎活動已成功開始！請前往 {interaction.channel.mention} 查看。", ephemeral=True)
        
        time_to_wait = max(0, end_time.timestamp() - datetime.datetime.now(datetime.timezone.utc).timestamp())
        
        async def end_giveaway_task():
            await asyncio.sleep(time_to_wait)
            try:
                guild = self.bot.get_guild(interaction.guild_id)
                channel = guild.get_channel(interaction.channel.id)
                message = await channel.fetch_message(giveaway_message.id)
                await self._end_giveaway(guild, channel, message, giveaway_info)
            except Exception as e:
                print(f"自動結束抽獎 {giveaway_message.id} 時發生錯誤: {e}")
            finally:
                self.active_giveaway_tasks.pop(str(giveaway_message.id), None)
                
        self.active_giveaway_tasks[str(giveaway_message.id)] = asyncio.create_task(end_giveaway_task())

    async def _end_giveaway(self, guild: discord.Guild, channel: discord.TextChannel, message: discord.Message, giveaway_info: Dict[str, Any]):
        print(f"嘗試結束抽獎 {message.id} 並抽取贏家。")
        guild_id_str = str(guild.id)
        message_id_str = str(message.id)
        
        prize_pool_name = giveaway_info["prize_pool_name"]
        guild_data = get_guild_data(self.giveaway_data, guild.id)
        prize_pool_data = guild_data["prize_pools"].get(prize_pool_name)
        
        if not prize_pool_data:
            await channel.send(f"抽獎 `{prize_pool_name}` 的獎池數據已遺失。無法抽取贏家。")
            giveaway_info["status"] = "ended"
            del guild_data["active_giveaways"][message_id_str]
            save_giveaway_data(self.giveaway_data)
            return

        reacted_users_ids = []
        try:
            message = await channel.fetch_message(int(message_id_str))
            for reaction in message.reactions:
                if str(reaction.emoji) == giveaway_info["entry_emoji"]:
                    async for user in reaction.users():
                        if not user.bot:
                            reacted_users_ids.append(str(user.id))
                    break
        except (discord.NotFound, discord.Forbidden):
            print(f"警告: 無法獲取抽獎訊息 {message_id_str} 的反應。將使用儲存的參與者列表。")
            reacted_users_ids = giveaway_info["participants"]
        except Exception as e:
            print(f"獲取反應時發生錯誤: {e}。將使用儲存的參與者列表。")
            reacted_users_ids = giveaway_info["participants"]

        participants_ids = list(set(reacted_users_ids))
        eligible_participants: List[discord.Member] = []
        
        pool_required_role_id = prize_pool_data.get("required_role_id")
        pool_required_role = guild.get_role(int(pool_required_role_id)) if pool_required_role_id else None

        for user_id in participants_ids:
            member = guild.get_member(int(user_id))
            if not member:
                continue
            
            if pool_required_role and pool_required_role not in member.roles:
                continue
            
            if giveaway_info["required_entry_level"] > 0:
                user_level = 0
                if self.bot.get_cog('Leveling'):
                    try:
                        user_level = await self.bot.get_cog('Leveling').get_user_level(member.id)
                    except AttributeError:
                        user_level = giveaway_info["required_entry_level"] + 1
                else:
                    user_level = giveaway_info["required_entry_level"] + 1

                if user_level < giveaway_info["required_entry_level"]:
                    continue
            
            eligible_participants.append(member)

        final_participants: List[discord.Member] = []
        cost_token = prize_pool_data.get("cost_token", 0)

        currency_cog = self.bot.get_cog('Currency')
        if currency_cog and cost_token > 0:
            for member in eligible_participants:
                try:
                    user_balance = await currency_cog.get_user_money(member.id)
                    if user_balance >= cost_token:
                        await currency_cog.deduct_user_money(member.id, cost_token)
                        final_participants.append(member)
                    else:
                        try:
                            await message.remove_reaction(giveaway_info["entry_emoji"], member)
                        except discord.HTTPException:
                            pass
                        await member.send(f"很抱歉，您在抽獎 `{prize_pool_name}` 中代幣不足，未能參與。所需代幣: {cost_token}")
                except AttributeError:
                    await channel.send("⚠️ 抽獎代幣系統未正常運作，本次抽獎將免費參與。")
                    final_participants = eligible_participants
                    break
                except Exception as e:
                    await channel.send(f"⚠️ 處理代幣時發生未知錯誤，本次抽獎將免費參與：{e}")
                    final_participants = eligible_participants
                    break
        else:
            if cost_token > 0 and not currency_cog:
                await channel.send("⚠️ 抽獎需要代幣，但機器人無法處理代幣扣除。本次抽獎將免費參與。")
            final_participants = eligible_participants 

        if not final_participants:
            await channel.send(f"很抱歉，抽獎 `{prize_pool_name}` 沒有任何合格參與者。沒有獎品送出。")
            giveaway_info["status"] = "ended"
            if message_id_str in guild_data["active_giveaways"]:
                del guild_data["active_giveaways"][message_id_str]
            save_giveaway_data(self.giveaway_data)
            return

        winners_and_prizes: List[Tuple[discord.Member, Dict[str, Any]]] = []
        
        prize_inventory: Dict[str, Dict[str, Any]] = {}
        for item in prize_pool_data["items"]:
            prize_inventory[item["item_name"]] = {"item_data": item, "remaining_quantity": item["quantity"]}

        random.shuffle(final_participants) 

        max_participants_limit = giveaway_info.get("max_participants", 0)
        if max_participants_limit > 0:
            final_participants = final_participants[:max_participants_limit]

        for participant_member in final_participants:
            current_prize_choices = []
            current_prize_weights = []

            for item_name, inventory_data in prize_inventory.items():
                if inventory_data["remaining_quantity"] > 0:
                    current_prize_choices.append(inventory_data["item_data"])
                    current_prize_weights.append(inventory_data["item_data"]["probability"])
            
            if not current_prize_choices or sum(current_prize_weights) == 0:
                break
            
            try:
                chosen_prize_data = random.choices(current_prize_choices, weights=current_prize_weights, k=1)[0]
                prize_inventory[chosen_prize_data["item_name"]]["remaining_quantity"] -= 1
                winners_and_prizes.append((participant_member, chosen_prize_data))
            except Exception:
                pass

        if winners_and_prizes:
            winners_announcement = []
            for winner_member, item_data in winners_and_prizes:
                winners_announcement.append(f"恭喜 {winner_member.mention} 贏得了 **{item_data['item_name']}**！")
            
            results_embed = discord.Embed(
                title="🎉 抽獎結果公佈！ 🎉",
                description="\n".join(winners_announcement) + "\n\n恭喜所有中獎者！",
                color=discord.Color.blue()
            )
            results_embed.set_footer(text=f"抽獎來自獎池: {prize_pool_name}")
            await channel.send(embed=results_embed)
        else:
            await channel.send(f"很抱歉，抽獎 `{prize_pool_name}` 沒有任何中獎者。")

        giveaway_info["status"] = "ended"
        giveaway_info["winners"] = [{"user_id": str(w[0].id), "item_name": w[1]['item_name']} for w in winners_and_prizes]
        
        if message_id_str in guild_data["active_giveaways"]:
            del guild_data["active_giveaways"][message_id_str]
        
        save_giveaway_data(self.giveaway_data)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.guild_id is None or payload.member.bot:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild: return
        member = guild.get_member(payload.user_id)
        if not member or member.bot: return

        guild_data = get_guild_data(self.giveaway_data, payload.guild_id)
        active_giveaways = guild_data.get("active_giveaways", {})

        if str(payload.message_id) in active_giveaways:
            giveaway = active_giveaways[str(payload.message_id)]
            if giveaway["status"] != "active":
                return

            if str(payload.emoji) != giveaway["entry_emoji"]:
                return

            prize_pool_name = giveaway["prize_pool_name"]
            prize_pool_data = guild_data["prize_pools"].get(prize_pool_name)

            if not prize_pool_data:
                await member.send(f"很抱歉，抽獎 `{giveaway['prize_pool_name']}` 的配置有誤，請聯繫管理員。")
                try:
                    channel = guild.get_channel(giveaway["channel_id"])
                    if channel:
                        message = await channel.fetch_message(payload.message_id)
                        await message.remove_reaction(payload.emoji, member)
                except discord.HTTPException: pass
                return

            pool_required_role_id = prize_pool_data.get("required_role_id")
            if pool_required_role_id:
                required_role = guild.get_role(int(pool_required_role_id))
                if required_role and required_role not in member.roles:
                    await member.send(f"您需要擁有 `{required_role.name}` 身分組才能參與。")
                    try:
                        channel = guild.get_channel(giveaway["channel_id"])
                        if channel:
                            message = await channel.fetch_message(payload.message_id)
                            await message.remove_reaction(payload.emoji, member)
                    except discord.HTTPException: pass
                    return

            required_level = giveaway.get("required_entry_level", 0)
            if required_level > 0:
                user_level = 0
                leveling_cog = self.bot.get_cog('Leveling')
                if leveling_cog:
                    try:
                        user_level = await leveling_cog.get_user_level(member.id)
                    except AttributeError:
                        pass
                
                if user_level < required_level:
                    await member.send(f"您目前的等級是 `{user_level}`，所需最低等級為 `{required_level}`。")
                    try:
                        channel = guild.get_channel(giveaway["channel_id"])
                        if channel:
                            message = await channel.fetch_message(payload.message_id)
                            await message.remove_reaction(payload.emoji, member)
                    except discord.HTTPException: pass
                    return

            current_participants_count = len(set(giveaway["participants"]))
            max_participants_limit = giveaway.get("max_participants", 0)
            
            if max_participants_limit > 0 and current_participants_count >= max_participants_limit and str(member.id) not in giveaway["participants"]:
                await member.send(f"抽獎已達參與人數上限 (`{max_participants_limit}` 人)。")
                try:
                    channel = guild.get_channel(giveaway["channel_id"])
                    if channel:
                        message = await channel.fetch_message(payload.message_id)
                        await message.remove_reaction(payload.emoji, member)
                except discord.HTTPException: pass
                return

            cost_token = giveaway.get("cost_token", 0)
            if cost_token > 0:
                currency_cog = self.bot.get_cog('Currency')
                if currency_cog:
                    try:
                        user_balance = await currency_cog.get_user_money(member.id)
                        if user_balance < cost_token:
                            await member.send(f"您所需 `{cost_token}` 代幣不足。")
                            try:
                                channel = guild.get_channel(giveaway["channel_id"])
                                if channel:
                                    message = await channel.fetch_message(payload.message_id)
                                    await message.remove_reaction(payload.emoji, member)
                            except discord.HTTPException: pass
                            return
                    except (AttributeError, Exception):
                        await member.send("警告：機器人貨幣系統暫時無法運作，無法檢查您的代幣餘額。請通知管理員。")
                else:
                    await member.send("警告：抽獎需要代幣，但貨幣系統未找到。本次參與可能不計入代幣消耗。")
            
            giveaway["participants"].append(str(member.id))
            save_giveaway_data(self.giveaway_data)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        if payload.guild_id is None:
            return
        guild = self.bot.get_guild(payload.guild_id)
        if not guild: return
        member = guild.get_member(payload.user_id)
        if not member or member.bot: return

        guild_data = get_guild_data(self.giveaway_data, payload.guild_id)
        active_giveaways = guild_data.get("active_giveaways", {})

        if str(payload.message_id) in active_giveaways:
            giveaway = active_giveaways[str(payload.message_id)]
            if giveaway["status"] != "active":
                return
            
            if str(payload.emoji) != giveaway["entry_emoji"]:
                return

            user_id_str = str(payload.user_id)
            while user_id_str in giveaway["participants"]:
                giveaway["participants"].remove(user_id_str)
            save_giveaway_data(self.giveaway_data)

    def cog_unload(self):
        for task in self.active_giveaway_tasks.values():
            task.cancel()
        print("所有活躍抽獎的任務已取消。")

async def setup(bot):
    await bot.add_cog(Giveaways(bot))