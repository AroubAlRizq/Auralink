# app/models/video_audio_summarizer.py
import os, io, sys, math, json, shutil, argparse, subprocess
from pathlib import Path
from typing import List, Dict
from PIL import Image
import google.generativeai as genai

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


def check_ffmpeg():
    for exe in ("ffmpeg", "ffprobe"):
        try:
            subprocess.run([exe, "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        except Exception:
            raise RuntimeError(f"'{exe}' not found. Please install ffmpeg via brew/apt/winget.")


def ffprobe_duration(video_path: str) -> float:
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", video_path
    ]
    out = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode().strip()
    return float(out)


def run_ffmpeg(cmd: List[str]) -> None:
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg error:\n{proc.stderr}")


def extract_frames(video_path: str, frames_dir: Path, fps: int) -> List[Path]:
    frames_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-y", "-i", video_path, "-vf", f"fps={fps}", "-q:v", "2",
        str(frames_dir / "frame_%09d.jpg")
    ]
    run_ffmpeg(cmd)
    files = sorted(frames_dir.glob("frame_*.jpg"))
    print(f"[DEBUG] Extracted {len(files)} frames.")
    return files


def extract_audio_full(video_path: str, audio_path: Path) -> None:
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-y", "-i", video_path, "-vn", "-ac", "1", "-ar", "16000", str(audio_path)
    ]
    run_ffmpeg(cmd)
    print(f"[DEBUG] Extracted audio to {audio_path}")


def split_audio_windows(base_audio: Path, window_s: int, duration: float) -> List[Dict]:
    num_windows = math.ceil(duration / window_s)
    out = []
    for w in range(num_windows):
        start = w * window_s
        end = min(start + window_s, duration)
        outp = base_audio.parent / f"win_{w:03d}.wav"
        cmd = [
            "ffmpeg", "-hide_banner", "-loglevel", "error",
            "-y", "-ss", str(start), "-t", str(end - start),
            "-i", str(base_audio), str(outp)
        ]
        run_ffmpeg(cmd)
        out.append({"w": w, "start": start, "end": end, "path": str(outp)})
    print(f"[DEBUG] Split audio into {len(out)} windows.")
    return out


def summarize_video(
    video_path: str,
    workdir: str = "./vproc",
    fps: int = 2,
    window_s: int = 30,
    max_imgs_per_chunk: int = 60,
    model_name: str = None,
    audio_only: bool = False
) -> Dict:
    check_ffmpeg()
    os.makedirs(workdir, exist_ok=True)

    duration = ffprobe_duration(video_path)
    print(f"[DEBUG] Video duration: {duration:.1f}s")

    frames = []
    if not audio_only:
        frames = extract_frames(video_path, Path(workdir) / "frames", fps)
    base_audio = Path(workdir) / "audio" / "full.wav"
    extract_audio_full(video_path, base_audio)
    audio_slices = split_audio_windows(base_audio, window_s, duration)

    api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Missing GOOGLE_API_KEY in environment.")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name or os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))

    windows = []
    for w in audio_slices:
        prompt = f"Describe what happens between {w['start']}s and {w['end']}s in this meeting."
        parts = [{"text": prompt}, {"mime_type": "audio/wav", "data": Path(w['path']).read_bytes()}]

        try:
            resp = model.generate_content(parts)
            text = getattr(resp, "text", str(resp))
        except Exception as e:
            text = f"[Gemini error on window {w['w']}] {e}"

        windows.append({"window": w["w"], "start": w["start"], "end": w["end"], "text": text})

    narration_path = Path(workdir) / "video_audio_narration.txt"
    summary_path = Path(workdir) / "video_audio_summary.txt"

    narration = "\n\n".join([f"Window {w['w']+1}: {w['text']}" for w in windows])
    narration_path.write_text(narration, encoding="utf-8")

    try:
        final_prompt = f"Summarize this meeting based on the narration:\n{narration}"
        summary = model.generate_content(final_prompt).text
    except Exception as e:
        summary = f"[Gemini summary error] {e}"
    summary_path.write_text(summary, encoding="utf-8")

    return {
        "narration_file": str(narration_path),
        "summary_file": str(summary_path),
        "windows": windows,
        "summary_text": summary,
    }