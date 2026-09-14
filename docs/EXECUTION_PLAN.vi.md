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
- [ ] Nếu có: luật phát âm cục bộ, nhập/xuất, xem text thực đưa vào engine, cache có phiên bản; giữ văn bản hiển thị.
- [ ] Kiểm thử, cập nhật tài liệu và commit riêng từng tính năng.
- [ ] Xác nhận hoàn thành giai đoạn trước khi sang giai đoạn 3.

## Giai đoạn 3 — CI/CD, thư mục nguồn, hàng đợi

### 3.1 Docker CI/CD
- [ ] GitHub Actions build/test trên PR, build/push GHCR trên nhánh phát hành và tag/release; dùng GITHUB_TOKEN quyền packages:write.
- [ ] Tag image theo phiên bản, SHA; latest chỉ từ bản phát hành phù hợp; tránh publish từ PR/fork không được phép.
- [ ] Kiểm tra workflow và build image; ghi rõ registry/repository được chọn và việc publish thực tế.
- [ ] Commit + hướng dẫn fork/permissions/pull image.

### 3.2 Chọn video/SRT trong thư mục
- [ ] APP_MEDIA_ROOT cấu hình thư mục gốc; mặc định thư mục hiện hành. Docker mount host tùy ý vào root này.
- [ ] API duyệt thư mục, lọc video/SRT; chặn traversal và symlink ra ngoài root.
- [ ] UI chọn nguồn từ thư mục server cùng tùy chọn upload hiện có; CLI hỗ trợ tạo dự án từ đường dẫn.
- [ ] Kiểm thử Windows/Linux, Unicode, quyền chỉ đọc và file không tồn tại.
- [ ] Commit + tài liệu ví dụ volume mount.

### 3.3 Hàng đợi phiên bản
- [ ] Snapshot bất biến của dự án cho mỗi item; chọn xử lý ngay/thêm hàng đợi; lưu bền vững.
- [ ] Scheduler tuần tự, UI số phiên bản chờ/đang chạy/hoàn tất và thao tác bắt đầu.
- [ ] Chỉnh sửa item: gỡ khỏi hàng đợi rồi trả snapshot về dự án gốc, kiểm tra revision tránh mất chỉnh sửa.
- [ ] Xóa dự án: xác nhận hủy item chờ; xử lý job đang chạy an toàn trước khi xóa dữ liệu.
- [ ] Kiểm thử race/cancel/restart/edit/delete và output theo từng snapshot.
- [ ] Commit + README/CHANGELOG và xác nhận hoàn thành giai đoạn.

Thứ tự bắt buộc: Giai đoạn 1 → 2 → 3. Không push source lên repository upstream. Các thao tác publish thật chỉ thực hiện với repository/registry người dùng sở hữu hoặc chỉ định.
