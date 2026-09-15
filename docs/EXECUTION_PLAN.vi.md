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
- [x] Kiểm thử Windows/Linux, Unicode, quyền chỉ đọc và file không tồn tại. CI 34874567845 đã nhập nguồn từ bind mount read-only trong container non-root.
- [x] Commit 7418f41 + tài liệu ví dụ volume mount và CLI.

### 3.3 Hàng đợi phiên bản
- [x] Snapshot bất biến của dự án cho mỗi item; chọn xử lý ngay/thêm hàng đợi; lưu bền vững.
- [x] Scheduler tuần tự, UI số phiên bản chờ/đang chạy/hoàn tất và thao tác bắt đầu.
- [x] Chỉnh sửa item: gỡ khỏi hàng đợi rồi trả snapshot về dự án gốc, kiểm tra revision tránh mất chỉnh sửa.
- [x] Xóa dự án: xác nhận hủy item chờ; xử lý job đang chạy an toàn trước khi xóa dữ liệu.
- [x] Kiểm thử race/cancel/restart/edit/delete và output theo từng snapshot (5 test queue riêng).
- [x] Commit 209cb7f cùng các bản sửa sau đó, README/CHANGELOG và xác nhận hoàn thành giai đoạn 3 ngày 15/09/2026.

## Nghiệm thu cuối

- [x] CI [34874567845](https://github.com/NgoMinhToan/vienue-dubbing/actions/runs/34874567845): 43 test qua trên mỗi OS Windows/Linux, frontend build, Docker smoke và publish đều thành công.
- [x] UI: chọn nguồn server, thư viện giọng thật 4,48 giây, từ điển VieNeu → Vi Nói, thêm/chỉnh sửa queue về dự án gốc và MKV thật đúng hai track.
- [x] Image code b230ed3 được publish dưới edge/SHA; digest ghi trong DOCKER_PUBLISH.vi.md. Gói Windows có frontend và tài liệu/CLI đầy đủ.

Ba giai đoạn đã hoàn thành theo phạm vi checklist. Các giới hạn và phạm vi để sau (domain/auth, thêm kiến trúc CPU, kiểm chứng mọi codec) được ghi riêng trong IMPLEMENTATION_STATUS.vi.md.

Thứ tự bắt buộc: Giai đoạn 1 → 2 → 3. Không push source lên repository upstream. Các thao tác publish thật chỉ thực hiện với repository/registry người dùng sở hữu hoặc chỉ định.


## Giai đoạn 4 — Phòng thu: clone và giọng tùy chỉnh (bổ sung 15/09/2026)

Mục tiêu: tạo giọng cục bộ từ mẫu thu, lưu vào thư viện và dùng trong lồng tiếng. Phòng thu từng bị loại khỏi bản đầu ở DUBBING_WEBUI_PLAN.vi.md; nay được đưa vào kế hoạch tiếp theo. Chức năng đã triển khai; xem checklist tiến độ và các kiểm chứng còn mở ở cuối tài liệu.

### 4.1 Kiểm chứng engine — 1–2 ngày
- [ ] Kiểm chứng API `encode_reference`/`add_voice` của v3 Turbo với ONNX CPU và model đang cài; đo RAM, thời gian và chất lượng từ mẫu thật.
- [ ] Xác định model bổ sung và dung lượng, nơi cache trong APP_DATA_DIR/HF_HOME; thử chạy offline sau lần tải đầu trên Windows và Linux/Docker.
- [ ] Chốt giới hạn mẫu dựa trên thử nghiệm; không cam kết clone hoạt động chỉ dựa trên API có sẵn.

### 4.2 Pipeline và lưu giọng — 2–3 ngày
- [ ] Nhập WAV/MP3 hoặc thu bằng micro trong trình duyệt; nghe, cắt đoạn và kiểm tra im lặng, clipping, thời lượng.
- [ ] FFmpeg chuẩn hóa mẫu; xử lý clone bằng worker CPU dùng chung, có tiến độ, hủy và lỗi rõ ràng.
- [ ] Lưu ID custom ổn định, metadata, mẫu nguồn và embedding/version dưới data volume; nạp lại sau restart.
- [ ] Đăng ký giọng custom vào thư viện, giọng chung và giọng từng câu; cache có phiên bản giọng để không dùng âm thanh cũ.
- [ ] Khi xóa giọng đang được dự án/queue tham chiếu, bảo vệ dữ liệu cần dùng hoặc yêu cầu chọn giọng thay thế.

### 4.3 Giao diện Phòng thu — 2–3 ngày
- [ ] Trang riêng: Nhập/thu mẫu → kiểm tra mẫu → tạo giọng → nhập tên/thẻ → nghe thử → lưu vào thư viện.
- [ ] Văn bản nghe thử áp dụng từ điển toàn cục; hiển thị trạng thái và lỗi, không yêu cầu API trả phí.
- [ ] Phân biệt rõ giọng cài sẵn và giọng tự tạo; micro dùng trên localhost (khi triển khai domain cần HTTPS).

### 4.4 Nghiệm thu — 1–2 ngày
- [ ] Test mẫu hỏng/im lặng, hủy tác vụ, restart, cache, queue snapshot và dự án dùng giọng custom.
- [ ] Thử thật CPU Windows và Docker/Linux với data volume; cập nhật README/CHANGELOG và commit theo tính năng.

Ước tính tổng: 6–10 ngày công, điều chỉnh sau bước kiểm chứng engine. Không bao gồm huấn luyện/fine-tune mô hình mới.


### Tiến độ triển khai Phòng thu
- [x] Kiểm chứng encode_reference và infer với embedding/codes trên CPU thật; khôi phục offline từ NPZ.
- [x] API nhập mẫu giới hạn dung lượng, chuẩn hóa FFmpeg, kiểm tra 3–8 giây/im lặng/clipping.
- [x] Worker tuần tự, dừng/thử lại/restart; nghe rồi lưu giọng, ID bất biến và thư viện metadata.
- [x] UI Phòng thu với upload, thu micro, mốc cắt, nghe nguồn/preview, lưu/xóa; nối chọn giọng chung và từng câu.
- [x] Bảo vệ xóa giọng được dự án/queue tham chiếu; kiểm thử tự động lưu/restart/hủy/thử lại/mẫu lỗi.
- [x] Kiểm tra UI và clone CPU thật trên Windows; nghe giọng custom qua thư viện.
- [ ] Đo RAM peak và đánh giá chất lượng với mẫu người thật; kiểm thử micro vật lý.
- [ ] Kiểm chứng inference clone thật trên Docker/Linux. CI kiểm thử lifecycle với model giả không thay cho bước này.

Chi tiết vận hành và bằng chứng: [STUDIO.vi.md](STUDIO.vi.md). Chức năng đã triển khai; nghiệm thu mở rộng còn các mục chưa đánh dấu ở trên.
