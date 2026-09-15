# Thay đổi lịch sử Git

Mốc phát triển riêng đầu tiên trong lịch sử cũ: `89a79bd` (WebUI CPU, MP3, MKV hai track).

Phương án: tạo lại chuỗi commit với commit này là root không có parent; giữ tree, tác giả, thời gian và thông điệp của từng commit phát triển riêng. Mỗi commit sau trỏ tới parent mới. Do parent đổi, SHA của các commit đổi. Không squash toàn bộ quá trình phát triển thành một commit.

Các bước thực hiện:
1. Kiểm tra chỉ có branch `main` trên origin, không có remote tag hoặc merge riêng cần xử lý.
2. Lưu `artifacts/history-before-cleanup.bundle` và branch backup cục bộ, không push backup.
3. Dùng Git commit objects tạo root mới từ tree của commit đầu, rồi tái tạo các commit sau theo thứ tự.
4. So sánh tree của HEAD trước/sau: phải giống hoàn toàn, working tree phải sạch.
5. Cập nhật `main` và push `--force-with-lease` kèm SHA remote đã kiểm tra.
6. Kiểm tra root và số commit trên GitHub; không push tag upstream bằng `--tags`/`--mirror`.

Backup giữ trong máy để phục hồi khi cần. Lịch sử upstream không còn là tổ tiên của `main` trên GitHub; GitHub có thể còn lưu các đối tượng/URL SHA cũ trong cache hoặc dữ liệu Actions. Đây không phải quy trình xóa dữ liệu bí mật khỏi hệ thống GitHub.

Máy khác đã clone lịch sử cũ nên sao lưu các chỉnh sửa chưa commit và clone lại repository mới. Không pull/rebase lịch sử cũ vào main mới.
