"""
Stream Manager — Quản lý đa luồng stream độc lập
Mỗi luồng = 1 instance StreamEngine riêng
"""
import threading, time, os, json
from typing import List, Optional, Callable
from core.stream_engine import StreamEngine, StreamConfig, StreamTarget, StreamStatus
from core.video_source import get_local_videos, VideoSourceLoader

class StreamInstance:
    """Một luồng stream độc lập"""
    def __init__(self, instance_id: int, name: str, on_log=None, on_status=None, on_video=None):
        self.id = instance_id
        self.name = name
        self.engine: Optional[StreamEngine] = None
        self.playlist: List[str] = []
        self.config_panel = None  # reference to UI panel
        
        # Callbacks
        self._on_log = on_log
        self._on_status = on_status
        self._on_video = on_video
        
        # Config (defaults)
        self.video_source = "local"
        self.source_path = ""
        self.stream_key = ""
        self.platform = "youtube"
        self.resolution = "1280x720"
        self.fps = 30
        self.video_bitrate = "3000"
        self.audio_bitrate = "128"
        self.loop_mode = "shuffle"
        self.volume = 1.0
        self.overlay_text = ""
        self.show_clock = False
        
    @property
    def is_running(self) -> bool:
        return self.engine is not None and self.engine.status == StreamStatus.RUNNING
    
    def start(self):
        if self.is_running:
            return
        if not self.playlist:
            if self._on_log: self._on_log(self.id, f"❌ [Luồng {self.id}] Chưa có video!")
            return
        if not self.stream_key:
            if self._on_log: self._on_log(self.id, f"❌ [Luồng {self.id}] Chưa nhập Stream Key!")
            return
            
        target = StreamTarget.from_platform(self.platform, self.stream_key)
        config = StreamConfig(
            targets=[target],
            video_bitrate=self.video_bitrate + "k",
            audio_bitrate=self.audio_bitrate + "k",
            resolution=self.resolution,
            fps=self.fps,
            loop_mode=self.loop_mode,
            overlay_text=self.overlay_text,
            show_clock=self.show_clock,
            volume=self.volume,
        )
        
        self.engine = StreamEngine(config)
        self.engine.set_playlist(self.playlist)
        self.engine.on_log(lambda m: self._on_log(self.id, m) if self._on_log else None)
        self.engine.on_status_change(lambda s: self._on_status(self.id, s) if self._on_status else None)
        self.engine.on_video_change(lambda v: self._on_video(self.id, v) if self._on_video else None)
        self.engine.start()
        
    def stop(self):
        if self.engine:
            self.engine.stop()
            self.engine = None
    
    def load_source(self, path: str):
        """Tải nguồn video từ path local / URL"""
        self.source_path = path
        if os.path.isfile(path):
            self.playlist = [path]
        elif os.path.isdir(path):
            self.playlist = get_local_videos(path)
        else:
            # Có thể là URL — cần xử lý async qua loader
            self.playlist = []
            

class StreamManager:
    """Quản lý tất cả các luồng"""
    def __init__(self, on_log=None, on_status=None, on_video=None):
        self.instances: List[StreamInstance] = []
        self._next_id = 1
        self._lock = threading.Lock()
        self._on_log = on_log
        self._on_status = on_status
        self._on_video = on_video
        self._loader_threads = []
        
    def add_instance(self, name: str = "") -> StreamInstance:
        with self._lock:
            inst = StreamInstance(
                instance_id=self._next_id,
                name=name or f"Luồng {self._next_id}",
                on_log=self._on_log,
                on_status=self._on_status,
                on_video=self._on_video,
            )
            self.instances.append(inst)
            self._next_id += 1
            return inst
    
    def remove_instance(self, instance_id: int) -> bool:
        with self._lock:
            inst = self._get_instance(instance_id)
            if not inst:
                return False
            if inst.is_running:
                return False  # Không xoá khi đang chạy
            inst.stop()
            self.instances.remove(inst)
            return True
    
    def get_instance(self, instance_id: int) -> Optional[StreamInstance]:
        for inst in self.instances:
            if inst.id == instance_id:
                return inst
        return None
    
    def _get_instance(self, instance_id: int) -> Optional[StreamInstance]:
        for inst in self.instances:
            if inst.id == instance_id:
                return inst
        return None
    
    def stop_all(self):
        for inst in self.instances:
            inst.stop()
    
    @property
    def active_count(self) -> int:
        return sum(1 for inst in self.instances if inst.is_running)
    
    @property
    def total_count(self) -> int:
        return len(self.instances)
    
    def load_youtube_source(self, instance_id: int, url: str, download_dir: str = ""):
        """Tải nguồn YouTube trong thread riêng"""
        def _run():
            from core.video_source import download_youtube_videos
            dl_dir = download_dir or os.path.join(os.path.expanduser("~"), "Videos", "LiveStream_Cache")
            if self._on_log:
                self._on_log(instance_id, f"⬇️  Đang tải video từ YouTube...")
            videos = download_youtube_videos(url, dl_dir)
            inst = self.get_instance(instance_id)
            if inst:
                inst.playlist = videos
                if self._on_log:
                    self._on_log(instance_id, f"✅ Đã tải {len(videos)} video")
        
        t = threading.Thread(target=_run, daemon=True)
        t.start()
        self._loader_threads.append(t)
