# Docker CI/CD

Workflow `.github/workflows/dubbing.yml` kiểm thử Windows/Linux, build container và kiểm tra HTTP/non-root trước khi publish.

| Trigger | Kết quả |
|---|---|
| PR | Kiểm thử/build, không đăng nhập registry, không push |
| Push main thay code hoặc workflow | Push tag `edge` và `sha-<full commit>` |
| Push tag v1.2.3 | Push `1.2.3` và SHA |
| Release published ổn định | Push phiên bản và `latest` |
| Prerelease | Có tag phiên bản, không đổi `latest` |
| workflow_dispatch trên main | Kiểm thử và publish edge/SHA |

Registry: `ghcr.io/ngominhtoan/vienue-dubbing`, nền tảng `linux/amd64`. Workflow dùng `GITHUB_TOKEN` với `packages:write`, không cần lưu PAT trong source. Repo riêng tư; package mới mặc định riêng tư, tài khoản pull phải được cấp quyền đọc package. Khi fork, sửa tên image và điều kiện repository ở job publish theo repo của bạn.

```sh
docker pull ghcr.io/ngominhtoan/vienue-dubbing:edge
docker run --rm -p 127.0.0.1:7861:7861 -v dubbing-data:/data ghcr.io/ngominhtoan/vienue-dubbing:edge
```

Dùng tag SHA hoặc digest để cố định bản triển khai. `edge` theo main; không đại diện bản ổn định. Model tải lần đầu và được giữ trong volume dữ liệu. Khi chưa có release ổn định, `latest` chưa tồn tại.

Tham khảo: [GitHub publish container](https://docs.github.com/en/actions/tutorials/publish-packages/publish-docker-images), [Docker metadata action](https://github.com/docker/metadata-action), [Docker build/push action](https://github.com/docker/build-push-action).
