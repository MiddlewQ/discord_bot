import discord
import math
import logging
import src.utils.message as msg
logger = logging.getLogger(__name__)

class PaginationView(discord.ui.View):

    def __init__(
            self,
            data: dict,
            *,
            title: str | None = None,
            description: str | None = None,
            timeout: float | None = 180,
            sep: int = 5
    ):
        super().__init__(timeout=timeout)
        
        if "fields" not in data:
            raise ValueError("Pagination data must contain a 'fields' list")
        self.data = data
        self.title= title
        self.description = description
        
        if sep <= 0:
            raise ValueError("sep must be greater than 0")
        self.sep = sep
        
        self.current_page = 1
        self.message: discord.Message | None = None
    
    
    async def send(self, ctx):
        self.update_buttons()
        self.message = await ctx.send(embed=self.create_embed(), view=self)

    def create_embed(self):
        current_page_data = self.get_current_page_data()
        title = self.title or "Page"

        embed = discord.Embed(
            title=f"{title} {self.current_page} / {self.page_count()}", 
            description=self.description
        )

        for item in current_page_data:
            embed.add_field(
                name=item.get("label") or "\u200b",
                value=item.get("item") or "\u200b",
                inline=False
            )

        thumbnail = self.data.get("thumbnail")

        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
        
        time_label = self.data.get("time_label")
        time_value = self.data.get("time")
        if time_label and time_value:
            embed.add_field(name=time_label, value=time_value, inline=False)

        logger.debug(msg.LOG_PAGINATOR_EXECUTED.format(page=self.current_page))
        return embed

    async def update_message(self):
        if self.message is None:
            return 

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

        if self.current_page >= self.page_count():
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
        start = (self.current_page - 1) * self.sep
        end = start + self.sep
        return self.data["fields"][start:end]
        
    def page_count(self):
        return max(1, math.ceil(len(self.data["fields"]) / self.sep))

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
        self.current_page = max(1, self.current_page - 1)
        await self.update_message()

    @discord.ui.button(label=">",
                       style=discord.ButtonStyle.primary)
    async def next_button(self, interaction:discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.current_page = min(self.page_count(), self.current_page + 1)
        await self.update_message()

    @discord.ui.button(label=">|",
                       style=discord.ButtonStyle.green)
    async def last_page_button(self, interaction:discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.current_page = self.page_count()
        await self.update_message()


class LinePaginationView(PaginationView):
    """Pages of plain text lines instead of embed fields, which take far less room.

    data["fields"] holds one string per line, and data["summary"] goes in the footer next to the
    page number. data["thumbnail"] is an optional image URL. The description stays on every page.
    Lines have a blank line between them so they are easy to read. A single page shows no buttons.
    """

    async def send(self, ctx):
        if self.page_count() > 1:
            await super().send(ctx)
        else:
            await ctx.send(embed=self.create_embed())

    def create_embed(self):
        lines = [self.description, *self.get_current_page_data()]
        embed = discord.Embed(
            title=self.title,
            description="\n\n".join(line for line in lines if line),
            color=discord.Color.blue(),
        )
        thumbnail = self.data.get("thumbnail")
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
        embed.set_footer(text=msg.PAGE_FOOTER.format(
            page=self.current_page,
            pages=self.page_count(),
            summary=self.data["summary"],
        ))

        logger.debug(msg.LOG_PAGINATOR_EXECUTED.format(page=self.current_page))
        return embed
