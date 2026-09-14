# Changelog

## Unreleased — 2026-09-14

### WebUI và media
- Thêm chế độ âm nền Giữ nguyên; timeline phân biệt chưa tạo, đã tạo và câu chồng âm.
- Tự theo dõi vị trí phát, sửa mốc thời gian trực tiếp, kéo cue trên timeline.
- Chọn trước giữ hoặc bỏ qua câu tràn khi xuất; tái sử dụng bản phối cùng revision và chính sách.
- Lưu job nguyên tử, phục hồi trạng thái gián đoạn và giữ cache khi hủy.
- Chuẩn hóa timestamp nguồn khi ghép MKV; kiểm thử VFR và hai audio track.
- Dọn cache/bản xuất cũ có xác nhận; bảo vệ nguồn và kết quả hiện hành.
- Bổ sung kiểm tra launcher, gói ZIP Windows và CI Windows/Linux.

### Kiểm chứng
- 29 kiểm thử qua trong môi trường Python mới trên Windows.
- Benchmark TTS CPU 60 câu trên timeline 600 giây: 580,05 giây tổng hợp/xuất. Không phải phép đo 600 giây lời nói liên tục.
- TypeScript và Vite production build đã qua. Linux CI và rebuild Docker của mốc này còn chờ nghiệm thu.

### Kế hoạch tiếp theo
- Thư viện giọng và từ điển phát âm đã được người dùng xác nhận triển khai.
- GHCR, duyệt thư mục nguồn/mount Docker và hàng đợi phiên bản theo checklist.
