# Phòng thu — giọng tùy chỉnh

1. Mở **Phòng thu**, chọn file âm thanh hoặc **Thu bằng micro** (tối đa 60 giây thu; localhost hoặc HTTPS).
2. Nghe file nguồn, đặt mốc bắt đầu/kết thúc cho đoạn 3–8 giây nói rõ, một người, ít tạp âm. File tối đa 50 MB.
3. Nhập tên giọng và câu thử; bấm **Tạo giọng và nghe thử**. Tác vụ dùng worker CPU chung với lồng tiếng, hiển thị từng bước và có Dừng.
4. Nghe mẫu đã chọn và bản đọc thử; bấm **Lưu vào thư viện**. Mở Giọng nói để chỉnh metadata/thẻ/câu mẫu, hoặc Lồng tiếng để chọn giọng chung/từng câu.
5. Khi lỗi hoặc hủy, chọn **Thử lại từ mẫu nguồn**. Khi server khởi động lại, tác vụ gián đoạn được đánh dấu đã dừng, không tự chạy.

Giọng có ID `custom:<uuid>` bất biến. `APP_DATA_DIR/studio/<uuid>` chứa file nguồn, WAV đã chọn, embedding/codes NPZ và trạng thái JSON. Sửa tên/thẻ không đổi giọng. Để tạo chất giọng khác, tạo ID mới; cache và snapshot cũ không bị đổi.

Xóa giọng trong Phòng thu có xác nhận; bị chặn nếu dự án hoặc snapshot hàng đợi còn tham chiếu, hoặc worker còn dùng dữ liệu. Đổi giọng trong dự án và gỡ các phiên bản liên quan trước khi xóa.

Từ điển phát âm dùng cho câu thử và các lần tạo giọng tiếp theo. Mẫu âm thanh nguồn không bị áp dụng từ điển. Không cần nhập lời chép của mẫu hay API trả phí.

## Windows / Docker

Mount toàn bộ APP_DATA_DIR để giữ studio, SQLite, dự án và cache model. Dữ liệu giọng không ghi vào thư mục source/model cài sẵn. Engine dùng ONNX CPU fp32; clone cần speaker_encoder.onnx và codec encoder từ model v3 Turbo. Lần đầu có thể cần tải model; sau khi cache đầy đủ có thể dùng offline. Micro chạy ở trình duyệt của người dùng, không cần thiết bị âm thanh trong container. Khi đưa lên domain cần HTTPS để dùng micro.

## Kiểm chứng và giới hạn

- Clone thật trên Windows CPU từ mẫu tổng hợp: 34,62 giây gồm nạp model và tạo bản thử 2,88 giây. Không phải benchmark độ giống giọng người thật.
- Giọng lưu NPZ đã được nạp bằng tiến trình mới offline: bản thử 2,88 giây, khoảng 8 giây gồm nạp model.
- API/UI lưu vào thư viện và nghe mẫu thật đã được kiểm tra. Test tự động dùng FFmpeg thật, model giả cho kiểm thử vòng đời/restart/cancel/xóa tham chiếu.
- Chưa đo RAM peak, chưa đánh giá độ giống với bản thu người thật, chưa kiểm thử micro vật lý và inference clone thật trong Docker/Linux. Các mục này giữ mở trong kế hoạch nghiệm thu, không coi kiểm thử model giả là kiểm chứng chất lượng clone.
- Giới hạn 8 giây theo `_MAX_REF_SECONDS` của engine; không bật denoiser mặc định. Mẫu im lặng/quá nhỏ, clipping và mẫu quá ngắn bị từ chối.
