# Kế hoạch thực hiện theo ba giai đoạn

Ngày bắt đầu: 14/09/2026. Mỗi mục chỉ đánh dấu hoàn tất sau khi có code và kiểm chứng. Không coi việc viết workflow là đã publish image.

## Giai đoạn 1 — Hoàn thiện bản hiện tại

- [x] Rà soát Git, backend, editor, pipeline media và các kết quả thử trước đây.
- [x] Cache bản phối theo nội dung/revision/chế độ câu tràn; không sử dụng bản phối cũ sau khi tạo lại giọng.
- [x] Dọn cache và bản xuất cũ qua thao tác có xác nhận, bảo vệ nguồn và kết quả hiện hành.
- [x] Củng cố job recovery/cancellation, kiểm thử nguồn timestamp/VFR và giao diện 398 câu (6–11 thẻ DOM khi cuộn).
- [x] Chạy TTS workload dài: 60 câu/timeline 600 giây, mất 580,05 giây trên CPU. Không tương đương 600 giây lời đọc liên tục; chưa đo RAM peak.
- [x] Kiểm thử Windows/Linux, build lại frontend và gói Windows/Docker. CI 34869583419 qua cả hai OS và build/khởi động container non-root.
- [x] Cập nhật README/CHANGELOG, commit mốc nghiệm thu và xác nhận hoàn thành giai đoạn.

Giai đoạn 1 hoàn thành trong phạm vi checklist này. Giới hạn kiểm chứng: chưa thử mọi codec/edit list, chưa đo RAM peak phim dài; môi trường Windows sạch là venv mới trên máy hiện tại. Tiến độ tải model hiện ở mức trạng thái, chưa có phần trăm từng file. Docker Desktop local không chạy; bản build sạch được kiểm chứng trên GitHub Linux runner.

## Giai đoạn 2 — Các chức năng đã dự kiến

- [x] Người dùng xác nhận triển khai cả thư viện giọng và từ điển phát âm.
- [x] Quản lý metadata giọng, tìm/lọc/yêu thích, nghe mẫu; không đổi ID gốc. Kiểm thử API lưu/restart/revision/cache và UI tìm/lọc/form.
- [x] Luật phát âm cục bộ, nhập/xuất, xem text thực đưa vào engine, snapshot có revision; giữ văn bản hiển thị.
- [x] Kiểm thử (35 test Windows), cập nhật tài liệu và commit riêng từng tính năng; TypeScript/Vite build qua.
- [x] Xác nhận hoàn thành giai đoạn 2: thư viện giọng `23f5486`, từ điển `cfa0775`; 35 test qua, UI thử VieNeu → Vi Nói đúng, không lỗi JavaScript trong lượt thử.

## Giai đoạn 3 — CI/CD, thư mục nguồn, hàng đợi

### 3.1 Docker CI/CD
- [x] GitHub Actions build/test trên PR, build/push GHCR trên main và tag/release; dùng GITHUB_TOKEN quyền packages:write.
- [x] Tag image theo phiên bản, SHA; latest chỉ từ release ổn định; tránh publish từ PR/fork không được phép.
- [x] CI 34871803582 đã build, publish và kiểm tra digest thật tại ghcr.io/ngominhtoan/vienue-dubbing (edge/SHA).
- [x] Commit 7945055 + hướng dẫn fork/permissions/pull image. Chưa tạo tag/release ổn định nên latest chưa có.

### 3.2 Chọn video/SRT trong thư mục
- [x] APP_MEDIA_ROOT cấu hình thư mục gốc; mặc định thư mục hiện hành. Docker mount host tùy ý vào root này.
- [x] API duyệt thư mục, lọc video/SRT; chặn traversal và symlink ra ngoài root.
- [x] UI chọn nguồn từ thư mục server cùng tùy chọn upload hiện có; CLI hỗ trợ tạo dự án từ đường dẫn.
- [ ] Kiểm thử Windows/Linux, Unicode, quyền chỉ đọc và file không tồn tại.
- [x] Commit 7418f41 + tài liệu ví dụ volume mount và CLI.

### 3.3 Hàng đợi phiên bản
- [x] Snapshot bất biến của dự án cho mỗi item; chọn xử lý ngay/thêm hàng đợi; lưu bền vững.
- [x] Scheduler tuần tự, UI số phiên bản chờ/đang chạy/hoàn tất và thao tác bắt đầu.
- [x] Chỉnh sửa item: gỡ khỏi hàng đợi rồi trả snapshot về dự án gốc, kiểm tra revision tránh mất chỉnh sửa.
- [x] Xóa dự án: xác nhận hủy item chờ; xử lý job đang chạy an toàn trước khi xóa dữ liệu.
- [x] Kiểm thử race/cancel/restart/edit/delete và output theo từng snapshot (5 test queue riêng).
- [ ] Commit + README/CHANGELOG và xác nhận hoàn thành giai đoạn.

Thứ tự bắt buộc: Giai đoạn 1 → 2 → 3. Không push source lên repository upstream. Các thao tác publish thật chỉ thực hiện với repository/registry người dùng sở hữu hoặc chỉ định.
