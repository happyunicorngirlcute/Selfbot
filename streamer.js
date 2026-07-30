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
    console.log(`[streamer] Media file: ${mediaToStream} (${fs.statSync(mediaToStream).size} bytes)`);

    // Verify the media file is valid
    try {
        const probe = execSync(`ffprobe -v error -show_format -show_streams -of json "${mediaToStream}"`, { encoding: "utf8" });
        const info = JSON.parse(probe);
        console.log("[streamer] Media info:", JSON.stringify({
            format: info.format.format_name,
            duration: info.format.duration,
            streams: info.streams.map(s => ({ codec_name: s.codec_name, codec_type: s.codec_type, width: s.width, height: s.height, sample_rate: s.sample_rate }))
        }));
    } catch (e) {
        console.error("[streamer] ffprobe failed:", e.message);
    }

    // Check if zmq is available in ffmpeg
    try {
        const zmqCheck = execSync("ffmpeg -protocols 2>&1 | grep zmq || echo 'ZMQ NOT FOUND'", { encoding: "utf8" });
        console.log("[streamer] ZMQ protocol support:", zmqCheck.trim());
    } catch (e) {
        console.log("[streamer] ZMQ check failed:", e.message);
    }

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

        console.log("[streamer] Starting continuous video + audio stream...");
        while (true) {
            try {
                console.log("[streamer] Calling prepareStream...");
                const { command, output, promise } = prepareStream(mediaToStream);
                
                // Log FFmpeg command line
                command.once("start", (cmdline) => {
                    console.log("[streamer] FFmpeg command:", cmdline);
                });
                command.on("error", (err) => {
                    console.error("[streamer] FFmpeg command error:", err.message);
                });
                
                // Monitor the output stream
                let bytesReceived = 0;
                output.on("data", (chunk) => {
                    bytesReceived += chunk.length;
                    if (bytesReceived <= 1024 || bytesReceived % (1024 * 100) < 1024) {
                        console.log(`[streamer] Output stream received ${bytesReceived} bytes total`);
                    }
                });
                output.on("error", (err) => {
                    console.error("[streamer] Output stream error:", err.message, err.stack);
                });
                output.on("end", () => {
                    console.log(`[streamer] Output stream ended. Total bytes: ${bytesReceived}`);
                });
                output.on("close", () => {
                    console.log(`[streamer] Output stream closed. Total bytes: ${bytesReceived}`);
                });

                // Monitor the promise from prepareStream
                promise.then(() => {
                    console.log("[streamer] prepareStream promise resolved");
                }).catch((err) => {
                    console.error("[streamer] prepareStream promise rejected:", err?.message || err);
                });

                console.log("[streamer] Calling playStream...");
                await playStream(output, streamer);
                console.log("[streamer] Stream loop completed. Restarting...");
                await new Promise((resolve) => setTimeout(resolve, 2000));
            } catch (err) {
                console.error("[streamer] Error in stream loop:", err?.message || err);
                if (err?.stack) console.error("[streamer] Stack:", err.stack);
                await new Promise((resolve) => setTimeout(resolve, 5000));
            }
        }
    } catch (err) {
        console.error("[streamer] Fatal voice channel error:", err);
        process.exit(1);
    }
});

client.login(TOKEN);
