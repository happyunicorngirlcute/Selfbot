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

async function startVoiceLoop() {
    while (true) {
        try {
            const channel = await client.channels.fetch(VOICE_CHANNEL_ID);
            if (!channel) {
                console.log("[voice] Voice channel not found — retrying in 10s");
                await new Promise((resolve) => setTimeout(resolve, 10000));
                continue;
            }

            console.log(`[voice] Joining voice channel ${channel.name} (${channel.id})...`);
            await streamer.joinVoice(channel.guild.id, channel.id);
            console.log("[voice] Joined voice channel successfully!");

            try {
                if (typeof client.signalVideo === "function") {
                    await client.signalVideo(channel.guild.id, channel.id, true);
                }
            } catch (e) {}

            // Background stream loop
            let streamActive = true;
            (async () => {
                const mediaToStream = fs.existsSync(COMBINED_PATH) ? COMBINED_PATH : GIF_PATH;
                while (streamActive && streamer.voiceConnection && streamer.voiceConnection.voiceChannelId) {
                    try {
                        const { command, output } = prepareStream(mediaToStream, {
                            videoCodec: "VP8",
                            noTranscoding: true,
                        });
                        command.on("error", () => {});
                        await playStream(output, streamer);
                        await new Promise((resolve) => setTimeout(resolve, 1000));
                    } catch (e) {
                        await new Promise((resolve) => setTimeout(resolve, 3000));
                    }
                }
            })();

            // Monitor voice connection (classic voice_loop pattern)
            while (streamer.voiceConnection && streamer.voiceConnection.voiceChannelId === VOICE_CHANNEL_ID) {
                await new Promise((resolve) => setTimeout(resolve, 5000));
            }

            console.log("[voice] Disconnected or kicked from voice channel — rejoining in 3s...");
            streamActive = false;
            try { streamer.stopStream(); } catch (e) {}
            await new Promise((resolve) => setTimeout(resolve, 3000));

        } catch (err) {
            console.error("[voice] Connection error:", err.message || err);
            await new Promise((resolve) => setTimeout(resolve, 10000));
        }
    }
}

client.on("ready", async () => {
    console.log(`[streamer] Logged in as ${client.user.tag}`);
    ensureCombinedMedia();
    
    // Listen for voice state changes to break the connection loop instantly on kick
    client.on("voiceStateUpdate", (oldState, newState) => {
        const userId = oldState.id || (oldState.member && oldState.member.id);
        if (userId === client.user.id && oldState.channelId && !newState.channelId) {
            console.log("[voice] Kicked from voice channel event received!");
            try {
                if (streamer.voiceConnection) {
                    delete streamer.voiceConnection.voiceChannelId;
                }
            } catch (e) {}
        }
    });

    startVoiceLoop();
});

client.login(TOKEN);
