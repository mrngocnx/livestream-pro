"""
Video Source Manager
Hỗ trợ: thư mục local, Google Drive, YouTube playlist/link
"""
import os, re, sys, logging, threading, subprocess, tempfile
from typing import List, Optional, Callable
from pathlib import Path

logger = logging.getLogger(__name__)
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv", ".webm", ".ts", ".m4v"}


# ── Tìm python executable hiện tại ──────────────────────
def _python_exe() -> str:
    return sys.executable or "python"


# ══════════════════════════════════════════════════════
# Local
# ══════════════════════════════════════════════════════
def get_local_videos(path: str) -> List[str]:
    p = Path(path)
    if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS:
        return [str(p)]
    if p.is_dir():
        files = []
        for ext in VIDEO_EXTENSIONS:
            files.extend(p.rglob(f"*{ext}"))
        return sorted(str(f) for f in files)
    return []


# ══════════════════════════════════════════════════════
# YouTube (yt-dlp)
# ══════════════════════════════════════════════════════

def _run_ytdlp(args: List[str], on_log=None) -> str:
    try:
        import yt_dlp
        opts = {'quiet': True, 'no_warnings': True}
        url = [a for a in args if a.startswith('http')]
        url = url[0] if url else (args[-1] if args else '')
        if '--get-url' in args: opts['geturl'] = True
        if '--yes-playlist' in args or 'yesplaylist' in args: opts['yesplaylist'] = True
        if '--no-playlist' in args: opts['noplaylist'] = True
        for i, a in enumerate(args):
            if a in ('-f','--format') and i+1<len(args): opts['format'] = args[i+1]
            if a == '--merge-output-format' and i+1<len(args): opts['merge_output_format'] = args[i+1]
            if a in ('-o','--output') and i+1<len(args): opts['outtmpl'] = args[i+1]
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=not opts.get('geturl'))
            if opts.get('geturl'):
                if info.get('_type') == 'playlist':
                    return '\\n'.join(e.get('url','') for e in (info.get('entries') or []) if e)
                return info.get('url','')
            else:
                if info.get('_type') == 'playlist':
                    return '\\n'.join(e.get('requested_downloads',[{}])[0].get('filepath','') for e in (info.get('entries') or []) if e)
                return info.get('requested_downloads',[{}])[0].get('filepath','')
    except ImportError:
        msg = "❌ yt-dlp chưa được cài!"
        if on_log: on_log(msg)
        raise RuntimeError(msg)
    except Exception as e:
        if on_log: on_log(f"[yt-dlp] {str(e)[:200]}")
        raise

def _cookies_args(cookies: Optional[str]) -> List[str]:
    if not cookies:
        return []
    if cookies.strip().lower() in ("chrome", "firefox", "edge", "opera", "brave", "chromium"):
        return ["--cookies-from-browser", cookies.strip().lower()]
    return ["--cookies", cookies.strip()]


def get_youtube_direct_urls(youtube_url: str, on_log=None, cookies=None) -> List[str]:
    if on_log: on_log(f"🔍 Đang lấy URL từ YouTube: {youtube_url}")
    args = (["--get-url", "-f", "best[ext=mp4]/best",
             "--no-playlist" if "list=" not in youtube_url else "--yes-playlist"]
            + _cookies_args(cookies) + [youtube_url])
    output = _run_ytdlp(args, on_log)
    urls = [u for u in output.splitlines() if u.startswith("http")]
    if on_log: on_log(f"✅ Tìm thấy {len(urls)} video từ YouTube")
    return urls


def download_youtube_videos(youtube_url: str, download_dir: str,
                             on_log=None, on_progress=None, cookies=None) -> List[str]:
    os.makedirs(download_dir, exist_ok=True)
    if on_log: on_log(f"⬇️  Đang tải video từ: {youtube_url}")
    cmd = ([_python_exe(), "-m", "yt_dlp",
            "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "--merge-output-format", "mp4",
            "-o", os.path.join(download_dir, "%(title)s.%(ext)s"),
            "--no-playlist" if "list=" not in youtube_url else "--yes-playlist",
            "--newline"] + _cookies_args(cookies) + [youtube_url])
    try:
        import yt_dlp
        def _hook(d):
            if on_progress and d.get('status') == 'downloading':
                t = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                if t > 0: on_progress(d.get('downloaded_bytes',0)/t*100)
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'merge_output_format': 'mp4',
            'outtmpl': os.path.join(download_dir, '%(title)s.%(ext)s'),
            'quiet': True, 'no_warnings': True,
            'progress_hooks': [_hook] if on_progress else [],
        }
        if on_log: on_log(f"⬇️  {youtube_url[:50]}...")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([youtube_url])
        if on_log: on_log(f"✅ Tải xong")
    except ImportError:
        if on_log: on_log("❌ yt-dlp chưa cài!")
        return []
    except Exception as e:
        if on_log: on_log(f"❌ {str(e)[:200]}")
        return []
    return get_local_videos(download_dir)


# ══════════════════════════════════════════════════════
# Google Drive (gdown qua python -m)
# ══════════════════════════════════════════════════════
def _extract_drive_folder_id(url: str) -> Optional[str]:
    for p in [r"/folders/([a-zA-Z0-9_-]+)", r"id=([a-zA-Z0-9_-]+)"]:
        m = re.search(p, url)
        if m: return m.group(1)
    return None

def _extract_drive_file_id(url: str) -> Optional[str]:
    for p in [r"/file/d/([a-zA-Z0-9_-]+)", r"id=([a-zA-Z0-9_-]+)"]:
        m = re.search(p, url)
        if m: return m.group(1)
    return None

def _check_gdown(on_log=None) -> bool:
    """Kiểm tra gdown có cài không, dùng python -m gdown"""
    result = subprocess.run(
        [_python_exe(), "-m", "gdown", "--version"],
        capture_output=True, text=True,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    if result.returncode != 0:
        if on_log:
            on_log(f"❌ gdown chưa cài hoặc không tìm thấy.")
            on_log(f"💡 Chạy lệnh sau để cài:")
            on_log(f"   {_python_exe()} -m pip install gdown")
        return False
    return True

def get_google_drive_videos(drive_url_or_id: str, download_dir: str,
                             credentials_path=None, on_log=None) -> List[str]:
    os.makedirs(download_dir, exist_ok=True)

    if not _check_gdown(on_log):
        return []

    is_folder = "folders" in drive_url_or_id
    try:
        if is_folder:
            folder_id = _extract_drive_folder_id(drive_url_or_id) or drive_url_or_id
            if on_log: on_log(f"📂 Đang tải folder Google Drive: {folder_id}")
            folder_url = f"https://drive.google.com/drive/folders/{folder_id}"
            cmd = [_python_exe(), "-m", "gdown", "--folder", folder_url,
                   "-O", download_dir, "--remaining-ok"]
        else:
            file_id = _extract_drive_file_id(drive_url_or_id) or drive_url_or_id
            if on_log: on_log(f"📄 Đang tải file Google Drive: {file_id}")
            file_url = f"https://drive.google.com/uc?id={file_id}"
            out_path = os.path.join(download_dir, "drive_video.mp4")
            cmd = [_python_exe(), "-m", "gdown", "--fuzzy", file_url, "-O", out_path]

        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        for line in proc.stdout:
            line = line.strip()
            if on_log and line: on_log(f"[gdown] {line[:120]}")
        proc.wait()

        videos = get_local_videos(download_dir)
        if on_log: on_log(f"✅ Tải xong {len(videos)} video từ Drive")
        return videos

    except Exception as e:
        err = str(e)
        if on_log:
            on_log(f"❌ Lỗi Google Drive: {err[:200]}")
            if "quota" in err.lower() or "Too many" in err:
                on_log("⚠️ Drive đạt giới hạn. Thử lại sau hoặc dùng rclone mount.")
            elif "403" in err or "Permission" in err:
                on_log("⚠️ File chưa public: Drive → Share → 'Anyone with the link'")
        return []


# ══════════════════════════════════════════════════════
# Pre-encode (encode trước khi live để đảm bảo độ mượt)
# ══════════════════════════════════════════════════════
def pre_encode_video(input_path: str, output_dir: str, vf_filter: str,
                     resolution: str, vbitrate: str, abitrate: str, fps: int,
                     on_log=None, on_progress=None) -> Optional[str]:
    """
    Encode lại video với filter + settings đã chọn.
    Trả về đường dẫn file đã encode.
    """
    os.makedirs(output_dir, exist_ok=True)
    base = Path(input_path).stem
    out_path = os.path.join(output_dir, f"{base}_encoded.mp4")

    if on_log: on_log(f"🔄 Đang encode: {Path(input_path).name}")

    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-vf", vf_filter,
        "-af", "aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo",
        "-vcodec", "libx264",
        "-preset", "fast",
        "-b:v", vbitrate,
        "-maxrate", vbitrate,
        "-bufsize", str(int(vbitrate[:-1]) * 2) + "k",
        "-pix_fmt", "yuv420p",
        "-r", str(fps),
        "-acodec", "aac",
        "-b:a", abitrate,
        "-movflags", "+faststart",
        out_path,
    ]
    try:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        duration_total = None
        for line in proc.stdout:
            line = line.strip()
            # Parse duration
            if "Duration:" in line and duration_total is None:
                m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", line)
                if m:
                    h, mn, s = float(m.group(1)), float(m.group(2)), float(m.group(3))
                    duration_total = h*3600 + mn*60 + s
            # Parse progress
            if on_progress and "time=" in line and duration_total:
                m = re.search(r"time=(\d+):(\d+):(\d+\.\d+)", line)
                if m:
                    h, mn, s = float(m.group(1)), float(m.group(2)), float(m.group(3))
                    elapsed = h*3600 + mn*60 + s
                    pct = min(100.0, elapsed / duration_total * 100)
                    on_progress(pct)
            if on_log and ("error" in line.lower() or "warning" in line.lower()):
                on_log(f"[ffmpeg] {line}")
        proc.wait()
        if proc.returncode == 0:
            if on_log: on_log(f"✅ Encode xong: {Path(out_path).name}")
            return out_path
        else:
            if on_log: on_log(f"❌ Encode thất bại: {Path(input_path).name}")
            return None
    except FileNotFoundError:
        if on_log: on_log("❌ Không tìm thấy FFmpeg!")
        return None
    except Exception as e:
        if on_log: on_log(f"❌ Lỗi encode: {e}")
        return None


def pre_encode_playlist(playlist: List[str], output_dir: str, vf_filter: str,
                         resolution: str, vbitrate: str, abitrate: str, fps: int,
                         on_log=None, on_progress=None,
                         on_done: Optional[Callable] = None):
    """Encode toàn bộ playlist trong background thread"""
    def _run():
        encoded = []
        total = len(playlist)
        for i, path in enumerate(playlist):
            if path.startswith("http"):
                encoded.append(path)
                continue
            if on_log: on_log(f"📦 Encode {i+1}/{total}: {Path(path).name}")
            def prog(pct, idx=i):
                if on_progress:
                    overall = (idx + pct/100) / total * 100
                    on_progress(overall)
            out = pre_encode_video(path, output_dir, vf_filter, resolution,
                                    vbitrate, abitrate, fps, on_log, prog)
            encoded.append(out if out else path)
        if on_log: on_log(f"🎉 Encode xong {len(encoded)} video!")
        if on_done: on_done(encoded)
    threading.Thread(target=_run, daemon=True).start()


# ══════════════════════════════════════════════════════
# Async loader
# ══════════════════════════════════════════════════════
class VideoSourceLoader:
    def __init__(self, on_done: Callable, on_log=None):
        self._on_done = on_done
        self._on_log  = on_log

    def load_local(self, path: str):
        def _run():
            videos = get_local_videos(path)
            if self._on_log: self._on_log(f"📁 Tìm thấy {len(videos)} video trong '{path}'")
            self._on_done(videos)
        threading.Thread(target=_run, daemon=True).start()

    def load_youtube(self, url: str, mode="download", download_dir="", cookies=None):
        def _run():
            if mode == "download":
                dl = download_dir or os.path.join(os.path.expanduser("~"), "Videos", "LiveStream_Cache")
                videos = download_youtube_videos(url, dl, on_log=self._on_log, cookies=cookies)
            else:
                videos = get_youtube_direct_urls(url, on_log=self._on_log, cookies=cookies)
            self._on_done(videos)
        threading.Thread(target=_run, daemon=True).start()

    def load_google_drive(self, url: str):
        def _run():
            dl = os.path.join(tempfile.gettempdir(), "livestream_drive")
            videos = get_google_drive_videos(url, dl, on_log=self._on_log)
            self._on_done(videos)
        threading.Thread(target=_run, daemon=True).start()
