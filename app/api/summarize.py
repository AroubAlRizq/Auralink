

import os
import io
import sys
import math
import json
import glob
import shutil
import argparse
import subprocess
from pathlib import Path
from typing import List, Dict, Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from PIL import Image


import google.generativeai as genai


# --------------------------- Utilities ---------------------------

def check_ffmpeg() -> None:
    """Ensure ffmpeg and ffprobe are installed."""
    for exe in ("ffmpeg", "ffprobe"):
        try:
            subprocess.run([exe, "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        except Exception as e:
            raise RuntimeError(
                f"Required tool '{exe}' not found. Install ffmpeg and ensure it's on PATH.\n"
                f"Windows (PowerShell): winget install Gyan.FFmpeg (or choco install ffmpeg)\n"
                f"macOS (Homebrew): brew install ffmpeg\n"
                f"Linux (Debian/Ubuntu): sudo apt-get install ffmpeg\n"
            ) from e


def ffprobe_duration(video_path: str) -> float:
    """Return video duration in seconds using ffprobe."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_path
    ]
    out = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode().strip()
    return float(out)


def run_ffmpeg(cmd: List[str]) -> None:
    """Run an ffmpeg command with error surfacing."""
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg error:\n{proc.stderr}")


def extract_frames(video_path: str, frames_dir: Path, fps: int) -> List[Path]:
    """
    Extract frames at given FPS into frames_dir as JPG.
    Filenames: frame_000000001.jpg, ...
    """
    frames_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-y", "-i", video_path,
        "-vf", f"fps={fps}",
        "-q:v", "2",
        str(frames_dir / "frame_%09d.jpg")
    ]
    run_ffmpeg(cmd)
    files = sorted(frames_dir.glob("frame_*.jpg"))
    return files


def extract_audio_full(video_path: str, audio_path: Path) -> None:
    """Extract mono 16k WAV from video."""
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-y", "-i", video_path,
        "-vn", "-ac", "1", "-ar", "16000", str(audio_path)
    ]
    run_ffmpeg(cmd)


def split_audio_windows(base_audio: Path, window_s: int, duration: float) -> List[Dict]:
    """Cut audio into window slices and return descriptors."""
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
    return out


def load_image_bytes(p: Path) -> bytes:
    im = Image.open(p).convert("RGB")
    # Optional downscale to control cost/latency:
    # im.thumbnail((1280, 1280))
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def load_audio_bytes(p: Path) -> bytes:
    return Path(p).read_bytes()


def even_sample(paths: List[Path], cap: int) -> List[Path]:
    """Evenly sample a list down to 'cap' elements (inclusive)."""
    if len(paths) <= cap:
        return paths
    # float stepping to evenly pick indices
    step = (len(paths) - 1) / (cap - 1)
    idxs = [round(i * step) for i in range(cap)]
    # Deduplicate in rare rounding collisions
    seen = set()
    result = []
    for i in idxs:
        if i not in seen:
            result.append(paths[i])
            seen.add(i)
    return result


def make_prompt_for_window(w_idx: int, t0: float, t1: float, fps: int) -> str:
    return f"""
You will receive a sequence of video frames (sampled at {fps} FPS) **and** the matching audio clip.

WINDOW: #{w_idx} from ~{t0:.1f}s to ~{t1:.1f}s

TASKS:
1) ### Narration
   Describe what happens visually AND what is said/heard in the audio.
   Be specific and chronological. Mention actions, objects, on-screen text, and any scene changes.
   If audio is unclear, note [inaudible] rather than guessing.

2) ### Key Moments
   Bullet points of notable events in this window.

3) ### Timestamps
   Use approximate seconds (e.g., 2–3s, 12s, etc.) relative to this window.
""".strip()


def per_window_frames(frames: List[Path], start: float, end: float, fps: int, cap: int) -> List[Path]:
    """Select frames whose timestamps fall in [start, end); timestamp = index/fps."""
    # We rely on the deterministic extraction rate:
    # frame index i corresponds to time i/fps
    start_i = math.ceil(start * fps)
    end_i = math.floor(end * fps) - 1
    if end_i < start_i:
        end_i = start_i
    window_paths = [frames[i] for i in range(start_i, min(end_i + 1, len(frames)) if frames else 0)]
    return even_sample(window_paths, cap) if cap else window_paths


def summarize_video(
    video_path: str,
    workdir: str,
    fps: int,
    window_s: int,
    max_imgs_per_chunk: int,
    model_name: str
) -> None:

    check_ffmpeg()

    video_path = str(Path(video_path).resolve())
    workdir_p = Path(workdir).resolve()

    # Fresh workspace
    if workdir_p.exists():
        shutil.rmtree(workdir_p)
    (workdir_p / "frames").mkdir(parents=True, exist_ok=True)
    (workdir_p / "audio").mkdir(parents=True, exist_ok=True)

    print(f"Workspace: {workdir_p}")

    # Duration & windowing
    duration = ffprobe_duration(video_path)
    num_windows = math.ceil(duration / window_s)
    print(f"Video duration ≈ {duration:.2f}s → {num_windows} windows of {window_s}s")

    # Extract artifacts
    frames = extract_frames(video_path, workdir_p / "frames", fps)
    base_audio = workdir_p / "audio" / "full.wav"
    extract_audio_full(video_path, base_audio)
    audio_slices = split_audio_windows(base_audio, window_s, duration)

    # Configure Gemini
    api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY not set. Use environment variable or .env file.")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)

    # Process windows
    chunk_results = []
    for w in audio_slices:
        start, end = w["start"], w["end"]
        w_idx = w["w"] + 1
        frame_list = per_window_frames(frames, start, end, fps, max_imgs_per_chunk)

        if not frame_list and (end - start) < 1.0:
            continue  # skip empty trailing sliver

        parts = [{"text": make_prompt_for_window(w_idx, start, end, fps)}]
        # Add images (chronological)
        for fp in frame_list:
            parts.append({"mime_type": "image/jpeg", "data": load_image_bytes(fp)})
        # Add audio slice (WAV)
        parts.append({"mime_type": "audio/wav", "data": load_audio_bytes(Path(w["path"]))})

        # Call Gemini
        try:
            resp = model.generate_content(parts)
            text = getattr(resp, "text", str(resp))
        except Exception as e:
            text = f"[ERROR calling Gemini for window {w_idx}: {e}]"

        chunk_results.append({
            "window": w["w"],
            "start": start,
            "end": end,
            "frames": len(frame_list),
            "text": text
        })
        print(f"Processed window {w_idx}/{len(audio_slices)} with {len(frame_list)} frames.")

    # Write narration
    narration_path = workdir_p / "video_audio_narration.txt"
    full_narration = "\n\n".join(
        f"## Window {c['window']+1} ({c['start']:.1f}s–{c['end']:.1f}s)\n{c['text']}"
        for c in chunk_results
    )
    narration_path.write_text(full_narration, encoding="utf-8")

    # Global summary
    summary_prompt = f"""
You are given a multi-window narration of a video, where each window combined
images and audio for that time range.

Please produce:
1) **Executive Summary** (6–10 sentences, objective, no speculation).
2) **Chronological Key Events** (10–20 bullets, deduplicated).
3) **Quotes / Spoken Highlights**: short list of notable lines (if audio provided them).
4) **Action Items / TODOs** (if applicable).

NARRATION START
{full_narration}
NARRATION END
""".strip()

    try:
        final = genai.GenerativeModel(model_name).generate_content(summary_prompt).text
    except Exception as e:
        final = f"[ERROR calling Gemini for global summary: {e}]"

    summary_path = workdir_p / "video_audio_summary.txt"
    summary_path.write_text(final, encoding="utf-8")

    print("Saved:")
    print(f"- {narration_path}")
    print(f"- {summary_path}")


# --------------------------- CLI ---------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="VS Code-friendly video+audio summarizer with Gemini.")
    p.add_argument("--video", required=True, help="Path to input video file")
    p.add_argument("--workdir", default="./vproc", help="Working directory (will be recreated)")
    p.add_argument("--fps", type=int, default=2, help="Frames per second to sample (1–2 is typical)")
    p.add_argument("--window", type=int, default=30, help="Window length in seconds")
    p.add_argument("--max-images", type=int, default=60, help="Max images per window (safety cap)")
    p.add_argument("--model", default="gemini-2.5-flash", help="Gemini model name")
    return p.parse_args()


def main():
    args = parse_args()
    try:
        summarize_video(
            video_path=args.video,
            workdir=args.workdir,
            fps=args.fps,
            window_s=args.window,
            max_imgs_per_chunk=args.max_images,
            model_name=args.model
        )
    except Exception as e:
        print(f"[Fatal error] {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()