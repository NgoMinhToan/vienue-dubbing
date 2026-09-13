# Trạng thái triển khai — 13/09/2026

Đối chiếu với DUBBING_WEBUI_PLAN.vi.md. Đây là trạng thái mã nguồn hiện tại, không phải xác nhận toàn bộ kế hoạch đã nghiệm thu.

## Đã triển khai

- WebUI React/FastAPI cục bộ; v3 Turbo fp32, CPU ONNX, 23 giọng; không có luồng API trả phí.
- Dự án video/SRT, thay nguồn có kiểm tra revision, tự lưu, sửa lời/giọng/tốc độ, hoàn tác/làm lại, danh sách câu ảo hóa và timeline.
- Tạo giọng từng câu/toàn bộ, cache WAV, nghe mẫu giọng chung; số câu đã tạo và vô hiệu hóa nút khi đủ.
- Giữ start, dùng khoảng nghỉ, tăng tốc giới hạn, cảnh báo và cho xuất chồng lời.
- Bốn chế độ nền, xuất MP3 và MKV hai track bằng mkvmerge; hai nhánh nguồn MKV và không-MKV.
- Proxy H.264, chuyển âm gốc/lồng tiếng có nhãn và màu; con trỏ timeline cập nhật theo frame và tiến trình có chuyển động mượt.
- Setup/Start Windows, cấu hình đường dẫn bên ngoài mã nguồn, Dockerfile headless/non-root, hướng dẫn chạy.

## Chưa triển khai đầy đủ

1. **Dữ liệu/editor:** lưu riêng lời SRT ban đầu và lời đã sửa; sửa start/end trực tiếp trên UI; cảnh báo riêng khi SRT chồng nhau hoặc nằm ngoài video ngay lúc nhập. Hiện đã kiểm tra encoding, cú pháp và end > start.
2. **Preview:** nghe đúng track gốc đã chọn khi nguồn có nhiều audio; proxy hiện lấy audio đầu tiên. Hoàn thiện phát phần đuôi lồng tiếng dài hơn hình và cảnh báo tương ứng. Cache mẫu giọng/bản phối để tránh tạo lại không cần thiết.
3. **Media khó:** fallback remux trung gian bằng FFmpeg khi mkvmerge không đọc container nguồn; kiểm định video/audio copy sâu hơn việc đếm hai track. Cần rà soát ánh xạ video chính khi có nhiều video/cover.
4. **Tài nguyên và khôi phục:** giới hạn dung lượng upload video, kiểm tra đĩa trống trước xử lý, dọn file tạm/job lỗi/bản xuất cũ, giảm dung lượng cache. Khôi phục trạng thái job đã có ở mức cơ bản, chưa nghiệm thu đầy đủ khi tắt ứng dụng giữa chừng.
5. **Đóng gói:** tiến độ tải model chi tiết, kiểm tra runtime/tool/cổng bận thân thiện hơn; gói phát hành Windows có frontend build sẵn; CI Linux và kiểm tra Docker thực tế.

## Đã có nhưng chưa nghiệm thu đủ

- Đồng bộ sau seek, nguồn timestamp khác 0/âm, MP4 edit lists, VFR, MP3 encoder delay và lời vượt cuối video.
- Đo cả bốn preset nền, stereo, peak/clipping; so sánh payload hoặc audio/video giải mã để xác nhận stream copy.
- AVI/MOV/codec khó, đường dẫn Unicode, file hỏng, hết đĩa, thiếu model/tool, hủy và khởi động lại, chạy offline sau setup.
- Video 10 phút và 30–60 phút; 522–1.000 câu; thời gian tạo, RAM, dung lượng đĩa, cuộn/timeline và phản hồi UI ở nhiều độ phân giải.
- Cài sạch trên Windows; build/chạy Linux/Docker, quyền volume, shutdown và CPU inference trong container. Môi trường hiện chưa có Docker.

Đã xác minh: 11 kiểm thử backend/media thành công ở lần chạy gần nhất; TypeScript và production build thành công; tạo giọng CPU thật và MP3/MKV trên video 12 giây, tạo mẫu giọng và proxy H.264, kiểm tra các thao tác giao diện chính. Chưa dùng kết quả này để khẳng định đạt các chỉ tiêu đồng bộ/hiệu năng trong kế hoạch.

## Để giai đoạn sau theo phạm vi đã chốt

- Màn hình quản lý thư viện giọng đầy đủ và từ điển phát âm.
- Domain, HTTPS, xác thực, nhiều người dùng và vận hành Docker image chính thức.

Thứ tự đề xuất: sửa tính đúng đắn của preview và cảnh báo → xử lý media khó/tài nguyên → nghiệm thu video dài/offline → cài sạch Windows và Linux/Docker → đóng gói phát hành.
