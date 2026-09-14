# Giai đoạn 2: thư viện cục bộ

## Thư viện giọng

- [x] Lưu metadata trong SQLite cùng thư mục dữ liệu; giữ nguyên ID preset của engine.
- [x] Tìm theo tên/mô tả/thẻ; lọc giới tính, vùng miền, phong cách và yêu thích.
- [x] Sửa tên hiển thị, mô tả, thẻ, câu mẫu. Metadata không thay đổi giọng tổng hợp.
- [x] Nghe mẫu bằng worker CPU dùng chung để không chạy inference đồng thời.
- [x] Cache mẫu theo ID giọng và câu mẫu; phục vụ WAV qua API cục bộ.

## Từ điển phát âm

- [x] Luật gồm từ gốc, cách đọc, cả từ, phân biệt hoa thường và bật/tắt.
- [x] Thay thế một lượt trên văn bản đầu vào, ưu tiên luật ở trên khi trùng; không thay đệ quy kết quả.
- [x] Nhập/xuất JSON có version; kiểm tra tất cả luật trước khi lưu nguyên tử.
- [x] Xem văn bản thực đưa vào engine; giữ nguyên lời hiển thị/SRT.
- [x] Snapshot luật vào dự án khi áp dụng; tăng revision để vô hiệu hóa bản phối cũ.
- [x] Cache WAV theo văn bản sau xử lý; câu không bị ảnh hưởng có thể dùng lại.
- [x] Chặn áp dụng khi dự án đang chạy, tránh thay đổi đầu vào giữa job.

API nhận JSON và dùng đường dẫn dưới data, không gọi dialog/shell Windows. Cùng thiết kế dùng được khi mount data vào Docker.
