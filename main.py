from config import *
import discord
from discord import Game, Channel
import asyncio
import logging
from urllib.request import urlopen
import urllib.parse
import json
import mysql.connector
import subprocess
import time
import datetime

client = discord.Client()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('SilverleafBot')

def connectMySQL():
    """ Connect to MySQL database """
    try:
        logger.info('Connecting to database...')
        global engine
        engine = mysql.connector.connect(user=MYSQL_USERNAME, password=MYSQL_PASSWORD, host=MYSQL_IP, port=MYSQL_PORT, database=MYSQL_DATABASE, buffered=True)
        if engine.is_connected():
            logger.info('Connected to MySQL')
    except Error as e:
        logger.info(e)

def getRadioMeta():
    response = urlopen('http://radio.pawprintradio.com/status-json.xsl')
    xsl = response.read()
    mfr_json = json.loads(str(xsl.decode("utf-8")))
    mfr_json = mfr_json["icestats"]["source"]
    mfr_json.pop()
    return mfr_json.pop()

@client.event
async def on_ready():
    connectMySQL()
    print('------')
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')
    radioMeta = ""
    while True:
        mfr_json = getRadioMeta()
        text = str(mfr_json["title"])
        if text != radioMeta:
            radioMeta = text
            status = Game(name=text)
            await client.change_status(game=status, idle=False)
        await asyncio.sleep(10)

@client.event
async def on_message(message):
    if message.content.startswith('!help') or message.content.startswith('!commands'):
        await client.send_typing(message.channel)
        commands = """**List of commands:**
        `!help` - displays this help menu
        `!about` - general information about SilverleafBot
        `!nowplaying` - shows what is currently playing in the station
        `!listeners` - show the listener count according to Icecast
        `!queue` - lists the upcoming songs in the radio dj
        `!list (index)` - list the songs in the radio database
        `!search <query>` - search for songs that contains the string
        `!request <id>` - request the song to be played in the station
        ----------------------
        `!togglerequests` - toggle requests functionality for the bot
        `!joinvoice` - joins the voice channel with the person who sent the command
        `!disconnectvoice` - disconnect from the voice channel

        Command parameters: `<required>` `(optional)`
        """
        await client.send_message(message.channel, commands)
    elif message.content.startswith('!about'):
        await client.send_typing(message.channel)
        out = subprocess.getoutput("git rev-parse --short master")
        about = """**Silverleaf 🤖** by EndenDragon
        Git revision: `{0}` | URL: https://git.mane-frame.com/EndenDragon/silverleaf_bot/commit/{0}
        Made with :heart: for PawPrintRadio.
        http://www.pawprintradio.com/
        """.format(out)
        await client.send_message(message.channel, about)
    elif message.content.startswith('!nowplaying') or message.content.startswith('!np'):
        await client.send_typing(message.channel)
        mfr_json = getRadioMeta()
        text = "**Now Playing:** " + str(mfr_json["title"])
        await client.send_message(message.channel, text)
    elif message.content.startswith('!listeners'):
        await client.send_typing(message.channel)
        mfr_json = getRadioMeta()
        text = "**Listeners** *(According to Icecast):* " + ' _' + str(mfr_json["listeners"]) + '_'
        await client.send_message(message.channel, text)
    elif message.content.startswith('!queue'):
        await client.send_typing(message.channel)
        connectMySQL()
        cursor = engine.cursor()
        query = ("SELECT ID, songID, artist FROM queuelist")
        cursor.execute(query)
        cursorSecondary = engine.cursor()
        retMSG = "__**Upcoming Songs in the Queue**__\n[Position | ID | Artist | Title]"
        for (ID, songID, artist) in cursor:
            querySecondary = ("SELECT title FROM songs WHERE ID LIKE " + str(songID))
            cursorSecondary.execute(querySecondary)
            for title in cursorSecondary:
                t = title
            retMSG = retMSG + "\n" + str(ID) + " | " + str(songID) + " | " + str(artist) + " | " + str(title)[2:len(str(title))-3]
        await client.send_message(message.channel, retMSG)
    elif message.content.startswith('!list'):
        await client.send_typing(message.channel)
        if len(str(message.content)) >= 7:
            index = str(message.content)[str(message.content).find("!list") + 6:]
            try:
                index = abs(int(index))
            except:
                index = 1
        else:
            index = 1
        connectMySQL()
        cursor = engine.cursor()
        cursorCount = engine.cursor()
        countQuery = ("SELECT COUNT(*) FROM songs")
        cursorCount.execute(countQuery)
        count = ""
        for (x) in cursorCount:
            count = x
        count = str(count)[1:len(count)-3]
        query = ("SELECT ID, artist, title FROM songs ORDER BY `artist` LIMIT " + str((int(index) - 1) * 10) + ", 10")
        cursor.execute(query)
        await client.send_message(message.channel, "**__Song List: Page " + str(index) + " of " + str(round(int(count)/10)) + "__**")
        await client.send_typing(message.channel)
        await client.send_message(message.channel, "[ID | Artist | Title]")
        text = ""
        await client.send_typing(message.channel)
        for (ID, artist, title) in cursor:
            text = text + "**" + str(ID) + "** | " + artist + " | " + title + "\n"
        await client.send_message(message.channel, text)
        cursor.close()
    elif message.content.startswith('!search'):
        await client.send_typing(message.channel)
        if len(str(message.content)) == 7:
            await client.send_message(message.channel, "**I'm sorry, what was that? Didn't quite catch that.** \n Please enter your search query after the command. \n eg. `!search Rainbow Dash`")
        else:
            connectMySQL()
            cursor = engine.cursor()
            query = str(message.content)[8:]
            command = ("SELECT ID, artist, title FROM songs WHERE `artist` COLLATE UTF8_GENERAL_CI LIKE '%%" + str(query) + "%%' OR `title` COLLATE UTF8_GENERAL_CI LIKE '%%" + str(query) + "%%' LIMIT 15")
            cursor.execute(command)
            await client.send_message(message.channel, "**__Search Songs: " + query + "__**")
            await client.send_message(message.channel, "[ID | Artist | Title]")
            text = ""
            for (ID, artist, title) in cursor:
                await client.send_typing(message.channel)
                text = text + "**" + str(ID) + "** | " + artist + " | " + title + "\n"
            await client.send_message(message.channel, text)
            cursor.close()
    elif message.content.startswith('!request') or message.content.startswith('!req'):
        await client.send_typing(message.channel)
        if (len(str(message.content)) == 8 and message.content.startswith('!request')) or (len(str(message.content)) == 4 and message.content.startswith('!req')):
            await client.send_message(message.channel, "**I just don't know what went wrong!** \n Please enter your requested song id after the command. \n eg. `!request 14982` \n _Remember: you can search for the song with the `!search` command!_")
        else:
            if REQUESTS_ENABLED == True:
                if message.content.startswith('!request'):
                    reqSONGID = str(message.content)[9:]
                else:
                    reqSONGID = str(message.content)[5:]
                reqUSERNAME = str(message.author.name)
                connectMySQL()
                cursorSong = engine.cursor()
                songQuery = ("SELECT ID, artist, title FROM songs WHERE `ID` LIKE  " + str(int(reqSONGID)))
                cursorSong.execute(songQuery)
                x = None
                for (ID, artist, title) in cursorSong:
                    x = "(#" + str(ID) + ") " + title + ", by " + artist
                if x == None:
                    await client.send_message(message.channel, "I'm sorry, this song does not exist in the database!")
                else:
                    data = {
                        'reqSONGID' : reqSONGID,
                        'reqUSERNAME' : reqUSERNAME
                    }
                    data = bytes( urllib.parse.urlencode( data ).encode() )
                    handler = urllib.request.urlopen( REQUESTS_POST_URL, data );
                    results = handler.read().decode( 'utf-8' )
                    if str(results) == "1":
                        await client.send_message(message.channel, "Good news " + reqUSERNAME + "! Your song of: **" + x + "** has been submitted! Rest assured, keep listening to the radio as your song might be played after the next few songs!")
                    else:
                        await client.send_message(message.channel, results)
            else:
                await client.send_message(message.channel, "I'm sorry, but requests are disabled for the moment!")
    elif message.content.startswith('!togglerequests'):
        await client.send_typing(message.channel)
        if int(str(message.author.id)) in BOT_ADMINS:
            global REQUESTS_ENABLED
            REQUESTS_ENABLED = not REQUESTS_ENABLED
            await client.send_message(message.channel, "**REQUESTS ENABLED:** " + str(REQUESTS_ENABLED))
        else:
            await client.send_message(message.channel, "I'm sorry, this is an **admin only** command!")
    elif message.content.startswith('!joinvoice') or message.content.startswith('!jv'):
        await client.send_typing(message.channel)
        if int(str(message.author.id)) in BOT_ADMINS:
            c = discord.utils.get(message.server.channels, id=message.author.voice_channel.id)
            global v
            v = await client.join_voice_channel(c)
            await client.send_message(message.channel, "Successfully joined the voice channel!")
            player = v.create_ffmpeg_player("http://radio.pawprintradio.com/stream-128.mp3")
            player.start()
        else:
            await client.send_message(message.channel, "I'm sorry, this is an **admin only** command!")
    elif message.content.startswith('!disconnectvoice'):
        await client.send_typing(message.channel)
        if int(str(message.author.id)) in BOT_ADMINS:
            await v.disconnect()
            await client.send_message(message.channel, "Successfully disconnected from the voice channel!")
        else:
            await client.send_message(message.channel, "I'm sorry, this is an **admin only** command!")

if BOT_USE_EMAIL:
    client.run(DISCORD_BOT_EMAIL, DISCORD_BOT_PASSWORD)
else:
    client.run(DISCORD_BOT_TOKEN)
