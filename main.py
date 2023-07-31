import discord
from discord import Option
from datetime import timedelta
from datetime import datetime
from discord.ext import commands
from discord.ext.commands import MissingPermissions
from asyncio import sleep
import asyncio
import datetime
from discord import Member
from discord.ext import commands
import mysql.connector

intents = discord.Intents.all()

# Define your bot
bot = commands.Bot(command_prefix='/', intents=intents)

db_config = {
    "host": "db.mena1.oinkdom.xyz",
    "user": "u12_SpN0rtXKgF",
    "password": "PMlN.dTOwRm=@LyLeU9S^v0m",
    "database": "s12_Reaction-roles"
}

# Connect to the Perma-bans database
perma_bans_conn = mysql.connector.connect(
    host="db.mena1.oinkdom.xyz",
    user="u12_XH191wWsP7",
    password="o@uAmlPG1!kuA^bDsGMR@aFT",
    database="s12_Perma-bans"
)
perma_bans_cursor = perma_bans_conn.cursor()

banned_users_set = set()

def load_banned_users():
    perma_bans_cursor.execute("SELECT user_id FROM banned_users")
    banned_users_set.update(user_id for (user_id,) in perma_bans_cursor.fetchall())

# Connect to the Exempt-roles database
exempt_roles_conn = mysql.connector.connect(
    host="db.mena1.oinkdom.xyz",
    user="u12_OFRPmnUnJH",
    password="koy5KbO=Y7Ki@IgopjxuIKh=",
    database="s12_Exempt-roles"
)
exempt_roles_cursor = exempt_roles_conn.cursor()

# Function to load exempt roles for a guild from the database to a set
def load_exempt_roles(guild_id):
    exempt_roles_cursor.execute("SELECT role_id FROM exempt_roles WHERE guild_id = %s", (guild_id,))
    return {role_id for (role_id,) in exempt_roles_cursor.fetchall()}

#define the IDs
servers = [1083830428953219202] #Replace with the ID of your guild
co_moderator_role_id = 1106713868635488266 # Replace with the ID of the Co-Moderator role
moderator_role_id = 1083845849815203891 # Replace with the ID of the Moderator role
mod_application_channel_id = 1106310873351458886 # Replace with the ID of the mod-application channel
logs_channel = 1083830429389430866 #Replace with the ID of the logs channel
unverified_role_id = 1089510673114988544 #Replace with the ID of the Unverified role

@bot.slash_command(name="help", description="Shows the available commands.")
async def help(ctx):
    embed = discord.Embed(title="Help", description="Hi, my name is Oinky.exe! Here are the available commands:")
    response = await ctx.defer()
    
    # Get all the registered slash commands
    commands = await bot.http.get_global_commands(bot.user.id)
    commands_dict = {command['name']: command['description'] for command in commands}

    for name, description in commands_dict.items():
        embed.add_field(name=name, value=description, inline=False)

    await ctx.send(embed=embed)

async def send_mod_application_embed(user, timezone, country, region, city, reason):
    embed = discord.Embed(
        title="Co-Moderator Application",
        description="The user below has applied for the Co-Moderator role.",
        color=discord.Color.blue()
    )
    embed.set_author(
        name=user.name,
        icon_url=user.display_avatar.url
    )
    embed.add_field(
        name="Timezone",
        value=timezone
    )
    embed.add_field(
        name="Country",
        value=country
    )
    embed.add_field(
        name="Region",
        value=region
    )
    embed.add_field(
        name="City",
        value=city
    )
    embed.add_field(
        name="Reason for Applying",
        value=reason
    )
    embed.set_footer(text="React with ✅ to approve, or ❌ to reject.")
    mod_application_channel = bot.get_channel(1106310873351458886) # Replace with the ID of the channel where you want to send the application
    message = await mod_application_channel.send(embed=embed)
    return message

@bot.slash_command(debug_guilds=servers, name="apply", description="Apply for the Co-Moderator role.", defer=True, timeout=10)
async def apply(ctx, timezone: Option(str, description="The timezone you are located in", required=True), country: Option(str, description="The country you are located in", required=True), region: Option(str, description="The region you are located in", required=True), city: Option(str, description="The city you are located in", required=True), reason: Option(str, description="The reason why you want to become a Co-Moderator", required=True)):
    # Convert timezone string to a timedelta object
    offset_str = timezone.split()[0]
    if offset_str[0] == "+":
        offset = datetime.timedelta(hours=int(offset_str[1:3]), minutes=int(offset_str[3:]))
    else:
        offset = datetime.timedelta(hours=-int(offset_str[1:3]), minutes=-int(offset_str[3:]))
    
    # Get Co-Moderator role
    co_moderator_role = ctx.guild.get_role(co_moderator_role_id)
    
    # Calculate the expiration date for the Co-Moderator role
    expiration_date = datetime.datetime.now(datetime.timezone(offset)) + datetime.timedelta(weeks=3)

    # Schedule a task to remove the Co-Moderator role after 3 weeks
    async def remove_co_moderator_role():
        await asyncio.sleep((expiration_date - datetime.datetime.now(datetime.timezone(offset))).total_seconds())
        await ctx.author.remove_roles(co_moderator_role)
        moderator_role = ctx.guild.get_role(moderator_role_id)
        await ctx.author.add_roles(moderator_role)

    bot.loop.create_task(remove_co_moderator_role())
    
    # Send the moderator application embed and wait for moderator approval/rejection
    await ctx.send(f"{ctx.author.mention} Your Mod application has been submitted and waiting approval, I'll try keep you up-to-date!")
    message = await send_mod_application_embed(ctx.author, timezone, country, region, city, reason)
    await message.add_reaction("✅")
    await message.add_reaction("❌")

    def check(reaction, user):
        return str(reaction.emoji) in ['✅', '❌'] and reaction.message.id == message.id and user.id != ctx.bot.user.id

    try:
        reaction, user = await bot.wait_for('reaction_add', timeout=604800, check=check)
    except (asyncio.TimeoutError, asyncio.CancelledError):
        await ctx.send(f"{ctx.author.mention} Your Co-Moderator role application has expired. Please re-apply if you're still interested.")
        return

    if str(reaction.emoji) == '✅':
        await ctx.send(f"{ctx.author.mention} Congratulations! Your Co-Moderator role application has been approved.")
        await ctx.author.add_roles(co_moderator_role)
    else:
        await ctx.send(f"{ctx.author.mention} Unfortunately, your Co-Moderator role application has been rejected.")
        return

@bot.event
async def on_member_join(member):
        unverified = discord.utils.get(member.guild.roles, id=unverified_role_id)
        await member.add_roles(unverified)

@bot.slash_command(debug_guilds=servers, name="clear", description="Clears a channel's messages")
@commands.has_permissions(manage_messages=True)
@commands.cooldown(1, 5, commands.BucketType.user)
async def clear(ctx, messages: Option(int, description="How many messages do you want to clear?", required=True)):
    try:
        z = await ctx.channel.purge(limit=messages)
        await ctx.respond(f"I have cleared {len(z)}")
    except discord.errors.NotFound:
        pass

@clear.error
async def clearerror(ctx, error):
    if isinstance(error, MissingPermissions):
        await ctx.respond("You need manage messages permissions to do this!")
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.respond(error)
    else:
        raise error

@bot.slash_command(name="setup_verification_system", debug_guilds=[servers], description="Sets up the verification system!!")
@commands.has_permissions(moderate_members = True)
async def setup_verification_system(ctx):
    message = await ctx.send("<:ServerBooster:1089309398855319592>======Verify======<:ServerBooster:1089309398855319592>\nPlease click the Checkmark bellow to get access to the server content and chat with our amazing members")
    await message.add_reaction("<:Verify:1089311271079383081>")

@bot.slash_command(debug_guilds = servers, name = 'timeout', description = "mutes/timeouts a member")
@commands.has_permissions(moderate_members = True)
async def timeout(ctx, member: Option(discord.Member, required = True), reason: Option(str, required = False), days: Option(int, max_value = 27, default = 0, required = False), hours: Option(int, default = 0, required = False), minutes: Option(int, default = 0, required = False), seconds: Option(int, default = 0, required = False)): #setting each value with a default value of 0 reduces a lot of the code
    if member.id == ctx.author.id:
        await ctx.respond("You can't timeout yourself!")
        return
    if discord.Member.guild_permissions(moderate_members = True):
        await ctx.respond("You can't do this, this person is a moderator!")
        return
    duration = timedelta(days = days, hours = hours, minutes = minutes, seconds = seconds)
    if duration >= timedelta(days = 28): #added to check if time exceeds 28 days
        await ctx.respond("I can't mute someone for more than 28 days!", ephemeral = True) #responds, but only the author can see the response
        return
    if reason == None:
        await member.timeout_for(duration)
        await ctx.respond(f"<@{member.id}> has been timed out for {days} days, {hours} hours, {minutes} minutes, and {seconds} seconds by <@{ctx.author.id}>.")
    else:
        await member.timeout_for(duration, reason = reason)
        await ctx.respond(f"<@{member.id}> has been timed out for {days} days, {hours} hours, {minutes} minutes, and {seconds} seconds by <@{ctx.author.id}> for '{reason}'.")

@timeout.error
async def timeouterror(ctx, error):
    if isinstance(error, MissingPermissions):
        await ctx.respond("You can't do this! You need to have moderate members permissions!")
    else:
        raise error

@bot.slash_command(debug_guilds = servers, name = 'unmute', description = "unmutes/untimeouts a member")
@commands.has_permissions(moderate_members = True)
async def unmute(ctx, member: Option(discord.Member, required = True), reason: Option(str, required = False)):
    if reason == None:
        await member.remove_timeout()
        await ctx.respond(f"<@{member.id}> has been untimed out by <@{ctx.author.id}>.")
    else:
        await member.remove_timeout(reason = reason)
        await ctx.respond(f"<@{member.id}> has been untimed out by <@{ctx.author.id}> for '{reason}'.")

@unmute.error
async def unmuteerror(ctx, error):
    if isinstance(error, MissingPermissions):
        await ctx.respond("You can't do this! You need to have moderate members permissions!")
    else:
        raise error

@bot.slash_command(debug_guilds = servers, name = "ban", description = "Bans a member")
@commands.has_permissions(ban_members = True, administrator = True)
async def ban(ctx, user: Option(discord.Member, description = "Who do you want to ban?"), reason: Option(str, description = "Why?", required = False)):
    if ctx.author.guild_permissions.ban_members:
        exempt_roles = load_exempt_roles(ctx.guild.id)
        if any(role.id in exempt_roles for role in user.roles):
            await ctx.send(f"{user.mention} cannot be banned due to an unbannable role.")
            return

        # Ban the user with a reason
        await user.ban(reason=reason, delete_message_days=7)

        await ctx.send(f"{user.mention} has been banned for: {reason}")
    else:
        await ctx.send("You do not have the permission to ban members.")
    
@ban.error
async def banerror(ctx, error):
    if isinstance(error, MissingPermissions):
        await ctx.respond("You need Ban Members and Administrator permissions to do this!")
    else:
        await ctx.respond("Something went wrong...") #most likely due to missing permissions
        raise error

@bot.slash_command(debug_guilds = servers, name = "kick", description = "Kicks a member")
@commands.has_permissions(kick_members = True, administrator = True)
async def kick(ctx, member: Option(discord.Member, description = "Who do you want to kick?"), reason: Option(str, description = "Why?", required = False)):
    if member.id == ctx.author.id: #checks to see if they're the same
        await ctx.respond("BRUH! You can't kick yourself!")
    elif member.resolved_permissions(administrator = True):
        await ctx.respond("Stop trying to kick an admin! :rolling_eyes:")
    else:
        if reason == None:
            reason = f"None provided by {ctx.author}"
        await member.kick(reason = reason)
        await ctx.respond(f"<@{ctx.author.id}>, <@{member.id}> has been kicked from this server!\n\nReason: {reason}")

@kick.error
async def kickerror(ctx, error):
    if isinstance(error, MissingPermissions):
        await ctx.respond("You need Kick Members and Administrator permissions to do this!")
    else:
        await ctx.respond("Something went wrong...") #most likely due to missing permissions 
        raise 

@bot.slash_command(debug_guilds=servers, name="bans", description="Get a list of members who are banned from this server!")
@commands.has_permissions(ban_members=True)
async def bans(ctx):
    await ctx.defer()
    guild = ctx.guild
    bans = [entry async for entry in guild.bans(limit=2000)]
    embed = discord.Embed(title=f"List of Banned Members in {ctx.guild}", color=discord.Colour.red())
    for entry in bans:
        if len(embed.fields) >= 25:
            break
        if len(embed) > 5900:
            embed.add_field(name="Too many bans to list", value="")
        else:
            embed.add_field(name=f"Ban", value=f"Username: {entry.user.name}#{entry.user.discriminator}\nReason: {entry.reason}\nUser ID: {entry.user.id}\nIs Bot: {entry.user.bot}", inline=False)
    await ctx.respond(embed=embed)
    
@bot.slash_command(debug_guilds=servers, name="perma_ban", description="Permanently ban a user from the server")
async def perma_ban(ctx, user: Option(discord.Member, description = "Who do you wanna permanently ban?"), reason: Option(str, description = "Why?", required = False)):
    if ctx.author.guild_permissions.ban_members:
        # Ban the user with a reason and delete the messages from the past 7 days
        await user.ban(reason=reason, delete_message_seconds=604800)

        # Add the user ID to the banned_users table for this guild
        perma_bans_cursor.execute("INSERT INTO banned_users (guild_id, user_id, reason) VALUES (%s, %s, %s)",
                                  (ctx.guild.id, user.id, reason))
        perma_bans_conn.commit()

        await ctx.send(f"{user.mention} has been permabanned")
        
@bot.slash_command(debug_guilds = servers, name = "set_unbannable_roles", description = "Adds/Removes unbannable roles to/from a database")
async def set_exempt_roles(ctx, role: Option(discord.Role, description = "Which role do you wanna add/remove")):
    if ctx.author.guild_permissions.administrator:
        # Check if the role is already exempt and toggle its status
        exempt_roles = load_exempt_roles(ctx.guild.id)
        if role.id in exempt_roles:
            exempt_roles_cursor.execute("DELETE FROM exempt_roles WHERE guild_id = %s AND role_id = %s",
                                        (ctx.guild.id, role.id))
            await ctx.send(f"{role.name} has been removed from the exempt roles.")
        else:
            exempt_roles_cursor.execute("INSERT INTO exempt_roles (guild_id, role_id) VALUES (%s, %s)",
                                        (ctx.guild.id, role.id))
            await ctx.send(f"{role.name} has been added to the exempt roles.")
        exempt_roles_conn.commit()
    else:
        await ctx.send("You do not have the permission to configure the bot settings.")
    
@bot.slash_command(debug_guilds = servers, name = "unban", description = "Unbans a member")
@commands.has_permissions(ban_members = True)
async def unban(ctx, user_id: Option(discord.Member, description = "The User ID of the person you want to unban.", required = True)):
    if ctx.guild is not None:
        if user_id not in banned_users_set:
            try:
                user = await bot.fetch_user(user_id)
                await ctx.guild.unban(user)
                await ctx.send(f"{user.name}#{user.discriminator} has been unbanned.")
            except discord.NotFound:
                await ctx.send("User not found.")
        else:
            await ctx.send("The specified user ID is in the list of permanenently banned users.")
    else:
        await ctx.send("This command cannot be used in a private message.")

@unban.error
async def unbanerror(ctx, error):
    if isinstance(error, MissingPermissions):
        await ctx.respond("You need ban members permissions to do this!")
    else: 
        await ctx.respond(f"Something went wrong, I couldn't unban this member or this member isn't banned.")
        raise error

@bot.event
async def on_message_delete(message):
    z = bot.get_channel(logs_channel)
    embed = discord.Embed(title = f"{message.author}'s Message was Deleted", description = f"Deleted Message: {message.content}\nAuthor: {message.author.mention}\nLocation: {message.channel.mention}", timestamp = datetime.datetime.now(), color = discord.Colour.red())
    embed.set_author(name = message.author.name, icon_url = message.author.display_avatar)
    await z.send(embed = embed)

@bot.event
async def on_message_edit(before, after):
    z = bot.get_channel(logs_channel)
    embed = discord.Embed(title = f"{before.author} Edited Their Message", description = f"Before: {before.content}\nAfter: {after.content}\nAuthor: {before.author.mention}\nLocation: {before.channel.mention}", timestamp = datetime.datetime.now(), color = discord.Colour.blue())
    embed.set_author(name = after.author.name, icon_url = after.author.display_avatar)
    await z.send(embed = embed)

@bot.event
async def on_member_update(before, after):
    z = bot.get_channel(logs_channel)
    if len(before.roles) > len(after.roles):
        role = next(role for role in before.roles if role not in after.roles)
        embed = discord.Embed(title = f"{before}'s Role has Been Removed", description = f"{role.name} was removed from {before.mention}.",  timestamp = datetime.datetime.now(), color = discord.Colour.red())
    elif len(after.roles) > len(before.roles):
        role = next(role for role in after.roles if role not in before.roles)
        embed = discord.Embed(title = f"{before} Got a New Role", description = f"{role.name} was added to {before.mention}.",  timestamp = datetime.datetime.now(), color = discord.Colour.green())
    elif before.nick != after.nick:
        embed = discord.Embed(title = f"{before}'s Nickname Changed", description = f"Before: {before.nick}\nAfter: {after.nick}",  timestamp = datetime.datetime.now(), color = discord.Colour.blue())
    else:
        return
    embed.set_author(name = after.name, icon_url = after.display_avatar)
    await z.send(embed = embed)

@bot.event
async def on_guild_channel_create(channel):
    z = bot.get_channel(logs_channel)
    embed = discord.Embed(title = f"{channel.name} was Created", description = channel.mention, timestamp = datetime.datetime.now(), color = discord.Colour.green())
    await z.send(embed = embed)
    
@bot.event
async def on_member_ban(guild, user):
    z = bot.get_channel(logs_channel)
    
    if z is None:
        print(f"Logs channel with ID {logs_channel} not found.")
        return
    
    embed = discord.Embed(
        title=f"{user.name} was Banned using the hammer of justice",
        description=user.mention,
        timestamp=datetime.datetime.now(),
        color=discord.Colour.red()
    )
    
    try:
        await z.send(embed=embed)
        print("Embed sent successfully.")
    except discord.Forbidden:
        print("Bot doesn't have permission to send messages in the logs channel.")
    except discord.HTTPException as e:
        print(f"An error occurred: {e}")
        
@bot.event
async def on_member_unban(guild, user):
    z = bot.get_channel(logs_channel)
    
    if z is None:
        print(f"Logs channel with ID {logs_channel} not found.")
        return
    
    embed = discord.Embed(
        title=f"{user.name} was Unbanned using the hammer of justice",
        description=user.mention,
        timestamp=datetime.datetime.now(),
        color=discord.Colour.red()
    )
    
    try:
        await z.send(embed=embed)
        print("Embed sent successfully.")
    except discord.Forbidden:
        print("Bot doesn't have permission to send messages in the logs channel.")
    except discord.HTTPException as e:
        print(f"An error occurred: {e}")

@bot.event
async def on_guild_channel_delete(channel):
    z = bot.get_channel(logs_channel)
    embed = discord.Embed(title = f"{channel.name} was Deleted", timestamp = datetime.datetime.now(), color = discord.Colour.red())
    await z.send(embed = embed)
    
# Function to add reaction role to the database
def add_reaction_role(guild_id, message_id, emoji, role_id):
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    try:
        cursor.execute("INSERT INTO reaction_roles (guild_id, message_id, emoji, role_id) VALUES (%s, %s, %s, %s)",
                       (guild_id, message_id, emoji, role_id))
        conn.commit()
    except mysql.connector.Error as err:
        print(f"Error: {err}")

    cursor.close()
    conn.close()

# Slash command to add a reaction role
@bot.slash_command(name="reactionroles", description="Create reaction roles.")
async def add_reaction_role_slash(ctx, message_id: str, emoji: str, role: discord.Role):
    try:
        message_id = int(message_id)
        # Fetch the message using the message_id
        message = await ctx.fetch_message(message_id)

        # Add the reaction to the message
        await message.add_reaction(emoji)

        # Store the reaction role in the database
        add_reaction_role(ctx.guild.id, message_id, emoji, role.id)

        await ctx.send(f"Reaction role added successfully!")
    except discord.NotFound:
        await ctx.send(f"Message with ID {message_id} was not found.")
    except discord.HTTPException:
        await ctx.send("Failed to add the reaction. Please make sure the emoji is valid.")

# Event listener for on_raw_reaction_add
@bot.event
async def on_raw_reaction_add(payload):
    if not payload.guild_id:
        return

    guild = bot.get_guild(payload.guild_id)
    
    if not guild:
        return
    
    member = guild.get_member(payload.user_id)

    if not member or member.bot:
        return

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    try:
        # Retrieve the role associated with the reacted emoji from the database
        cursor.execute("SELECT role_id FROM reaction_roles WHERE guild_id = %s AND message_id = %s AND emoji = %s",
                       (payload.guild_id, payload.message_id, str(payload.emoji)))
        row = cursor.fetchone()

        if row:
            # Get the role object using the role_id and add it to the member
            role = guild.get_role(row[0])

            if role:
                await member.add_roles(role)       
    except mysql.connector.Error as err:
         print(f"Error: {err}")

@bot.event
async def on_raw_reaction_remove(payload):
    if not payload.guild_id:
        return

    guild = bot.get_guild(payload.guild_id)
    
    if not guild:
        return
    
    member = guild.get_member(payload.user_id)

    if not member or member.bot:
        return

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    try:
        # Retrieve the role associated with the reacted emoji from the database
        cursor.execute("SELECT role_id FROM reaction_roles WHERE guild_id = %s AND message_id = %s AND emoji = %s",
                       (payload.guild_id, payload.message_id, str(payload.emoji)))
        row = cursor.fetchone()

        if row:
            # Get the role object using the role_id and add/remove it from the member
            role = guild.get_role(row[0])

            if role:
                await member.remove_roles(role)      
    except mysql.connector.Error as err:
         print(f"Error: {err}")
        
the_roles_db = {
    "host": "db.mena1.oinkdom.xyz",
    "user": "u12_KhGX5mYZy9",
    "password": "!HqYhj=5s!IntD1wjM6eJiq5",
    "database": "s12_The-Roles-DB"
}

def get_user_roles(user_id, guild_id):
     conn = mysql.connector.connect(
         host=the_roles_db["host"],
         user=the_roles_db["user"],
         password=the_roles_db["password"],
         database=the_roles_db["database"]
     )
  
     cursor = conn.cursor()
    
     query = "SELECT role_id FROM user_roles WHERE user_id=%s AND guild_id=%s"
    
     cursor.execute(query, (user_id, guild_id))
    
     result = [row[0] for row in cursor.fetchall()]
   
     cursor.close()
     conn.close()
     
     return result

def remove_user_roles(user_id, guild_id):
    conn = mysql.connector.connect(
        host=the_roles_db["host"],
        user=the_roles_db["user"],
        password=the_roles_db["password"],
        database=the_roles_db["database"]
    )
  
    cursor = conn.cursor()
    
    query = "DELETE FROM user_roles WHERE user_id=%s AND guild_id=%s"
    
    cursor.execute(query, (user_id, guild_id))
   
   # Close the cursor and connection properly
    cursor.close()
    conn.commit()
    conn.close()

## Function to add/update stored role IDs for a given user and guild in the database
def add_user_roles(user_id, guild_id, role_id):
    conn = mysql.connector.connect(**the_roles_db)
    cursor = conn.cursor()

    try:
        sql_query = """
            INSERT INTO user_roles (user_id, guild_id, role_id)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE role_id=%s;
        """

        joined_role_id_strg = ','.join(role_id)  # Convert list of IDs into comma-separated string
        data_tuple = (str(user_id), str(guild_id), joined_role_id_strg, joined_role_id_strg)

        cursor.execute(sql_query, data_tuple)

        conn.commit()

    except mysql.connector.Error as err:
        print(f"Error: {err}")

    finally:
        cursor.close()
        conn.close()

@bot.event
async def on_member_join(member):
    # Check if user ID exists in database
    stored_role_id = get_user_roles(member.id, member.guild.id)
    
    # If there are stored role IDs for this user, add them to the member
    if stored_role_id:
        for role_id in stored_role_id:
            try:
                role = discord.utils.get(member.guild.roles, id=int(role_id))
                if role:
                    await member.add_roles(role)
                else:
                    print(f"Role with ID {role_id} not found in the server. Skipping...")
            except ValueError:  # Handle invalid integer conversion for non-numeric or invalid IDs
                print(f"Invalid Role ID: {role_id}")

        remove_user_roles(member.id, member.guild.id)  # Optionally remove stored roles after adding them

    await sleep(10)

    for channel in member.guild.channels:
        if channel.name.startswith('Oinks:'):
            await channel.edit(name=f'Oinks: {member.guild.member_count}')
            break

@bot.event
async def on_member_remove(member):
    # Fetch the roles of the member before they leave
    role_id = [str(role.id) for role in member.roles]

    # Store the roles in the database for future reference
    add_user_roles(member.id, member.guild.id, role_id)

    await sleep(10)
    for channel in member.guild.channels:
        if channel.name.startswith('Oinks:'):
            await channel.edit(name=f'Oinks: {member.guild.member_count}')
            break
        
@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="over the server"))
    print('-----------------------------------------------------')
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('-----------------------------------------------------')

bot.run('MTA5NTA4NTUyNjc3MzY3ODEwMA.Gy6cFR.QonF9Eb8QU08-iPfa3-nKQwN3tOEhwZY4en4o4')

