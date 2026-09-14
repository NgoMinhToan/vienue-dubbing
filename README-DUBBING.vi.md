# VieNeu Dubbing WebUI

WebUI cục bộ dành cho lồng tiếng video bằng SRT tiếng Việt, sử dụng VieNeu v3 Turbo fp32 trên CPU. Không cần khóa API hay tài khoản. Lần đầu tạo giọng cần mạng để tải model; model được lưu trong thư mục dữ liệu.

## Chạy trên Windows

Gói ZIP tạo bằng `python scripts/package_dubbing.py` nằm trong `artifacts/vieneu-dubbing-windows.zip`. Gói có frontend build sẵn: chỉ cần Python 3.12, không cần Node.js. Giải nén vào thư mục có quyền ghi, chạy Setup.ps1 lần đầu rồi Start.bat. Đây là gói cài từ source, không phải EXE độc lập; model tải ở lần tạo giọng đầu tiên.

Yêu cầu khi cài từ source: Python 3.12, Node.js 22.12+ và mạng để tải dependencies/model.

```powershell
.\Setup.ps1
.\Start.bat
```

Trình duyệt mở tại http://127.0.0.1:7861. Để dừng, nhấn Ctrl+C trong cửa sổ server. Công cụ FFmpeg/FFprobe và MKVToolNix được cài riêng trong `.tools`, không thay đổi cài đặt toàn máy.

## Sử dụng

1. Tạo dự án, nhập video và SRT UTF-8/UTF-8 BOM.
2. Chọn giọng chung, bấm **Nghe mẫu giọng chung** rồi phát mẫu khi tạo xong; sửa văn bản, giọng hoặc tốc độ riêng từng câu nếu cần. Thay đổi tự lưu sau khoảng 1,2 giây.
3. Tạo giọng tất cả hoặc từng câu. Nghe câu bằng nút phát; chọn câu hoặc timeline để tua video.
4. Chọn cách trộn âm gốc. Nếu có nhiều track gốc, chọn đúng track trước khi xuất.
5. Chọn **Tải về → MP3** hoặc **MKV hai track**. Xem trước sử dụng bản âm thanh đã trộn; lần bấm đầu khi chưa có bản xuất sẽ tạo bản MP3.
6. Trong bảng Tải về, checkbox **Cho phát tiếp câu tràn** được tích mặc định: giữ câu tràn và chấp nhận chồng lời. Bỏ tích để bỏ qua toàn bộ lời lồng của câu vẫn tràn sau giới hạn tăng tốc; không cắt riêng phần đuôi. Cả hai chế độ đều xuất thẳng, không hỏi lại. Kết quả báo các câu bị bỏ qua; câu khác và nền giữ theo lựa chọn hiện tại.

Tăng tốc tự động sử dụng khoảng trống tới câu tiếp theo. Giới hạn tăng thêm nhân với tốc độ đã chọn, tổng tốc độ không vượt 3×. Câu cuối sử dụng khoảng trống tới hết video. Không dời các câu sau và không cắt mất phần cuối lời đọc.

MKV xuất có đúng hai audio tracks: **Original** (track gốc được chọn, không áp dụng giảm âm) và **Vietnamese Dub** (lời đọc trộn theo lựa chọn âm gốc, mặc định phát). Hình ảnh được remux, không mã hóa lại. Video không có âm thanh gốc chỉ xuất MP3.

## Dữ liệu và cấu hình

- `data/projects.sqlite3`: dự án và trạng thái chỉnh sửa.
- `data/projects/`: video nguồn, cache từng câu và các bản xuất.
- `data/models/`: model tải về; `data/tmp/`: tệp tạm.
- Sao lưu cả thư mục `data` khi server đã dừng.
- Tạo lại câu hoặc sửa nội dung làm bản xuất cũ không còn dùng cho dự án hiện tại; cần xuất lại.

Các biến môi trường: `APP_HOST` (mặc định `127.0.0.1`), `APP_PORT` (`7861`), `APP_DATA_DIR`, `APP_TEMP_DIR`, `HF_HOME`, `FFMPEG_BIN`, `FFPROBE_BIN`, `MKVMERGE_BIN`, `MKVEXTRACT_BIN`. Đường dẫn không phụ thuộc ký tự ổ đĩa Windows.

## Docker / Linux

Đã có Dockerfile riêng, backend chạy headless và dữ liệu tách khỏi image. Đã phát hiện và khởi động Docker Desktop qua đường dẫn cài đặt; trạng thái nghiệm thu được cập nhật trong docs/IMPLEMENTATION_STATUS.vi.md.

```sh
docker build -f docker/Dockerfile.dubbing -t vieneu-dubbing .
docker volume create vieneu-data
docker run --rm --name vieneu-dubbing -p 127.0.0.1:7861:7861 -v vieneu-data:/data vieneu-dubbing
```

Container dùng CPU, không cần CUDA; chạy user không phải root. Với bind mount thay named volume, thư mục phải ghi được bởi UID 1000. Khi triển khai domain sau này cần thêm xác thực, giới hạn upload, HTTPS và reverse proxy; bản hiện tại dành cho một người dùng cục bộ.

## Kiểm thử

```powershell
.venv\Scripts\python.exe -m pytest tests/dubbing -q
cd frontend
npm run build
```

Đã kiểm thử trên Windows: tạo giọng thật với model CPU, dự án video 12 giây / 3 câu, xuất MP3 và MKV, hai nhánh nguồn MP4/MKV có nhiều audio tracks, overlap, kiểm tra revision và chặn tải bản xuất cũ. Chưa lấy kết quả video ngắn làm cam kết hiệu năng cho phim dài.

## Phần còn lại của kế hoạch

- Đã bổ sung proxy H.264 khi trình duyệt không phát được video; nguồn xuất MKV vẫn là video gốc. Proxy giữ lại qua chỉnh sửa lời và tạo lại khi thay video.
- Đã bổ sung thay video/SRT trong dự án. SRT mới thay danh sách câu sau xác nhận; file lỗi không thay đổi nguồn hiện có. File video nguồn cũ còn giữ trên đĩa tới khi xóa dự án.
- Đã bổ sung nghe mẫu giọng chung ngay trong Lồng tiếng.
- Kiểm thử phim dài, timestamp lệch/phức tạp, dung lượng đĩa thấp, kiểm thử Docker/Linux và tinh chỉnh giao diện theo ảnh.
- Hai màn hình quản lý giọng và từ điển phát âm để giai đoạn sau theo phạm vi đã chốt.

Chi tiết yêu cầu, giai đoạn và quy trình MKV: [Kế hoạch](docs/DUBBING_WEBUI_PLAN.vi.md).

## Bổ sung về dữ liệu và tài nguyên

- Mức âm gốc **Giữ nguyên** giữ gain nền 100%, không duck khi có lời lồng. Bản phối cuối vẫn dùng limiter chống clipping; track Original trong MKV vẫn được copy nguyên bản.
- Hai ô `HH:MM:SS.mmm` trên mỗi câu cho sửa trực tiếp, lưu khi Enter/rời ô; ô đỏ báo thời gian không hợp lệ.
- Timeline: xám chưa tạo, xanh đã tạo, vàng chồng/tràn. Khi phát, tự chọn và cuộn đến câu tương ứng ở bảng lời/timeline. Kéo thân câu sang trái/phải để dời cả start/end, giữ nguyên thời lượng; có thể hoàn tác.

- Nút **Sửa mốc** nhận số giây bắt đầu/kết thúc; mốc không hợp lệ được báo lỗi.
- Cảnh báo SRT chồng nhau/vượt video hiển thị dưới vùng xem trước. Lời SRT ban đầu được lưu riêng khi nhập mới; dự án cũ giữ văn bản tại lần sửa đầu sau nâng cấp làm mốc gốc.
- Với nhiều audio tracks, tạo video tương thích sau khi chọn track để nghe đúng âm gốc trong preview.
- Giới hạn video mặc định 20 GiB (`APP_MAX_VIDEO_BYTES`); giữ tối thiểu 512 MiB khi lưu nguồn (`APP_MIN_FREE_BYTES`). Job còn dự trù dung lượng PCM theo thời lượng; đây là ước lượng, không đảm bảo mọi tác vụ tránh được hết đĩa.
- File trung gian của job được dọn sau khi kết thúc; video nguồn và các bản xuất hoàn chỉnh vẫn được giữ.
- Kiểm tra CPU offline bằng `HF_HUB_OFFLINE=1` và `python scripts/smoke_dubbing.py` sau khi model đã tải. Phép thử Windows đạt 3,84 giây audio trong 2,81 giây tổng hợp, model load 9,63 giây; chỉ là một câu mẫu.
- Khi tác vụ bị gián đoạn, mở lại dự án và bấm tạo giọng để tiếp tục các câu thiếu; các WAV đã tạo được dùng lại. Không tự chạy lại tác vụ sau khi mở ứng dụng.
- Nguồn có timestamp khác 0 được quy đổi về timeline của video. Nếu dự án nhập bằng bản cũ có thời lượng sai vì offset, hãy nhập lại video để cập nhật metadata rồi xuất lại.
