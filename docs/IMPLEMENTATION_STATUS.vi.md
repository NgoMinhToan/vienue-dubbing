# Trạng thái triển khai — 14/09/2026

## Cập nhật 14/09

- Job được ghi nguyên tử ngay khi vào hàng đợi và sau mỗi câu. Sau restart, job queued/running được đánh dấu gián đoạn cả trên đĩa; người dùng tạo tiếp sẽ dùng lại các câu đã cache.
- Đã kiểm thử hủy trong câu cuối: trạng thái cancelled, giữ WAV để tiếp tục, không báo complete sai.
- Sửa lỗi MKV nguồn có start khác 0 làm lệch track lồng tiếng. Chuẩn hóa timestamp video/audio gốc và hiệu chỉnh riêng nhánh MP4. Sửa cách đọc duration khi format/stream dùng quy ước khác nhau.
- **24 kiểm thử qua trên Windows và Linux container.** Fixture MP4/MKV có origin +5 giây, audio trễ 0/400 ms đều qua kiểm tra; onset MP3 giải mã sai lệch dưới 50 ms trong fixture. Chưa suy rộng thành bảo đảm mọi codec/edit list/VFR.
- Có `scripts/package_dubbing.py`: ZIP Windows chứa frontend build sẵn, mã nguồn/runtime scripts và manifest SHA256; không có dữ liệu/model. Gói này cần Python 3.12 và chạy Setup lần đầu, không phải EXE độc lập.
- Launcher kiểm tra công cụ, frontend và cổng trước khi mở trình duyệt. Còn nghiệm thu cài sạch trên máy Windows khác và tiến độ tải model chi tiết.

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

1. **Dữ liệu/editor:** đã thêm lời SRT gốc riêng, nút sửa start/end và cảnh báo SRT chồng/vượt video. Còn cần nghiệm thu UI với bộ phụ đề lớn.
2. **Preview:** proxy đã dùng đúng track được chọn và vô hiệu hóa khi đổi track; đã cho phát đuôi audio sau hết hình và thêm chú thích. Đã cache mẫu giọng; còn cache bản phối và nghiệm thu đồng bộ chuyên sâu.
3. **Media khó:** đã thêm fallback FFmpeg stream-copy khi mkvmerge không nhận diện nguồn. Đã so sánh hash frame giải mã trên fixture MP4/MKV. Còn nghiệm thu fallback trên định dạng khó và ánh xạ nhiều video/cover.
4. **Tài nguyên và khôi phục:** đã giới hạn upload mặc định 20 GiB, kiểm tra đĩa dự phòng, dọn file trung gian khi job kết thúc. Còn chính sách dọn cache/bản xuất cũ và nghiệm thu khi tắt ứng dụng giữa chừng.
5. **Đóng gói:** còn tiến độ tải model chi tiết, kiểm tra runtime/tool/cổng bận thân thiện hơn; gói phát hành Windows có frontend build sẵn. Đã thêm workflow CI Windows/Linux (chưa push/chạy trên GitHub); Docker đã build và chạy thực tế trên máy.

## Đã có nhưng chưa nghiệm thu đủ

- Đồng bộ sau seek, nguồn timestamp khác 0/âm, MP4 edit lists, VFR, MP3 encoder delay và lời vượt cuối video.
- Đo cả bốn preset nền, stereo, peak/clipping; so sánh payload hoặc audio/video giải mã để xác nhận stream copy.
- AVI/MOV/codec khó, đường dẫn Unicode, file hỏng, hết đĩa, thiếu model/tool, hủy và khởi động lại, chạy offline sau setup.
- Video 10 phút và 30–60 phút; 522–1.000 câu; thời gian tạo, RAM, dung lượng đĩa, cuộn/timeline và phản hồi UI ở nhiều độ phân giải.
- Cài sạch trên Windows; quyền bind volume trên máy khác và shutdown khi job đang chạy. Docker Desktop đã được tìm thấy ngoài PATH và khởi động để kiểm tra Linux.

Đã xác minh: **18 kiểm thử thành công trên Windows và Linux container**, gồm bốn hệ số nền stereo và hash frame video sau remux. TypeScript/production build thành công. Docker image build thành công; trang WebUI Linux đã mở trên cổng kiểm thử 7862 (container kiểm thử đã dừng). Bộ test Linux dùng source mới nhất bind read-only; image cần rebuild khi source tiếp tục thay đổi.

CPU offline: Windows tạo 3,84 giây audio trong 2,81 giây, load model 9,63 giây; Linux container `--network none` tạo 3,92 giây audio trong 11,77 giây, load model 53,15 giây. Hai phép đo đơn lẻ trong điều kiện tải hệ thống khác nhau, không phải so sánh hiệu năng hai OS.

Benchmark **bộ trộn tổng hợp, không gồm inference TTS**: 1.000 cue/10 phút mất 5,92 giây; 1.000 cue/60 phút mất 31,4 giây, file PCM khoảng 1,38 GB. File fixture được dọn sau phép thử. Chưa đo RAM peak hay benchmark TTS đầy đủ cho phim dài; chưa xác nhận đạt các ngưỡng đồng bộ ở kế hoạch.

## Để giai đoạn sau theo phạm vi đã chốt

- Màn hình quản lý thư viện giọng đầy đủ và từ điển phát âm.
- Domain, HTTPS, xác thực, nhiều người dùng và vận hành Docker image chính thức.

Thứ tự đề xuất: sửa tính đúng đắn của preview và cảnh báo → xử lý media khó/tài nguyên → nghiệm thu video dài/offline → cài sạch Windows và Linux/Docker → đóng gói phát hành.
