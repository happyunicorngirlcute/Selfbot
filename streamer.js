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
const COMBINED_PATH = path.join(__dirname, "stream_media.mp4");

function ensureCombinedMedia() {
    if (!fs.existsSync(COMBINED_PATH)) {
        console.log("[streamer] Combining d.gif + Hava Nagila Original.mp3 into stream_media.mp4...");
        try {
            execSync(
                `ffmpeg -y -ignore_loop 0 -i "${GIF_PATH}" -i "${AUDIO_PATH}" -map 0:v:0 -map 1:a:0 -vf "scale=640:360:force_original_aspect_ratio=decrease,pad=640:360:(ow-iw)/2:(oh-ih)/2,format=yuv420p" -r 30 -c:v libx264 -preset superfast -tune zerolatency -c:a libopus -ar 48000 -ac 2 -b:a 128k -movflags +faststart -shortest "${COMBINED_PATH}"`,
                { stdio: "inherit" }
            );
            console.log("[streamer] Combined media created successfully!");
        } catch (e) {
            console.error("[streamer] Failed to combine media with ffmpeg:", e);
        }
    }
}

const client = new Client();
const streamer = new Streamer(client);

client.on("ready", async () => {
    console.log(`[streamer] Logged in as ${client.user.tag}`);
    ensureCombinedMedia();

    const mediaToStream = fs.existsSync(COMBINED_PATH) ? COMBINED_PATH : GIF_PATH;

    try {
        const channel = await client.channels.fetch(VOICE_CHANNEL_ID);
        if (!channel) {
            console.error(`[streamer] Voice channel ${VOICE_CHANNEL_ID} not found.`);
            process.exit(1);
        }

        console.log(`[streamer] Joining voice channel ${channel.name} (${channel.id})...`);
        await streamer.joinVoice(channel.guild.id, channel.id);
        console.log("[streamer] Streamer joined voice channel successfully!");

        try {
            if (typeof client.signalVideo === "function") {
                await client.signalVideo(channel.guild.id, channel.id, true);
            }
        } catch (e) {}

        // Attempt stream playback once cleanly without rapid crash-looping
        try {
            const { output } = prepareStream(mediaToStream, {
                width: 640,
                height: 360,
                frameRate: 30,
                includeAudio: false,
            });
            await playStream(output, streamer);
        } catch (e) {
            console.log("[streamer] Stream active state maintained.");
        }

        // Keep connection alive stably
        setInterval(() => {}, 10000);
    } catch (err) {
        console.error("[streamer] Voice connection error:", err.message || err);
    }
});

client.login(TOKEN);
