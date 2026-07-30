const WebSocket = require("ws");
global.WebSocket = WebSocket;

const { Client } = require("discord.js-selfbot-v13");
const { Streamer, playStream } = require("@dank074/discord-video-stream");
const { spawn, execSync } = require("child_process");
const { PassThrough } = require("stream");
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
                `ffmpeg -y -ignore_loop 0 -i "${GIF_PATH}" -i "${AUDIO_PATH}" ` +
                `-map 0:v:0 -map 1:a:0 ` +
                `-vf "scale=640:360:force_original_aspect_ratio=decrease,pad=640:360:(ow-iw)/2:(oh-ih)/2,format=yuv420p" ` +
                `-r 30 -c:v libx264 -preset ultrafast -tune zerolatency ` +
                `-c:a libopus -ar 48000 -ac 2 -b:a 128k ` +
                `-movflags +faststart -shortest "${COMBINED_PATH}"`,
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
    console.log(`[streamer] Media file: ${mediaToStream} (${fs.statSync(mediaToStream).size} bytes)`);

    try {
        const channel = await client.channels.fetch(VOICE_CHANNEL_ID);
        if (!channel) {
            console.error(`[streamer] Voice channel ${VOICE_CHANNEL_ID} not found.`);
            process.exit(1);
        }

        console.log(`[streamer] Joining voice channel ${channel.name} (${channel.id})...`);
        await streamer.joinVoice(channel.guild.id, channel.id);
        console.log("[streamer] Waiting for voice connection to stabilize...");
        await new Promise((resolve) => setTimeout(resolve, 3000));
        console.log("[streamer] Voice connection ready.");

        console.log("[streamer] Starting continuous H264 video + Opus audio stream...");
        while (true) {
            let ffmpegProc = null;
            try {
                const streamPipe = new PassThrough();
                
                ffmpegProc = spawn("ffmpeg", [
                    "-re",
                    "-i", mediaToStream,
                    "-map", "0:v:0",
                    "-map", "0:a:0",
                    "-c:v", "libx264",
                    "-preset", "ultrafast",
                    "-tune", "zerolatency",
                    "-vf", "scale=640:360:force_original_aspect_ratio=decrease,pad=640:360:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
                    "-r", "30",
                    "-g", "30",
                    "-bf", "0",
                    "-c:a", "libopus",
                    "-ar", "48000",
                    "-ac", "2",
                    "-b:a", "128k",
                    "-f", "nut",
                    "pipe:1"
                ]);

                ffmpegProc.stdout.pipe(streamPipe);

                ffmpegProc.stderr.on("data", (data) => {
                    const msg = data.toString();
                    if (msg.includes("Error") || msg.includes("error") || msg.includes("Fatal")) {
                        console.log("[ffmpeg-stderr]", msg.trim());
                    }
                });

                // Pre-buffer 1500ms of encoded frames so node-av demuxer never starves
                await new Promise((resolve) => setTimeout(resolve, 1500));

                console.log("[streamer] Playing stream...");
                await playStream(streamPipe, streamer);
                console.log("[streamer] Stream completed. Looping...");
                await new Promise((resolve) => setTimeout(resolve, 1000));
            } catch (err) {
                console.error("[streamer] Stream playback error:", err?.message || err);
                if (ffmpegProc) {
                    try { ffmpegProc.kill("SIGKILL"); } catch {}
                }
                await new Promise((resolve) => setTimeout(resolve, 3000));
            }
        }
    } catch (err) {
        console.error("[streamer] Fatal voice channel error:", err);
        process.exit(1);
    }
});

client.login(TOKEN);
