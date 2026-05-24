# 🎬 LiveStream Pro

Stream video 24/7 lên **YouTube**, **Facebook**, **TikTok** từ máy tính Windows.

---

## ✅ Tính năng

- **Nguồn video đa dạng:**
  - 📁 File video / Thư mục local
  - ▶️ Link YouTube (video đơn hoặc playlist)
  - ☁️ Google Drive (file hoặc folder)
- **Stream đồng thời** lên nhiều kênh cùng lúc
- **Vòng lặp 24/7**: shuffle, tuần tự, hoặc một video lặp lại
- **Overlay text** và đồng hồ thời gian thực trên video
- **Cấu hình linh hoạt**: độ phân giải, bitrate, FPS, âm lượng
- **Lưu/tải Profile** để dùng lại
- **Custom RTMP** cho bất kỳ nền tảng nào

---

## 🛠 Yêu cầu cài đặt

### 1. Python 3.8+
Tải tại: https://python.org

### 2. FFmpeg (bắt buộc)
```
# Tải FFmpeg Windows: https://ffmpeg.org/download.html
# Giải nén và thêm vào PATH, hoặc đặt ffmpeg.exe vào cùng thư mục
```

### 3. Thư viện Python
```bash
pip install -r requirements.txt
```

Hoặc cài thủ công:
```bash
pip install yt-dlp          # Cho YouTube
pip install gdown           # Cho Google Drive (tùy chọn)
```

---

## 🚀 Chạy ứng dụng

```bash
cd livestream_app
python main.py
```

Hoặc double-click `run.bat` (Windows).

---

## 📖 Hướng dẫn sử dụng

### Bước 1: Chọn nguồn video
- **Local**: Click "Chọn Folder" hoặc "Chọn File(s)"
- **YouTube**: Dán link video/playlist, chọn chế độ stream hoặc tải về
- **Google Drive**: Dán link folder/file Drive

Click **"🔄 Tải danh sách"** để nạp video.

### Bước 2: Cấu hình kênh stream
- Tick vào **YouTube / Facebook / TikTok** tương ứng
- Nhập **Stream Key** (lấy từ trang quản lý kênh)

> **Lấy Stream Key:**
> - YouTube: https://studio.youtube.com → Đăng Live → Phần mềm stream
> - Facebook: https://www.facebook.com/live/producer
> - TikTok: TikTok Live Studio → Settings

### Bước 3: Điều chỉnh cài đặt (tùy chọn)
- Độ phân giải, FPS, bitrate
- Chữ overlay, đồng hồ
- Chế độ vòng lặp

### Bước 4: Bắt đầu stream
Click **"▶ BẮT ĐẦU STREAM"**.

---

## 🔧 Cài đặt nâng cao

### Stream Key lấy ở đâu?

| Nền tảng | URL |
|----------|-----|
| YouTube  | https://studio.youtube.com → Đăng Live |
| Facebook | https://www.facebook.com/live/producer |
| TikTok   | TikTok Live Studio → Cài đặt |

### Bitrate khuyến nghị

| Chất lượng | Video | Audio | Độ phân giải |
|-----------|-------|-------|--------------|
| 1080p FHD | 6000k | 192k  | 1920x1080    |
| 720p HD   | 3000k | 128k  | 1280x720     |
| 480p SD   | 1500k | 96k   | 854x480      |

---

## ❓ Xử lý lỗi thường gặp

**"Không tìm thấy FFmpeg"**
→ Cài FFmpeg và thêm vào PATH Windows

**"yt-dlp chưa được cài"**
→ Chạy: `pip install yt-dlp`

**Stream bị ngắt liên tục**
→ Giảm bitrate, kiểm tra tốc độ mạng upload

**Lỗi Google Drive**
→ Đảm bảo file/folder được chia sẻ "Anyone with the link"

---

## 📁 Cấu trúc project

```
livestream_app/
├── main.py              # Entry point
├── requirements.txt     # Thư viện cần cài
├── core/
│   ├── stream_engine.py # Xử lý FFmpeg stream
│   ├── video_source.py  # Quản lý nguồn video
│   └── config_manager.py# Lưu/tải cấu hình
└── ui/
    └── app.py           # Giao diện Tkinter
```
