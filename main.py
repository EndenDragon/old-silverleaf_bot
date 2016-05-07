from config import *
import discord
from discord import Game, Channel
import asyncio
import logging
from urllib.request import urlopen
import json
import mysql.connector
import subprocess
import time
import datetime

client = discord.Client()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('SilverleafBot')

engine = mysql.connector.connect(user=MYSQL_USERNAME, password=MYSQL_PASSWORD, host=MYSQL_IP, port=MYSQL_PORT, database=MYSQL_DATABASE)
logger.info('Connecting to database...')
connection = engine.connect()

def getRadioMeta():
    response = urlopen('http://radio.pawprintradio.com/status-json.xsl')
    xsl = response.read()
    mfr_json = json.loads(str(xsl.decode("utf-8")))
    mfr_json = mfr_json["icestats"]["source"]
    mfr_json.pop()
    return mfr_json.pop()

@client.event
async def on_ready():
    print('------')
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')
    while True:
        mfr_json = getRadioMeta()
        text = str(mfr_json["title"])
        status = Game(name=text)
        await client.change_status(game=status, idle=False)
        await asyncio.sleep(10)

@client.event
async def on_message(message):
    if message.content.startswith('!help') or message.content.startswith('!commands'):
        commands = """**List of commands:**
        `!help` - displays this help menu
        `!about` - general information about SilverleafBot
        `!nowplaying` - shows what is currently playing in the station
        `!listeners` - show the listener count according to Icecast
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
        out = subprocess.getoutput("git rev-parse --short master")
        about = """**SilverleafBot** by EndenDragon
        Git revision: `{0}` | URL: https://git.mane-frame.com/EndenDragon/silverleaf_bot/commit/{0}
        Made with :heart: for PawPrintRadio.
        http://www.pawprintradio.com/
        """.format(out)
        await client.send_message(message.channel, about)
    elif message.content.startswith('!nowplaying') or message.content.startswith('!np'):
        mfr_json = getRadioMeta()
        text = "**Now Playing:** " + str(mfr_json["title"])
        await client.send_message(message.channel, text)
    elif message.content.startswith('!listeners'):
        mfr_json = getRadioMeta()
        text = "**Listeners** *(According to Icecast):* " + ' _' + str(mfr_json["listeners"]) + '_'
        await client.send_message(message.channel, text)
    elif message.content.startswith('!list'):
        if len(str(message.content)) >= 7:
            index = str(message.content)[str(message.content).find("!list") + 6:]
            try:
                index = abs(int(index))
            except:
                index = 1
        else:
            index = 1
        cursor = engine.cursor()
        cursorCount = engine.cursor(prepared=True)
        countQuery = ("SELECT COUNT(*) FROM songs")
        cursorCount.execute(countQuery)
        count = ""
        for (x) in cursorCount:
            count = x
        count = str(count)[1:len(count)-3]
        query = ("SELECT ID, artist, title FROM songs ORDER BY `artist` LIMIT " + str((int(index) - 1) * 10) + ", 10")
        cursor.execute(query)
        await client.send_message(message.channel, "**__Song List: Page " + str(index) + " of " + str(round(int(count)/10)) + "__**")
        await client.send_message(message.channel, "[ID | Artist | Title]")
        text = ""
        for (ID, artist, title) in cursor:
            text = text + "**" + str(ID) + "** | " + artist + " | " + title + "\n"
        await client.send_message(message.channel, text)
        cursor.close()
    elif message.content.startswith('!search'):
        if len(str(message.content)) == 7:
            await client.send_message(message.channel, "**I'm sorry, what was that? Didn't quite catch that.** \n Please enter your search query after the command. \n eg. `!search Rainbow Dash`")
        else:
            cursor = engine.cursor()
            query = str(message.content)[8:]
            command = ("SELECT ID, artist, title FROM songs WHERE `artist` COLLATE UTF8_GENERAL_CI LIKE '%%" + str(query) + "%%' OR `title` COLLATE UTF8_GENERAL_CI LIKE '%%" + str(query) + "%%' LIMIT 15")
            cursor.execute(command)
            await client.send_message(message.channel, "**__Search Songs: " + query + "__**")
            await client.send_message(message.channel, "[ID | Artist | Title]")
            text = ""
            for (ID, artist, title) in cursor:
                text = text + "**" + str(ID) + "** | " + artist + " | " + title + "\n"
            await client.send_message(message.channel, text)
            cursor.close()
    elif message.content.startswith('!request'):
        if len(str(message.content)) == 8:
            await client.send_message(message.channel, "**I just don't know what went wrong!** \n Please enter your requested song id after the command. \n eg. `!request 14982` \n _Remember: you can search for the song with the `!search` command!_")
        else:
            if REQUESTS_ENABLED == True:
                cursor = engine.cursor()
                reqIP = "DISCORDAPP"
                reqSONGID = str(message.content)[9:]
                reqUSERNAME = str(message.author.nick)
                reqTIMESTAMP = str(datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S'))
                reqMSG = ""
                cursorSong = engine.cursor()
                songQuery = ("SELECT ID, artist, title FROM songs WHERE `ID` LIKE  " + str(int(reqSONGID)))
                cursorSong.execute(songQuery)
                x = None
                for (ID, artist, title) in cursorSong:
                    x = "(#" + str(ID) + ") " + title + ", by " + artist
                if x == None:
                    await client.send_message(message.channel, "I'm sorry, this song does not exist in the database!")
                else:
                    cursorSong2 = engine.cursor()
                    songQuery2 = ("""SELECT ID FROM queuelist WHERE `songID` LIKE """ + str(reqSONGID))
                    cursorSong2.execute(songQuery2)
                    for (ID) in cursorSong2:
                        if str(ID) == str(reqSONGID):
                            await client.send_message(message.channel, "The song you had requested is already in queue. Don't worry, as your song might be after within the next few songs.")
                            return
                    cursor = engine.cursor()
                    query = ("""INSERT INTO `requests` (`songID`, `username`, `userIP`, `message`, `requested`) VALUES (""" + str(reqSONGID) + """, '""" + reqUSERNAME + """', '""" + reqIP + """', '""" + reqMSG + """', '""" + reqTIMESTAMP + """');""")
                    cursor.execute(query)
                    await client.send_message(message.channel, "Good news " + reqUSERNAME + "! Your song of: **" + x + "** has been submitted! Rest assured, keep listening to the radio as your song might be played after the next few songs!")
            else:
                await client.send_message(message.channel, "I'm sorry, but requests are disabled for the moment!")
    elif message.content.startswith('!togglerequests'):
        if int(str(message.author.id)) in BOT_ADMINS:
            global REQUESTS_ENABLED
            REQUESTS_ENABLED = not REQUESTS_ENABLED
            await client.send_message(message.channel, "**REQUESTS ENABLED:** " + str(REQUESTS_ENABLED))
    elif message.content.startswith('!joinvoice'):
        if int(str(message.author.id)) in BOT_ADMINS:
            c = discord.utils.get(message.server.channels, id=message.author.voice_channel.id)
            global v
            v = await client.join_voice_channel(c)
            player = v.create_ffmpeg_player("http://radio.pawprintradio.com/stream-128.mp3")
            player.start()
    elif message.content.startswith('!disconnectvoice'):
        if int(str(message.author.id)) in BOT_ADMINS:
            await v.disconnect()
client.run(DISCORD_BOT_EMAIL, DISCORD_BOT_PASSWORD)
