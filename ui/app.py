"""
LiveStream Pro 2.0 — Multi-thread, multi-tab
© Ngọc NX
"""
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import os, sys, threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.stream_manager import StreamManager, StreamInstance
from core.stream_engine import StreamStatus

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

APP_NAME = "LiveStream Pro 2.0"
APP_VER = "2.0"

class StreamPanel(ctk.CTkFrame):
    """Panel cho 1 luồng stream"""
    def __init__(self, parent, instance: StreamInstance, manager: StreamManager, on_delete=None):
        super().__init__(parent, fg_color="transparent")
        self.instance = instance
        self.manager = manager
        self._on_delete = on_delete
        self._locked = False  # đang chạy → khoá
        self._build()
        
    def _build(self):
        self.pack(fill="both", expand=True, padx=10, pady=10)
        self.columnconfigure(1, weight=1)
        
        row = 0
        
        # ── Nguồn video ──
        ctk.CTkLabel(self, text="📂 Nguồn video", font=("Segoe UI", 12, "bold")).grid(row=row, column=0, columnspan=3, sticky="w", pady=(0,4))
        row += 1
        
        self.src_type = ctk.CTkSegmentedButton(self, values=["Local", "YouTube", "Drive"], 
                                                 command=self._on_src_type)
        self.src_type.grid(row=row, column=0, columnspan=3, sticky="w", pady=(0,4))
        row += 1
        
        self.src_entry = ctk.CTkEntry(self, placeholder_text="Đường dẫn file / thư mục / link...")
        self.src_entry.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0,4))
        
        self.src_btn = ctk.CTkButton(self, text="📁 Chọn", width=80, command=self._browse)
        self.src_btn.grid(row=row, column=2, padx=(4,0), pady=(0,4))
        row += 1
        
        self.load_btn = ctk.CTkButton(self, text="🔄 Tải danh sách", command=self._load_source)
        self.load_btn.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0,8))
        row += 1
        
        # Playlist info
        self.playlist_label = ctk.CTkLabel(self, text="📹 0 video", font=("Segoe UI", 10))
        self.playlist_label.grid(row=row, column=0, columnspan=3, sticky="w", pady=(0,8))
        row += 1
        
        # ── Separator ──
        ctk.CTkFrame(self, height=1, fg_color="#333").grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0,8))
        row += 1
        
        # ── Stream Key ──
        ctk.CTkLabel(self, text="📡 Stream Key", font=("Segoe UI", 12, "bold")).grid(row=row, column=0, columnspan=3, sticky="w", pady=(0,4))
        row += 1
        
        self.key_entry = ctk.CTkEntry(self, placeholder_text="Nhập Stream Key...")
        self.key_entry.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0,4))
        row += 1
        
        # Platform selector
        self.platform_var = ctk.StringVar(value="youtube")
        plat_row = ctk.CTkFrame(self, fg_color="transparent")
        plat_row.grid(row=row, column=0, columnspan=3, sticky="w", pady=(0,8))
        
        for p, icon in [("youtube", "🔴 YouTube"), ("facebook", "🔵 Facebook"), ("tiktok", "⚫ TikTok")]:
            ctk.CTkRadioButton(plat_row, text=icon, variable=self.platform_var, 
                               value=p, font=("Segoe UI", 11)).pack(side="left", padx=(0,12))
        row += 1
        
        # ── Separator ──
        ctk.CTkFrame(self, height=1, fg_color="#333").grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0,8))
        row += 1
        
        # ── Cấu hình ──
        ctk.CTkLabel(self, text="⚙️ Cấu hình", font=("Segoe UI", 12, "bold")).grid(row=row, column=0, columnspan=3, sticky="w", pady=(0,4))
        row += 1
        
        cfg = ctk.CTkFrame(self, fg_color="transparent")
        cfg.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0,8))
        cfg.columnconfigure(1, weight=1)
        cfg.columnconfigure(3, weight=1)
        
        self.res_var = ctk.StringVar(value="1280x720")
        self.loop_var = ctk.StringVar(value="shuffle")
        self.vbit_var = ctk.StringVar(value="3000")
        self.abit_var = ctk.StringVar(value="128")
        self.fps_var = ctk.StringVar(value="30")
        
        ctk.CTkLabel(cfg, text="Độ phân giải:", font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w", pady=1)
        ctk.CTkOptionMenu(cfg, variable=self.res_var, values=["1920x1080","1280x720","854x480","640x360"], width=120).grid(row=0, column=1, sticky="w", padx=(0,8), pady=1)
        ctk.CTkLabel(cfg, text="Vòng lặp:", font=("Segoe UI", 10)).grid(row=0, column=2, sticky="w", pady=1)
        ctk.CTkOptionMenu(cfg, variable=self.loop_var, values=["shuffle","sequential","single"], width=120).grid(row=0, column=3, sticky="w", pady=1)
        
        ctk.CTkLabel(cfg, text="Video bitrate:", font=("Segoe UI", 10)).grid(row=1, column=0, sticky="w", pady=1)
        ctk.CTkEntry(cfg, textvariable=self.vbit_var, width=70).grid(row=1, column=1, sticky="w", padx=(0,8), pady=1)
        ctk.CTkLabel(cfg, text="Audio bitrate:", font=("Segoe UI", 10)).grid(row=1, column=2, sticky="w", pady=1)
        ctk.CTkEntry(cfg, textvariable=self.abit_var, width=70).grid(row=1, column=3, sticky="w", pady=1)
        
        ctk.CTkLabel(cfg, text="FPS:", font=("Segoe UI", 10)).grid(row=2, column=0, sticky="w", pady=1)
        ctk.CTkOptionMenu(cfg, variable=self.fps_var, values=["24","25","30","60"], width=70).grid(row=2, column=1, sticky="w", padx=(0,8), pady=1)
        row += 1
        
        # ── Nút điều khiển ──
        ctrl = ctk.CTkFrame(self, fg_color="transparent")
        ctrl.grid(row=row, column=0, columnspan=3, pady=(8,0))
        row += 1
        
        self.start_btn = ctk.CTkButton(ctrl, text="▶ PHÁT", width=140, height=36,
                                        fg_color="#27AE60", hover_color="#1E8449",
                                        font=("Segoe UI", 13, "bold"), command=self._start)
        self.start_btn.pack(side="left", padx=4)
        
        self.stop_btn = ctk.CTkButton(ctrl, text="⏹ DỪNG", width=100, height=36,
                                       fg_color="#E74C3C", hover_color="#C0392B",
                                       font=("Segoe UI", 13, "bold"), state="disabled",
                                       command=self._stop)
        self.stop_btn.pack(side="left", padx=4)
        
        # Status
        self.status_var = ctk.StringVar(value="⏸ Chờ")
        ctk.CTkLabel(self, textvariable=self.status_var, font=("Segoe UI", 10)).grid(row=row, column=0, columnspan=3, sticky="w", pady=(4,0))
        
        self._update_ui()
    
    def _on_src_type(self, val):
        phs = {"Local": "Đường dẫn file / thư mục...", 
               "YouTube": "Link YouTube video / playlist...",
               "Drive": "Link Google Drive..."}
        self.src_entry.configure(placeholder_text=phs.get(val, ""))
    
    def _browse(self):
        if self.src_type.get() == "Local":
            p = filedialog.askdirectory()
            if p:
                self.src_entry.delete(0, "end")
                self.src_entry.insert(0, p)
        elif self.src_type.get() == "YouTube":
            # Paste link - just focus
            pass
    
    def _load_source(self):
        src = self.src_type.get()
        path = self.src_entry.get().strip()
        if not path:
            return
        if src == "Local":
            if os.path.isfile(path):
                self.instance.playlist = [path]
            elif os.path.isdir(path):
                from core.video_source import get_local_videos
                self.instance.playlist = get_local_videos(path)
            self.playlist_label.configure(text=f"📹 {len(self.instance.playlist)} video")
            if hasattr(self, '_on_log') and self._on_log:
                self._on_log(self.instance.id, f"📂 Đã tải {len(self.instance.playlist)} video")
        elif src == "YouTube":
            self.manager.load_youtube_source(self.instance.id, path)
    
    def _start(self):
        key = self.key_entry.get().strip()
        if not key:
            messagebox.showwarning("Thiếu key", "Vui lòng nhập Stream Key!")
            return
        if not self.instance.playlist:
            messagebox.showwarning("Thiếu video", "Vui lòng tải nguồn video trước!")
            return
        
        self.instance.stream_key = key
        self.instance.platform = self.platform_var.get()
        self.instance.resolution = self.res_var.get()
        self.instance.fps = int(self.fps_var.get())
        self.instance.video_bitrate = self.vbit_var.get()
        self.instance.audio_bitrate = self.abit_var.get()
        self.instance.loop_mode = self.loop_var.get()
        
        self._locked = True
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self._update_ui()
        self.instance.start()
    
    def _stop(self):
        self.instance.stop()
        self._locked = False
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.status_var.set("⏸ Đã dừng")
        self._update_ui()
    
    def _update_ui(self):
        """Bật/tắt config khi đang chạy"""
        state = "disabled" if self._locked else "normal"
        for w in [self.src_entry, self.src_btn, self.load_btn,
                  self.key_entry, self.src_type]:
            try: w.configure(state=state)
            except: pass
    
    def update_status(self, status: StreamStatus):
        if status == StreamStatus.RUNNING:
            self.status_var.set("▶ ĐANG PHÁT")
            self._live_dot = "🔴"
        elif status == StreamStatus.STOPPED:
            self.status_var.set("⏹ Đã dừng")
        elif status == StreamStatus.ERROR:
            self.status_var.set("❌ Lỗi")
        elif status == StreamStatus.IDLE:
            self.status_var.set("⏸ Chờ")


class LiveStreamApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title(f"{APP_NAME} v{APP_VER}")
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h = 1200, 850
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
        self.minsize(1000, 700)
        
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # Manager
        self.manager = StreamManager(
            on_log=self._on_log,
            on_status=self._on_status,
            on_video=self._on_video
        )
        
        # Build UI
        self._build_ui()
        
        # Thêm luồng mặc định
        self._add_tab()
    
    def _build_ui(self):
        # Header
        hdr = ctk.CTkFrame(self, height=44, corner_radius=0, fg_color="#1a1a2e")
        hdr.pack(fill="x")
        
        ctk.CTkLabel(hdr, text=f"🐉 {APP_NAME} v{APP_VER}", 
                      font=("Segoe UI", 16, "bold")).pack(side="left", padx=16)
        
        # Theme toggle
        self.theme_btn = ctk.CTkButton(hdr, text="🌙", width=32, height=26,
                                        fg_color="transparent",
                                        command=self._toggle_theme)
        self.theme_btn.pack(side="right", padx=12)
        
        # Main area
        main = ctk.CTkFrame(self)
        main.pack(fill="both", expand=True)
        
        # Left: tabs
        self.tab_view = ctk.CTkTabview(main, anchor="nw")
        self.tab_view.pack(side="left", fill="both", expand=True)
        
        # Right: log
        log_frame = ctk.CTkFrame(main, width=380)
        log_frame.pack(side="right", fill="y")
        log_frame.pack_propagate(False)
        
        ctk.CTkLabel(log_frame, text="📋 Nhật ký", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=10, pady=(8,4))
        
        self.log_text = ctk.CTkTextbox(log_frame, font=("Consolas", 10), 
                                        fg_color="#0a0a15", text_color="#00e57a")
        self.log_text.pack(fill="both", expand=True, padx=6, pady=(0,6))

        # Bottom controls bar
        bot = ctk.CTkFrame(self, height=36, corner_radius=0, fg_color="#1a1a2e")
        bot.pack(fill="x")
        
        ctk.CTkLabel(bot, textvariable=ctk.StringVar(value=f"🟢 {self.manager.active_count}/{self.manager.total_count} luồng"),
                      font=("Segoe UI", 10)).pack(side="left", padx=12)
    
    def _add_tab(self):
        inst = self.manager.add_instance()
        tab_name = f"Luồng {inst.id}"
        tab = self.tab_view.add(tab_name)
        
        panel = StreamPanel(tab, inst, self.manager, on_delete=self._delete_tab)
        inst.config_panel = panel
        
        # Nút xoá luồng trên tab
        close_btn = ctk.CTkButton(tab, text="✕", width=24, height=20, fg_color="transparent",
                                   hover_color="#E74C3C", font=("Segoe UI", 10),
                                   command=lambda i=inst.id: self._confirm_delete(i))
        close_btn.place(relx=1.0, x=-30, y=4, anchor="ne")
        
        # Nút thêm luồng mới
        add_btn = ctk.CTkButton(tab, text="+ Thêm luồng", width=100, height=28,
                                 font=("Segoe UI", 10), command=self._add_tab)
        add_btn.place(relx=1.0, x=-4, y=4, anchor="ne")
        
        self.tab_view.set(tab_name)
    
    def _confirm_delete(self, instance_id: int):
        inst = self.manager.get_instance(instance_id)
        if not inst:
            return
        if inst.is_running:
            messagebox.showwarning("Đang phát", "Không thể xoá luồng đang phát!\nHãy dừng luồng trước.")
            return
        
        if messagebox.askyesno("Xác nhận", f"Xoá {inst.name}?"):
            self.manager.remove_instance(instance_id)
            # Xoá tab
            for tab_name in self.tab_view._tab_names:
                if tab_name == inst.name or tab_name == f"Luồng {instance_id}":
                    try:
                        self.tab_view.delete(tab_name)
                    except:
                        pass
                    break
    
    def _delete_tab(self, instance_id):
        # Handled by _confirm_delete
        pass
    
    def _toggle_theme(self):
        current = ctk.get_appearance_mode()
        new = "light" if current == "Dark" else "dark"
        ctk.set_appearance_mode(new)
        self.theme_btn.configure(text="☀️" if new == "light" else "🌙")
    
    def _on_log(self, instance_id: int, message: str):
        if not self.winfo_exists():
            return
        try:
            tag = f"[L{instance_id}]" if instance_id else ""
            self.log_text.insert("end", f"{tag} {message}\n")
            self.log_text.see("end")
        except:
            pass
    
    def _on_status(self, instance_id: int, status: StreamStatus):
        inst = self.manager.get_instance(instance_id)
        if inst and inst.config_panel:
            inst.config_panel.update_status(status)
    
    def _on_video(self, instance_id: int, path: str):
        pass
    
    def _on_closing(self):
        self.manager.stop_all()
        self.destroy()


if __name__ == "__main__":
    app = LiveStreamApp()
    app.mainloop()
