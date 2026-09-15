# Trạng thái triển khai — 15/09/2026

Checklist chính: [EXECUTION_PLAN.vi.md](EXECUTION_PLAN.vi.md).

## Giai đoạn 1 — Đã hoàn thành

- Editor: preview có nhãn/màu, tiến trình mượt, số câu đã tạo, mốc sửa trực tiếp, kéo timeline, theo dõi câu đang phát và màu trạng thái.
- Media: năm chế độ nền, giữ start/dùng khoảng nghỉ/tăng tốc giới hạn; giữ hoặc bỏ toàn câu tràn; MP3 và MKV đúng hai audio track.
- Tài nguyên: cache WAV và bản phối, dọn dữ liệu có xác nhận, giới hạn dung lượng, lưu job nguyên tử và khôi phục gián đoạn.
- CI 34869583419 qua Windows/Linux, build Docker và khởi động non-root. Gói ZIP Windows có frontend build sẵn.
- Benchmark TTS CPU: 60 câu trên timeline 600 giây mất 580,05 giây; không tương đương 600 giây lời nói liên tục. Bộ trộn tổng hợp 1.000 câu/60 phút mất 31,4 giây trong phép đo trước đó.
- UI 398 câu cuộn với 6–11 thẻ DOM, không có lỗi JavaScript trong lượt kiểm tra.

## Giai đoạn 2 — Đã hoàn thành

- Thư viện 23 giọng: tên/mô tả/thẻ/yêu thích/bộ lọc, câu mẫu, nghe mẫu độc lập qua worker CPU chung; ID engine giữ nguyên. Commit 23f5486.
- Từ điển: thay một lượt, cả từ/hoa thường/bật tắt, nhập/xuất JSON, lời xem thử, snapshot vào dự án và cache theo lời thực đọc. Commit cfa0775.
- Kiểm thử metadata sau restart, revision conflict, mẫu cache, luật Unicode và tính bất biến của snapshot.

## Giai đoạn 3 — Đã hoàn thành

- GHCR đã publish thật và kiểm tra digest qua CI 34871803582: ghcr.io/ngominhtoan/vienue-dubbing. Tag edge/SHA; phiên bản theo tag, latest chỉ release ổn định. Chưa tạo release ổn định. [Hướng dẫn](DOCKER_PUBLISH.vi.md).
- Duyệt/import video và SRT từ APP_MEDIA_ROOT qua UI/CLI; root mặc định cwd, chặn traversal/symlink ra ngoài, dùng nguồn mount chỉ đọc. Commit 7418f41.
- Queue: snapshot riêng, chờ/xử lý ngay, số phiên bản, chỉnh sửa gỡ item và khôi phục dự án, hủy/thử lại/restart, xóa dự án đợi worker dừng. Commit 209cb7f. [Hướng dẫn](QUEUE.vi.md).
- UI đã thử thêm phiên bản, chỉnh sửa về dự án và xuất MKV thực; mkvmerge xác nhận một video + Original + Vietnamese Dub.
- CI cuối [34874567845](https://github.com/NgoMinhToan/vienue-dubbing/actions/runs/34874567845): **43 test qua trên mỗi OS Windows/Linux**, frontend build, mount nguồn read-only, Docker smoke và publish đều thành công. Code image b230ed3; digest được ghi trong DOCKER_PUBLISH.vi.md.
- Mẫu giọng thật từ màn hình thư viện tạo và phát WAV 4,48 giây; không có lỗi JavaScript trong lượt nghiệm thu UI.

## Giới hạn đã ghi nhận

- Chưa thử mọi codec/edit list/VFR của video thực tế; các fixture timestamp/VFR, fallback MOV và nhiều audio đã có test.
- Chưa đo RAM peak cho phim dài; cài sạch Windows được thử bằng venv mới trên cùng máy, không phải máy vật lý thứ hai.
- Tiến độ tải model đang ở mức trạng thái, chưa có phần trăm mỗi file. Offline sau khi tải model đã được thử trước đây trên Windows và Linux.
- Docker Desktop local chưa chạy; nghiệm thu container hiện dùng GitHub Linux runner. Chỉ hỗ trợ linux/amd64, một instance trên mỗi data volume.
- Domain/HTTPS/auth/nhiều người dùng không nằm trong đợt này.


### Cập nhật phạm vi ngày 15/09/2026
Từ điển đã lưu áp dụng chung cho tất cả dự án và nghe mẫu giọng. Dự án hiện có tự cập nhật, chỉ các câu đổi lời đọc cần tạo lại; file âm thanh đã xuất không bị sửa. Phiên bản hàng đợi đã tạo giữ snapshot cũ, phiên bản tạo mới dùng luật hiện hành. Không còn bước áp dụng riêng cho dự án.
Phòng thu đã hỗ trợ clone CPU, lưu giọng custom và dùng trong lồng tiếng. Xem `docs/STUDIO.vi.md` để biết cách dùng và các kiểm chứng còn mở.
