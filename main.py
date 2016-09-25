from config import *
import discord
from discord import Game, Channel, Server
import asyncio
import logging
from urllib.request import urlopen
import urllib.parse
import json
import subprocess
import time
import datetime
import sys

client = discord.Client()
logging.basicConfig(filename='silverleafbot.log',level=logging.INFO,format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
logger = logging.getLogger('SilverleafBot')

currentDate = datetime.datetime.now().date()
streamingURL = ""
currentlyStreaming = False

def getRadioMeta():
    response = urlopen('https://pawprintradio.com/update_radio_subtxt/json')
    xsl = response.read()
    mfr_json = json.loads(str(xsl.decode("utf-8")))
    return mfr_json

def getReqSongs(count=False):
    songListEndpoint = "https://radio.pawprintradio.com/api/requests/1/list"
    response = urlopen(songListEndpoint).read()
    response = json.loads(str(response.decode("utf-8")))
    response = response["result"]
    if count:
        return len(response)
    return response

def submitReqSong(id):
    songListEndpoint = "https://radio.pawprintradio.com/api/requests/1/submit/" + str(id) + "?key=" + AZURACAST_API_KEY
    try:
        response = urlopen(songListEndpoint).read()
    except urllib.error.HTTPError as error:
        response = error.read()
    response = json.loads(str(response.decode("utf-8")))
    if response["status"] == "success":
        return {'status': True}
    return {'status': False, 'error': response["error"]}

@client.event
async def on_ready():
    print('------')
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('')
    print('It is currently ' + str(currentDate))
    print('')
    print('Connected servers')
    for x in client.servers:
        print(x.name)
    print('------')
    radioMeta = ""
    global currentlyStreaming
    currentlyStreaming = False
    c = discord.utils.get(client.get_server(str(MAIN_SERVER)).channels, id=str(MUSIC_CHANNEL), type=discord.ChannelType.voice)
    global v
    v = await client.join_voice_channel(c)
    player = v.create_ffmpeg_player(MUSIC_STREAM_URL)
    player.start()
    while True:
        if currentDate != datetime.datetime.now().date():
            await client.logout()
            sys.exit("Bot Shutting Down... (Daily Restart)")
        mfr_json = getRadioMeta()
        text = str(mfr_json["text"])
        if text != radioMeta:
            radioMeta = text
            global currentlyStreaming
            if currentlyStreaming:
                global streamingURL
                status = Game(name=text, url=streamingURL, type=1)
            else:
                global streamingURL
                status = Game(name=text, type=0)
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
        ~~`!queue` - lists the upcoming songs in the radio dj~~
        `!list (index)` - list the songs in the radio database
        `!search <query>` - search for songs that contains the string
        `!request <id>` - request the song to be played in the station
        ----------------------
        `!togglerequests` - toggle requests functionality for the bot
        `!stream <Twitch Name/off> (username)` - Twitch streaming, username optional
        `!joinvoice` - joins the voice channel with the person who sent the command
        `!disconnectvoice` - disconnect from the voice channel
        `!changeavatar <URL>` - change the bot's avatar to the url
        `!restart` - restarts the bot

        Command parameters: `<required>` `(optional)`
        """
        await client.send_message(message.channel, commands)
    elif message.content.startswith('!about'):
        await client.send_typing(message.channel)
        out = subprocess.getoutput("git rev-parse --short master")
        about = """**Silverleaf 🤖** by EndenDragon
        Git revision: `{0}` | URL: https://git.pawprintradio.com/EndenDragon/silverleaf_bot/commit/{0}
        Made with :heart: for PawPrintRadio.
        http://www.pawprintradio.com/
        """.format(out)
        await client.send_message(message.channel, about)
    elif message.content.startswith('!nowplaying') or message.content.startswith('!np'):
        await client.send_typing(message.channel)
        mfr_json = getRadioMeta()
        text = "**Now Playing:** " + str(mfr_json["text"])
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
        count = getReqSongs(count=True)
        await client.send_message(message.channel, "**__Song List: Page " + str(index) + " of " + str(round(int(count)/10)) + "__**")
        await client.send_typing(message.channel)
        await client.send_message(message.channel, "[ID | Artist | Title]")
        text = ""
        await client.send_typing(message.channel)
        t = getReqSongs()
        t = t[(int(float(index)) - 1) * 10:(int(float(index)) - 1)*10+10]
        for x in t:
            text = text + "**" + str(x["request_song_id"]) + "** | " + x["song"]["artist"] + " | " + x["song"]["title"] + "\n"
        await client.send_message(message.channel, text)
    elif message.content.startswith('!search'):
        await client.send_typing(message.channel)
        if len(str(message.content)) == 7:
            await client.send_message(message.channel, "**I'm sorry, what was that? Didn't quite catch that.** \n Please enter your search query after the command. \n eg. `!search Rainbow Dash`")
        else:
            query = str(message.content)[8:]
            await client.send_message(message.channel, "**__Search Songs: " + query + "__**")
            await client.send_message(message.channel, "[ID | Artist | Title]")
            text = ""
            await client.send_typing(message.channel)
            count = 0
            for x in getReqSongs():
                if query.lower() in x["song"]["title"].lower() or query.lower() in x["song"]["artist"].lower() and count < 6:
                    text = text + "**" + str(x["request_song_id"]) + "** | " + x["song"]["artist"] + " | " + x["song"]["title"] + "\n"
                    count = count + 1
            await client.send_message(message.channel, text)
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
                a = None
                for x in getReqSongs():
                    if int(float(reqSONGID)) == int(float(x["request_song_id"])):
                        a = "(#" + str(x["request_song_id"]) + ") " + x["song"]["title"] + ", by " + x["song"]["artist"]
                if a == None:
                    await client.send_message(message.channel, "I'm sorry, this song does not exist in the database!")
                else:
                    data = {
                        'reqSONGID' : reqSONGID
                    }
                    post = submitReqSong(reqSONGID)
                    if post['status'] == True:
                        await client.send_message(message.channel, "Good news " + str(message.author.name) + "! Your song of: **" + a + "** has been submitted! Rest assured, keep listening to the radio as your song might be played after the next few songs!")
                    else:
                        await client.send_message(message.channel, post['error'])
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
        if int(str(message.author.id)) in BOT_ADMINS or int(str(message.author.voice_channel.id)) in TRUSTED_VOICE_CHANNELS:
            c = discord.utils.get(message.server.channels, id=message.author.voice_channel.id)
            global v
            v = await client.join_voice_channel(c)
            await client.send_message(message.channel, "Successfully joined the voice channel!")
            player = v.create_ffmpeg_player(MUSIC_STREAM_URL)
            player.start()
        else:
            await client.send_message(message.channel, "I'm sorry, this is an **admin only** command!")
    elif message.content.startswith('!disconnectvoice') or message.content.startswith('!dv'):
        await client.send_typing(message.channel)
        if int(str(message.author.id)) in BOT_ADMINS:
            await v.disconnect()
            await client.send_message(message.channel, "Successfully disconnected from the voice channel!")
        else:
            await client.send_message(message.channel, "I'm sorry, this is an **admin only** command!")
    elif message.content.startswith('!changeavatar'):
        await client.send_typing(message.channel)
        if int(str(message.author.id)) in BOT_ADMINS:
            f = urlopen(str(message.content)[13:])
            await client.edit_profile(avatar=f.read())
            await client.send_message(message.channel, "Successfully changed the avatar to " + str(message.content)[13:] + "!")
        else:
            await client.send_message(message.channel, "I'm sorry, this is an **admin only** command!")
    elif message.content.startswith('!restart'):
        await client.send_typing(message.channel)
        if int(str(message.author.id)) in BOT_ADMINS:
            await client.send_message(message.channel, "Silverleaf is restarting...")
            await client.logout()
            sys.exit("Bot Shutting Down... (User Invoked)")
        else:
            await client.send_message(message.channel, "I'm sorry, this is an **admin only** command!")
    elif message.content.startswith('!stream'):
        await client.send_typing(message.channel)
        if int(str(message.author.id)) in BOT_ADMINS:
            global streamingURL
            if len(message.content.split()) == 2 or len(message.content.split()) == 3:
                streamingURL = "https://www.twitch.tv/" + str(message.content.split()[1])
                mfr_json = getRadioMeta()
                text = str(mfr_json["text"])
                if str(message.content.split()[1]).lower() == "off":
                    global currentlyStreaming
                    currentlyStreaming = False
                    status = Game(name=text, type=0)
                    await client.change_status(game=status, idle=False)
                    await client.send_message(message.channel, "Stream has stopped.")
                else:
                    global currentlyStreaming
                    currentlyStreaming = True
                    status = discord.Game(name=text, url=streamingURL, type=1)
                    await client.change_status(game=status, idle=False)
                    try:
                        announChan = message.server.get_channel(str(ANNOUNCEMENT_CHANNEL_ID))
                    except:
                        announChan = None
                    if announChan is None:
                        if len(message.content.split()) == 2:
                            await client.send_message(message.channel, "Hey! **" + message.author.name + " is now streaming!** Check it out over here- " + streamingURL)
                        elif len(message.content.split()) == 3:
                            await client.send_message(message.channel, "Hey! **" + message.content.split()[2] + " is now streaming!** Check it out over here- " + streamingURL)
                    elif len(message.content.split()) == 2:
                        await client.send_message(announChan, "Hey @everyone! **" + message.author.name + " is now streaming!** Check it out over here- " + streamingURL)
                    elif len(message.content.split()) == 3:
                        await client.send_message(announChan, "Hey @everyone! **" + message.content.split()[2] + " is now streaming!** Check it out over here- " + streamingURL)
            else:
                await client.send_message(message.channel, "Invalid stream command syntax! Please enter a username or `off`.")
        else:
            await client.send_message(message.channel, "I'm sorry, this is an **admin only** command!")
    elif message.content.startswith('!hug'):
        mentions = message.mentions
        members = ""
        for x in mentions:
            members = members + " " + x.mention
        await client.send_message(message.channel, ":heartbeat: *Hugs " + members + "!* :heartbeat:")

if BOT_USE_EMAIL:
    client.run(DISCORD_BOT_EMAIL, DISCORD_BOT_PASSWORD)
else:
    client.run(DISCORD_BOT_TOKEN)
