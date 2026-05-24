"""
Stream Engine - Xử lý FFmpeg để stream video 24/7
"""
import subprocess
import threading
import os
import time
import random
import logging
from typing import List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class StreamStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    STOPPED = "stopped"


@dataclass
class StreamTarget:
    platform: str  # youtube, facebook, tiktok, custom
    rtmp_url: str
    stream_key: str

    @property
    def full_url(self) -> str:
        url = self.rtmp_url.rstrip("/")
        key = self.stream_key.strip()
        if key:
            return f"{url}/{key}"
        return url

    PLATFORM_URLS = {
        "youtube":  "rtmp://a.rtmp.youtube.com/live2",
        "facebook": "rtmps://live-api-s.facebook.com:443/rtmp",
        "tiktok":   "rtmp://push.tiktok.com/live",
        "custom":   "",
    }

    @classmethod
    def from_platform(cls, platform: str, stream_key: str) -> "StreamTarget":
        url = cls.PLATFORM_URLS.get(platform.lower(), "")
        return cls(platform=platform, rtmp_url=url, stream_key=stream_key)


@dataclass
class StreamConfig:
    targets: List[StreamTarget] = field(default_factory=list)
    video_bitrate: str = "3000k"
    audio_bitrate: str = "128k"
    resolution: str = "1280x720"
    fps: int = 30
    loop_mode: str = "shuffle"      # shuffle | sequential | single
    overlay_text: str = ""
    show_clock: bool = False
    volume: float = 1.0


class StreamEngine:
    """Quản lý tiến trình FFmpeg để stream 24/7"""

    def __init__(self, config: StreamConfig):
        self.config = config
        self.status = StreamStatus.IDLE
        self._process: Optional[subprocess.Popen] = None
        self._thread: Optional[threading.Thread] = None
        self._playlist: List[str] = []
        self._current_index = 0
        self._stop_event = threading.Event()
        self._on_status_change: Optional[Callable] = None
        self._on_video_change: Optional[Callable] = None
        self._on_log: Optional[Callable] = None

    # ──────────────────────────────────────────────
    # Callbacks
    # ──────────────────────────────────────────────
    def on_status_change(self, cb: Callable): self._on_status_change = cb
    def on_video_change(self,  cb: Callable): self._on_video_change  = cb
    def on_log(self,           cb: Callable): self._on_log           = cb

    def _emit_status(self, s: StreamStatus):
        self.status = s
        if self._on_status_change:
            self._on_status_change(s)

    def _emit_video(self, path: str):
        if self._on_video_change:
            self._on_video_change(path)

    def _emit_log(self, msg: str):
        logger.info(msg)
        if self._on_log:
            self._on_log(msg)

    # ──────────────────────────────────────────────
    # Playlist
    # ──────────────────────────────────────────────
    def set_playlist(self, files: List[str]):
        # Chấp nhận cả file local lẫn URL (http/https/rtmp)
        self._playlist = [
            f for f in files
            if f.startswith("http://") or f.startswith("https://") or f.startswith("rtmp") or os.path.isfile(f)
        ]
        if self.config.loop_mode == "shuffle":
            random.shuffle(self._playlist)
        self._current_index = 0
        self._emit_log(f"✅ Đã tải {len(self._playlist)} video vào danh sách phát")

    def _next_video(self) -> Optional[str]:
        if not self._playlist:
            return None
        if self.config.loop_mode == "single":
            return self._playlist[0]
        video = self._playlist[self._current_index % len(self._playlist)]
        self._current_index += 1
        if self.config.loop_mode == "shuffle" and self._current_index >= len(self._playlist):
            random.shuffle(self._playlist)
            self._current_index = 0
        return video

    # ──────────────────────────────────────────────
    # FFmpeg command builder
    # ──────────────────────────────────────────────
    def _build_ffmpeg_cmd(self, video_path: str) -> List[str]:
        w, h = self.config.resolution.split("x")
        vf_filters = [f"scale={w}:{h}:force_original_aspect_ratio=decrease",
                      f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2"]

        if self.config.show_clock:
            vf_filters.append(
                "drawtext=fontfile=/Windows/Fonts/arial.ttf:"
                "text='%{localtime\\:%H\\:%M\\:%S}':"
                "x=10:y=10:fontsize=24:fontcolor=white:"
                "box=1:boxcolor=black@0.5:boxborderw=5"
            )

        if self.config.overlay_text:
            safe_text = self.config.overlay_text.replace("'", "\\'").replace(":", "\\:")
            vf_filters.append(
                f"drawtext=fontfile=/Windows/Fonts/arial.ttf:"
                f"text='{safe_text}':"
                f"x=(w-text_w)/2:y=h-th-20:fontsize=28:fontcolor=white:"
                f"box=1:boxcolor=black@0.6:boxborderw=8"
            )

        vf = ",".join(vf_filters)

        # Xây outputs cho từng target
        output_args = []
        for t in self.config.targets:
            output_args += [
                "-f", "flv",
                "-vcodec", "libx264",
                "-preset", "veryfast",
                "-b:v", self.config.video_bitrate,
                "-maxrate", self.config.video_bitrate,
                "-bufsize", str(int(self.config.video_bitrate[:-1]) * 2) + "k",
                "-pix_fmt", "yuv420p",
                "-g", str(self.config.fps * 2),
                "-acodec", "aac",
                "-b:a", self.config.audio_bitrate,
                "-ar", "44100",
                "-r", str(self.config.fps),
                t.full_url,
            ]

        cmd = [
            "ffmpeg", "-re",
            "-i", video_path,
            "-vf", vf,
            "-af", f"volume={self.config.volume}",
        ] + output_args

        return cmd

    # ──────────────────────────────────────────────
    # Stream control
    # ──────────────────────────────────────────────
    def start(self):
        if self.status == StreamStatus.RUNNING:
            return
        if not self._playlist:
            self._emit_log("⚠️ Chưa có video nào trong danh sách!")
            return
        if not self.config.targets:
            self._emit_log("⚠️ Chưa cấu hình kênh stream!")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        self._emit_status(StreamStatus.RUNNING)

    def stop(self):
        self._stop_event.set()
        if self._process:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
        self._emit_status(StreamStatus.STOPPED)
        self._emit_log("🛑 Đã dừng stream")

    def _loop(self):
        """Vòng lặp stream liên tục"""
        while not self._stop_event.is_set():
            video = self._next_video()
            if not video:
                self._emit_log("❌ Không có video để phát")
                self._emit_status(StreamStatus.ERROR)
                break

            self._emit_video(video)
            self._emit_log(f"▶️  Đang phát: {os.path.basename(video)}")

            cmd = self._build_ffmpeg_cmd(video)
            try:
                self._process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                    bufsize=1,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0, startupinfo=_hide_window(),
                )
                for line in self._process.stdout:
                    if self._stop_event.is_set():
                        break
                    line = line.strip()
                    if line and ("error" in line.lower() or "warning" in line.lower()):
                        self._emit_log(f"[ffmpeg] {line}")

                self._process.wait()
                if self._process.returncode not in (0, -15, 1):
                    self._emit_log(f"⚠️ FFmpeg thoát với mã: {self._process.returncode}")
                    time.sleep(3)  # chờ trước khi thử lại

            except FileNotFoundError:
                self._emit_log("❌ Không tìm thấy FFmpeg! Hãy cài đặt FFmpeg và thêm vào PATH.")
                self._emit_status(StreamStatus.ERROR)
                break
            except Exception as e:
                self._emit_log(f"❌ Lỗi: {e}")
                time.sleep(3)

        if not self._stop_event.is_set():
            self._emit_status(StreamStatus.IDLE)
