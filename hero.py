import discord
from discord.ext import commands
import aiohttp
from bs4 import BeautifulSoup
import json
from log_handler import logger

class HeroCog(commands.Cog, name="Hero"):
    """Command to fetch character information from the Mineria Fandom Wiki."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="hero", aliases=["kahraman", "charinfo"])
    async def hero_lookup(self, ctx: commands.Context, *, name: str = None):
        """Fetches a character's page from the Mineria Wiki and displays all information.
        Usage: !hero <name>"""
        if not name:
            return await ctx.send("❌ Hata: Bir karakter ismi belirtmelisiniz. Örnek: `!hero Varka`")

        # Start typing to show the bot is working
        async with ctx.typing():
            # Format the name for URL (capitalize first letter, replace spaces with underscores)
            formatted_name = name.strip().replace(" ", "_").title()
            
            # MediaWiki API URL for parsing page content
            url = f"https://mineria.fandom.com/tr/api.php?action=parse&page={formatted_name}&format=json&prop=text"
            
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(url, headers={"User-Agent": "MineriaDiscordBot/1.0"}) as response:
                        if response.status != 200:
                            return await ctx.send(f"❌ Wiki API'ye ulaşılamadı. (Status Code: {response.status})")
                        
                        data = await response.json()
                        
                        if "error" in data:
                            if data["error"]["code"] == "missingtitle":
                                return await ctx.send(f"❌ '{name}' isimli bir karakter wiki'de bulunamadı.")
                            else:
                                return await ctx.send(f"❌ Wiki'den bilgi alınırken bir hata oluştu: {data['error'].get('info', 'Bilinmeyen hata')}")
                        
                        if "parse" not in data or "text" not in data["parse"] or "*" not in data["parse"]["text"]:
                            return await ctx.send("❌ Wiki verisi beklenen formatta değil.")
                        
                        html_content = data["parse"]["text"]["*"]
                        page_title = data["parse"]["title"]
                        wiki_url = f"https://mineria.fandom.com/tr/wiki/{formatted_name}"
                        
                        # Parse HTML
                        soup = BeautifulSoup(html_content, 'html.parser')
                        
                        # Remove edit links and brackets like [kaynağı değiştir]
                        for span in soup.find_all('span', class_='mw-editsection'):
                            span.decompose()
                        
                        # Find infobox
                        infobox = soup.find('aside', class_='portable-infobox')
                        if infobox:
                            # Extract thumbnail if available
                            image_fig = infobox.find('figure', class_='pi-image')
                            if image_fig:
                                img_tag = image_fig.find('img')
                                if img_tag and 'src' in img_tag.attrs:
                                    thumbnail_url = img_tag['src']
                                    # Fix size parameter if it exists to get better quality
                                    if 'scale-to-width-down' in thumbnail_url:
                                        import re
                                        thumbnail_url = re.sub(r'scale-to-width-down/\d+', 'scale-to-width-down/350', thumbnail_url)
                        
                        
                        # Extract infobox stats and then completely remove it so it doesn't bleed into paragraphs
                        stats = {}
                        thumbnail_url = None
                        
                        if infobox:
                            image_fig = infobox.find('figure', class_='pi-image')
                            if image_fig:
                                img_tag = image_fig.find('img')
                                if img_tag and 'src' in img_tag.attrs:
                                    thumbnail_url = img_tag['src']
                                    if 'scale-to-width-down' in thumbnail_url:
                                        import re
                                        thumbnail_url = re.sub(r'scale-to-width-down/\d+', 'scale-to-width-down/350', thumbnail_url)

                            for row in infobox.find_all('div', class_='pi-item'):
                                label_tag = row.find('h3', class_='pi-data-label')
                                value_tag = row.find('div', class_='pi-data-value')
                                if label_tag and value_tag:
                                    label_text = label_tag.get_text(strip=True)
                                    for br in value_tag.find_all('br'):
                                        br.replace_with('\n')
                                    for li in value_tag.find_all('li'):
                                        li.insert_before('\n• ')
                                        
                                    value_text = value_tag.get_text(separator=' ', strip=True)
                                    import re
                                    value_text = re.sub(r'\[\d+\]', '', value_text)
                                    value_text = re.sub(r'(\s*,\s*)+', ', ', value_text).strip(', ')
                                    value_text = re.sub(r'\n\s*\n', '\n', value_text).strip()
                                    
                                    if value_text:
                                        stats[label_text] = value_text
                                        
                            # Completely remove infobox from soup to avoid reading its text as paragraphs
                            infobox.decompose()
                        
                        # Extract paragraph text (story/details)
                        paragraphs = []
                        # Look for direct paragraphs or inside mw-parser-output
                        parser_output = soup.find('div', class_='mw-parser-output')
                        source_scope = parser_output if parser_output else soup
                        
                        for element in source_scope.find_all(['p', 'h2', 'h3', 'ul'], recursive=False):
                            # Skip empty paragraphs or those just containing br
                            text = element.get_text(strip=True)
                            if not text:
                                continue
                                
                            # If it's a heading, format it as bold
                            if element.name in ['h2', 'h3']:
                                # Skip table of contents heading and some internal wiki headings
                                if text in ['İçindekiler', 'Notlar', 'Referanslar', 'Dış bağlantılar']:
                                    continue
                                paragraphs.append(f"\n**{text}**")
                            elif element.name == 'ul':
                                # Handle lists in paragraphs
                                list_items = []
                                for li in element.find_all('li'):
                                    li_text = li.get_text(strip=True)
                                    import re
                                    li_text = re.sub(r'\[\d+\]', '', li_text)
                                    if li_text: list_items.append(f"• {li_text}")
                                paragraphs.append("\n".join(list_items))
                            else:
                                # Clean up citations
                                import re
                                text = re.sub(r'\[\d+\]', '', text)
                                paragraphs.append(text)
                        
                        story_text = "\n\n".join(paragraphs).strip()
                        if not story_text:
                            story_text = "Bu karakter için herhangi bir metin bulunamadı."
                        
                        # Build Embeds
                        embeds = []
                        
                        # Main Info Embed
                        main_embed = discord.Embed(
                            title=f"📖 {page_title}",
                            url=wiki_url,
                            color=discord.Color.blue()
                        )
                        
                        if thumbnail_url:
                            main_embed.set_thumbnail(url=thumbnail_url)
                            
                        # Add stats as fields vertically for better readability
                        for key, val in stats.items():
                            main_embed.add_field(name=key, value=val, inline=False)
                            
                        embeds.append(main_embed)
                        
                        # Handling story text limits (4096 is max embed description)
                        # We will create follow-up embeds if the text is too long
                        max_desc_len = 4000 # leaving some buffer
                        
                        if len(story_text) <= max_desc_len:
                            main_embed.description = story_text
                        else:
                            # Just set a brief intro on main embed or leave it empty, and send chunks
                            chunks = [story_text[i:i + max_desc_len] for i in range(0, len(story_text), max_desc_len)]
                            
                            # Put first chunk in main embed
                            main_embed.description = chunks[0]
                            
                            # Create new embeds for remaining chunks
                            for i, chunk in enumerate(chunks[1:], 1):
                                chunk_embed = discord.Embed(
                                    description=chunk,
                                    color=discord.Color.blue()
                                )
                                chunk_embed.set_footer(text=f"Sayfa {i+1}/{len(chunks)}")
                                embeds.append(chunk_embed)
                        
                        # Send the embed(s)
                        if len(embeds) == 1:
                            await ctx.send(embed=embeds[0])
                        else:
                            # Send main first
                            await ctx.send(embed=embeds[0])
                            # Send follow-ups
                            for emb in embeds[1:]:
                                await ctx.send(embed=emb)
                                
                except Exception as e:
                    logger.error(f"Error fetching hero data for {name}: {e}")
                    return await ctx.send(f"❌ Bilgi alınırken bir donanım/bağlantı hatası oluştu.")

async def setup(bot):
    await bot.add_cog(HeroCog(bot))
