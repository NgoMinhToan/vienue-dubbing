# Hàng đợi phiên bản

Trong editor chọn **Xử lý ngay** hoặc **Thêm vào hàng đợi** trước khi tạo toàn bộ giọng/xuất MP3/MKV. Mỗi lần tạo lưu một snapshot bất biến của lời, giọng, tốc độ, mốc, nguồn video, bản từ điển và chính sách câu tràn.

- **Xử lý ngay:** đưa vào worker dùng chung; nếu worker bận, chờ tuần tự.
- **Thêm vào hàng đợi:** lưu ở trạng thái chờ, chưa chạy. Trong mục Lồng tiếng bấm **Bắt đầu** từng item hoặc **Bắt đầu hàng đợi**.
- Thẻ dự án hiển thị số chờ, số hoàn tất/tổng phiên bản và số phiên bản đang xử lý/hoàn tất gần nhất. Số phiên bản tăng dần và không tái sử dụng sau khi gỡ item.
- **Chỉnh sửa:** áp dụng cho item chưa chạy (chờ bắt đầu/chờ worker). Xác nhận để gỡ item, khôi phục snapshot về dự án gốc và mở editor. Nội dung hiện tại bị thay bằng snapshot; revision kiểm tra lại khi lưu để tránh ghi đè một thay đổi xảy ra đồng thời.
- **Dừng/Thử lại:** giữ WAV đã tạo. Mỗi lượt dispatch có mã nội bộ riêng để callback đã hủy không chạy nhầm lượt thử lại.
- **Xóa dự án:** xác nhận hủy toàn bộ hàng đợi. Nếu đang inference, đợi câu hiện tại trả về để worker dọn tài nguyên rồi mới xóa dữ liệu; UI tự tiếp tục thao tác xóa. Không xóa thư mục khi worker còn dùng.
- **Restart:** phiên bản đang chờ vẫn chờ; phiên bản chạy/đợi worker lúc tắt được trả về chờ để người dùng bắt đầu lại. Không tự chạy tác vụ khi server vừa bật.
- Kết quả phiên bản hoàn tất có link tải riêng trong hàng đợi, kể cả khi dự án đã thay đổi. Dọn cache giữ snapshot và kết quả phiên bản; xóa dự án sẽ xóa tất cả.

Lưu trữ nằm trong `APP_DATA_DIR`: SQLite giữ bộ đếm phiên bản; `renders/<job>/snapshot.json` và `job.json` ghi nguyên tử. Nguồn đã nhập được sao chép vào data; thay nguồn giữ file trước đó cho snapshot cũ. Một instance server/worker trên mỗi data volume; không chạy nhiều replica chung SQLite.

API: POST `/api/projects/{id}/versions` với `revision`, `kind`, `mode` (`now`/`wait`), `overflow_policy` (`keep`/`skip`). GET `/api/queue`; POST `/api/queue/start`, `/api/queue/{id}/start`, `/api/queue/{id}/edit` (revision hiện tại của dự án).
