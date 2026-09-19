# Docker CI/CD

Nghiệm thu 15/09/2026: [CI 34874567845](https://github.com/NgoMinhToan/vienue-dubbing/actions/runs/34874567845) đã publish code `b230ed3` và kiểm tra digest:

```text
ghcr.io/ngominhtoan/vienue-dubbing@sha256:6e6ffb621f4b902dd1ed3e776ebfc775862a319518a12329269b9f9129b3c61b
```

Workflow `.github/workflows/dubbing.yml` kiểm thử Windows/Linux, build container và kiểm tra HTTP/non-root trước khi publish.

| Trigger | Kết quả |
|---|---|
| PR | Kiểm thử/build, không đăng nhập registry, không push |
| Push main thay code hoặc workflow | Push tag `latest`, `edge` và `sha-<full commit>` |
| Push tag v1.2.3 | Push `1.2.3` và SHA |
| Release published ổn định | Push phiên bản và `latest` |
| Prerelease | Có tag phiên bản, không đổi `latest` |
| workflow_dispatch trên main | Kiểm thử và publish latest/edge/SHA |

Registry: `ghcr.io/ngominhtoan/vienue-dubbing`, nền tảng `linux/amd64` và `linux/arm64`. Docker tự chọn kiến trúc phù hợp khi pull các tag mới. Workflow chạy smoke test trên runner AMD64 và ARM64, build bằng Buildx/QEMU rồi kiểm tra manifest có đủ hai kiến trúc sau khi push. Workflow dùng `GITHUB_TOKEN` với `packages:write`, không cần lưu PAT trong source. Repo và package đã public; người dùng có thể pull không cần đăng nhập. Khi fork, sửa tên image và điều kiện repository ở job publish theo repo của bạn.

```sh
docker pull ghcr.io/ngominhtoan/vienue-dubbing:edge
docker run --rm -p 127.0.0.1:7861:7861 -v dubbing-data:/data ghcr.io/ngominhtoan/vienue-dubbing:edge
```

Dùng tag SHA hoặc digest để cố định bản triển khai. `edge` theo main; không đại diện bản ổn định. Model tải lần đầu và được giữ trong volume dữ liệu. `latest` và `edge` cùng theo build main mới nhất đã vượt kiểm thử.

## Chọn nguồn từ thư mục host

Trong modal tạo dự án, chọn **Chọn trong thư mục server**, duyệt và chọn một video cùng một SRT. Mặc định root là thư mục làm việc của server. Đặt `APP_MEDIA_ROOT` để đổi; chỉ file/thư mục nằm dưới root này được duyệt, symlink ra ngoài bị chặn.

Ví dụ mount bất kỳ thư mục host vào `/media` (thay đường dẫn nguồn bên trái):

```sh
docker run --rm -p 127.0.0.1:7861:7861 -v dubbing-data:/data --mount type=bind,source=/home/user/videos,target=/media,readonly -e APP_MEDIA_ROOT=/media ghcr.io/ngominhtoan/vienue-dubbing:edge
```

Trên PowerShell dùng `--mount "type=bind,source=D:\Videos,target=/media,readonly"`. Mount nguồn chỉ cần quyền đọc; `/data` cần quyền ghi cho UID 1000. File được sao chép vào data khi tạo dự án, nên cần dự phòng dung lượng. Chỉ hỗ trợ một root mỗi instance, nhưng có thể mount nhiều thư mục host làm các thư mục con bên dưới root đó.

CLI dùng cùng API (đường dẫn tương đối theo root server, không phải đường dẫn máy chạy CLI):

```sh
python scripts/media_cli.py list
python scripts/media_cli.py list "phim" --offset 0
python scripts/media_cli.py import "phim/video.mp4" "phim/video.srt" --name "Dự án mới"
```

Tham khảo: [GitHub publish container](https://docs.github.com/en/actions/tutorials/publish-packages/publish-docker-images), [Docker metadata action](https://github.com/docker/metadata-action), [Docker build/push action](https://github.com/docker/build-push-action).


## Cập nhật public/latest
Repository và package GHCR đã public. Workflow main gắn latest sau test/build; dùng README.md và compose.yaml ở root làm hướng dẫn hiện hành. Không cần PAT để pull package public.
