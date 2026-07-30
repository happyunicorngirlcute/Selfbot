const WebSocket = require("ws");
global.WebSocket = WebSocket;

const { Client } = require("discord.js-selfbot-v13");
const { Streamer, prepareStream, playStream } = require("@dank074/discord-video-stream");
const { execSync } = require("child_process");
const fs = require("fs");
const path = require("path");

const TOKEN = process.env.TOKEN || "your_token_here";
const VOICE_CHANNEL_ID = process.env.VOICE_CHANNEL_ID || "1412501158689247273";

const GIF_PATH = path.join(__dirname, "d.gif");
const AUDIO_PATH = path.join(__dirname, "Hava Nagila Original.mp3");
const COMBINED_PATH = path.join(__dirname, "stream_media.webm");

function ensureCombinedMedia() {
    if (!fs.existsSync(COMBINED_PATH)) {
        console.log("[streamer] Combining d.gif + Hava Nagila Original.mp3 into stream_media.webm (VP8 + Opus)...");
        try {
            execSync(
                `ffmpeg -y -ignore_loop 0 -i "${GIF_PATH}" -i "${AUDIO_PATH}" ` +
                `-map 0:v:0 -map 1:a:0 ` +
                `-vf "scale=640:360:force_original_aspect_ratio=decrease,pad=640:360:(ow-iw)/2:(oh-ih)/2,format=yuv420p" ` +
                `-r 24 -c:v libvpx -crf 32 -b:v 500k ` +
                `-c:a libopus -ar 48000 -ac 2 -b:a 96k ` +
                `-shortest "${COMBINED_PATH}"`,
                { stdio: "inherit" }
            );
            console.log("[streamer] Combined VP8 WebM media created successfully!");
        } catch (e) {
            console.error("[streamer] Failed to combine media with ffmpeg:", e);
        }
    }
}

const client = new Client();
const streamer = new Streamer(client);

let isConnecting = false;

async function joinAndStream() {
    if (isConnecting) return;
    isConnecting = true;

    const mediaToStream = fs.existsSync(COMBINED_PATH) ? COMBINED_PATH : GIF_PATH;

    try {
        const channel = await client.channels.fetch(VOICE_CHANNEL_ID);
        if (!channel) {
            console.error(`[streamer] Voice channel ${VOICE_CHANNEL_ID} not found.`);
            isConnecting = false;
            return;
        }

        console.log(`[streamer] Joining voice channel ${channel.name} (${channel.id})...`);
        await streamer.joinVoice(channel.guild.id, channel.id);
        console.log("[streamer] Joined voice channel successfully!");

        console.log("[streamer] Starting continuous VP8 WebM stream...");
        while (true) {
            try {
                const { command, output } = prepareStream(mediaToStream, {
                    videoCodec: "VP8",
                    noTranscoding: true,
                });

                command.on("error", () => {});

                console.log("[streamer] Playing stream...");
                await playStream(output, streamer);
                await new Promise((resolve) => setTimeout(resolve, 1000));
            } catch (err) {
                await new Promise((resolve) => setTimeout(resolve, 5000));
            }
        }
    } catch (err) {
        console.error("[streamer] Voice connection error:", err.message || err);
    } finally {
        isConnecting = false;
    }
}

client.on("ready", async () => {
    console.log(`[streamer] Logged in as ${client.user.tag}`);
    ensureCombinedMedia();
    await joinAndStream();

    // Auto-reconnect if kicked or disconnected from voice channel
    client.on("voiceStateUpdate", (oldState, newState) => {
        if (oldState.id === client.user.id && !newState.channelId) {
            console.log("[streamer] Kicked or disconnected from voice channel! Reconnecting in 3s...");
            setTimeout(() => joinAndStream(), 3000);
        }
    });

    // Periodic health check every 15s to keep voice connection active
    setInterval(async () => {
        if (!streamer.voiceConnection || !streamer.voiceConnection.voiceChannelId) {
            console.log("[streamer] Disconnected check triggered. Reconnecting to voice channel...");
            await joinAndStream();
        }
    }, 15000);
});

client.login(TOKEN);
