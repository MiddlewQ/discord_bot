import discord
import math
from discord.ext import commands
from src.utils.logging_config import *
logger = logging.getLogger("bot")

class PaginationView(discord.ui.View):
    current_page : int = 1
    sep : int = 5
    title: str = None
    description: str = None

    async def send(self, ctx):
        self.message = await ctx.send(view=self)
        await self.update_message()

    def create_embed(self):
        current_page_data = self.get_current_page_data()
        embed = discord.Embed(title=f"{self.title} {self.current_page} / {min(1,math.ceil(len(self.data['fields']) / self.sep))}", description=self.description)
        for item in current_page_data:
            embed.add_field(name=item['label'], value=item['item'], inline=False)
        if self.data['thumbnail']:
            embed.set_thumbnail(url=self.data['thumbnail'])
        if self.data['time_label']:
            embed.add_field(name=self.data['time_label'], value=self.data['time'], inline=False)
        return embed

    async def update_message(self):
        self.update_buttons()
        await self.message.edit(embed=self.create_embed(), view=self)



    def update_buttons(self):
        if self.current_page == 1:
            self.first_page_button.disabled = True
            self.prev_button.disabled = True
            self.first_page_button.style = discord.ButtonStyle.gray
            self.prev_button.style = discord.ButtonStyle.gray
        else:
            self.first_page_button.disabled = False
            self.prev_button.disabled = False
            self.first_page_button.style = discord.ButtonStyle.green
            self.prev_button.style = discord.ButtonStyle.primary

        if self.current_page >= math.ceil(len(self.data['fields']) / self.sep):
            self.next_button.disabled = True
            self.last_page_button.disabled = True
            self.last_page_button.style = discord.ButtonStyle.gray
            self.next_button.style = discord.ButtonStyle.gray
        else:
            self.next_button.disabled = False
            self.last_page_button.disabled = False
            self.last_page_button.style = discord.ButtonStyle.green
            self.next_button.style = discord.ButtonStyle.primary

    def get_current_page_data(self):
        until_item = self.current_page * self.sep
        from_item = until_item - self.sep
        if self.current_page == 1:
            from_item = 0
            until_item = self.sep
        if self.current_page == math.ceil(len(self.data['fields']) / self.sep):

            from_item = self.current_page * self.sep - self.sep
            until_item = len(self.data['fields'])
        print(f"from {from_item} until {until_item}")
        return self.data['fields'][from_item:until_item]


    @discord.ui.button(label="|<",
                       style=discord.ButtonStyle.green)
    async def first_page_button(self, interaction:discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.current_page = 1
        await self.update_message()

    @discord.ui.button(label="<",
                       style=discord.ButtonStyle.primary)
    async def prev_button(self, interaction:discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.current_page -= 1
        await self.update_message()

    @discord.ui.button(label=">",
                       style=discord.ButtonStyle.primary)
    async def next_button(self, interaction:discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.current_page += 1
        await self.update_message()

    @discord.ui.button(label=">|",
                       style=discord.ButtonStyle.green)
    async def last_page_button(self, interaction:discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.current_page = math.ceil(len(self.data['fields']) / self.sep)
        await self.update_message()
