import os
import re
import tempfile
import streamlit as st
from moviepy import (
    AudioFileClip,
    CompositeVideoClip,
    ImageClip,
    TextClip,
    VideoFileClip,
    concatenate_videoclips,
)

st.set_page_config(page_title="Mobile Video Studio", page_icon="🎬", layout="centered")

st.title("🎬 Mobile Video Assembler")
st.write("Generate synchronized videos directly from your phone.")

# 1. Script Input
st.subheader("1. Script with Timestamps")
sample_script = (
    "0:00 - 0:05 | Welcome back to the channel\n"
    "0:05 - 0:10 | Today we explore ancient trade empires\n"
    "0:10 - 0:15 | Wealth flowed across thousands of miles"
)
script_text = st.text_area("Format: mm:ss - mm:ss | Subtitle", sample_script, height=130)

# 2. Audio Upload
st.subheader("2. Voiceover Audio")
audio_file = st.file_uploader("Upload Audio (.mp3, .wav, .m4a)", type=["mp3", "wav", "m4a"])

# 3. Media Upload
st.subheader("3. Images / Clips")
media_files = st.file_uploader(
    "Upload Media (Must match timestamp line count in exact order)",
    type=["png", "jpg", "jpeg", "webp", "mp4", "mov"],
    accept_multiple_files=True,
)

# 4. Settings
st.subheader("4. Formatting")
col1, col2 = st.columns(2)
with col1:
    ratio_choice = st.selectbox("Aspect Ratio", ["16:9 Landscape (YouTube)", "9:16 Portrait (Shorts)"])
with col2:
    style_choice = st.selectbox("Caption Style", ["Bold Yellow (Stroke)", "Classic White (Box Banner)", "Minimal White"])

def parse_timestamps(raw_text):
    pattern = r"(\d+):(\d+)\s*-\s*(\d+):(\d+)\s*[:\|]\s*(.+)"
    parsed = []
    for line in raw_text.strip().split("\n"):
        match = re.match(pattern, line.strip())
        if match:
            m1, s1, m2, s2, text = match.groups()
            start = int(m1) * 60 + int(s1)
            end = int(m2) * 60 + int(s2)
            duration = end - start
            if duration > 0:
                parsed.append({"start": start, "end": end, "duration": duration, "text": text.strip()})
    return parsed

# 5. Render
if st.button("⚡ Generate Video", type="primary", use_container_width=True):
    segments = parse_timestamps(script_text)

    if not segments:
        st.error("Please add valid timestamp lines (e.g. 0:00 - 0:05 | Subtitle).")
    elif not audio_file:
        st.error("Please upload your audio file.")
    elif len(segments) != len(media_files):
        st.error(f"Mismatch: Script has {len(segments)} lines, but you uploaded {len(media_files)} files.")
    else:
        with st.spinner("Rendering your video in the cloud..."):
            with tempfile.TemporaryDirectory() as tmpdir:
                audio_path = os.path.join(tmpdir, "voice.mp3")
                with open(audio_path, "wb") as f:
                    f.write(audio_file.read())

                saved_media = []
                for idx, mf in enumerate(media_files):
                    ext = os.path.splitext(mf.name)[1]
                    m_path = os.path.join(tmpdir, f"media_{idx}{ext}")
                    with open(m_path, "wb") as f:
                        f.write(mf.read())
                    saved_media.append(m_path)

                if "Shorts" in ratio_choice:
                    width, height = 1080, 1920
                    font_size = 52
                else:
                    width, height = 1920, 1080
                    font_size = 44

                text_w = int(width * 0.85)
                clips = []

                for seg, m_path in zip(segments, saved_media):
                    dur = seg["duration"]
                    ext = os.path.splitext(m_path)[1].lower()

                    if ext in [".png", ".jpg", ".jpeg", ".webp"]:
                        clip = ImageClip(m_path).with_duration(dur).resized(height=height)
                    else:
                        clip = VideoFileClip(m_path).subclipped(0, dur).resized(height=height)

                    clip = clip.with_position("center")

                    if "Yellow" in style_choice:
                        txt = TextClip(
                            text=seg["text"],
                            font_size=font_size,
                            font="Helvetica-Bold",
                            color="yellow",
                            stroke_color="black",
                            stroke_width=3,
                            method="caption",
                            size=(text_w, None),
                        )
                    elif "Box Banner" in style_choice:
                        txt = TextClip(
                            text=seg["text"],
                            font_size=font_size,
                            font="Helvetica-Bold",
                            color="white",
                            bg_color="black",
                            method="caption",
                            size=(text_w, None),
                        )
                    else:
                        txt = TextClip(
                            text=seg["text"],
                            font_size=font_size,
                            font="Helvetica-Bold",
                            color="white",
                            stroke_color="#222222",
                            stroke_width=1.5,
                            method="caption",
                            size=(text_w, None),
                        )

                    txt = txt.with_duration(dur).with_position(("center", int(height * 0.80)))
                    scene = CompositeVideoClip([clip, txt], size=(width, height)).with_duration(dur)
                    clips.append(scene)

                final_sequence = concatenate_videoclips(clips, method="compose")
                voice = AudioFileClip(audio_path)
                if voice.duration > final_sequence.duration:
                    voice = voice.subclipped(0, final_sequence.duration)
                final_sequence = final_sequence.with_audio(voice)

                output_path = os.path.join(tmpdir, "final_video.mp4")
                final_sequence.write_videofile(
                    output_path,
                    fps=24,
                    codec="libx264",
                    audio_codec="aac",
                    preset="veryfast",
                )

                st.success("Video ready!")
                with open(output_path, "rb") as out_f:
                    video_bytes = out_f.read()

                st.video(video_bytes)
                st.download_button(
                    label="💾 Download Video to Phone",
                    data=video_bytes,
                    file_name="finished_video.mp4",
                    mime="video/mp4",
                    use_container_width=True,
                )
                
