# Changelog

## Unreleased — 2026-09-14–15

### WebUI và media
- Hàng đợi phiên bản bền vững, chọn xử lý ngay/chờ, số thứ tự theo dự án, chỉnh sửa snapshot, hủy/thử lại/restart và xóa dự án sau khi worker dừng an toàn.
- Thêm chọn video/SRT từ APP_MEDIA_ROOT qua UI và scripts/media_cli.py; hỗ trợ mount nguồn chỉ đọc, chặn traversal/symlink ra ngoài.
- CI/CD GHCR: test + Docker smoke trước khi push, tag edge/SHA/semver và latest chỉ cho release ổn định.
- Thêm từ điển phát âm: luật một lượt, nhập/xuất JSON, thử lời engine, snapshot theo dự án và cache dựa trên lời thực đọc.
- Thêm màn hình thư viện giọng: metadata cục bộ có revision, tìm/lọc/yêu thích, sửa câu mẫu và nghe WAV qua worker CPU dùng chung.
- Thêm chế độ âm nền Giữ nguyên; timeline phân biệt chưa tạo, đã tạo và câu chồng âm.
- Tự theo dõi vị trí phát, sửa mốc thời gian trực tiếp, kéo cue trên timeline.
- Chọn trước giữ hoặc bỏ qua câu tràn khi xuất; tái sử dụng bản phối cùng revision và chính sách.
- Lưu job nguyên tử, phục hồi trạng thái gián đoạn và giữ cache khi hủy.
- Chuẩn hóa timestamp nguồn khi ghép MKV; kiểm thử VFR và hai audio track.
- Dọn cache/bản xuất cũ có xác nhận; bảo vệ nguồn và kết quả hiện hành.
- Bổ sung kiểm tra launcher, gói ZIP Windows và CI Windows/Linux.

### Kiểm chứng
- Nghiệm thu cuối CI 34874567845: 43 test qua trên mỗi OS Windows/Linux; frontend build, Docker import qua mount read-only, smoke và GHCR publish đều thành công. Ba giai đoạn hoàn thành theo EXECUTION_PLAN.vi.md.
- Giai đoạn 3: 42 test Windows qua. UI đã thêm/chỉnh sửa phiên bản và chạy MKV thật từ queue, kiểm định đúng một video + Original + Vietnamese Dub. Bổ sung smoke nhập SRT Unicode qua mount nguồn Docker read-only.
- 29 kiểm thử qua trong môi trường Python mới trên Windows.
- Benchmark TTS CPU 60 câu trên timeline 600 giây: 580,05 giây tổng hợp/xuất. Không phải phép đo 600 giây lời nói liên tục.
- TypeScript và Vite production build đã qua. CI 34869583419 qua Windows/Linux và build/khởi động Docker non-root, health và giao diện HTTP.
- Kiểm thử bổ sung fallback MOV tên Unicode qua trên Windows; editor 398 câu cuộn với 6–11 thẻ DOM, không có lỗi JavaScript trong lượt kiểm tra.

### Kế hoạch tiếp theo
- Repo riêng `NgoMinhToan/vienue-dubbing` đã được tạo và nhận source. Workflow SDK/PyPI kế thừa chỉ chạy ở upstream.
- Thư viện giọng và từ điển phát âm đã được người dùng xác nhận triển khai.
- GHCR, duyệt thư mục nguồn/mount Docker và hàng đợi phiên bản theo checklist.
