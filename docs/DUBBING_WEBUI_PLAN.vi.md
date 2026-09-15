# Kế hoạch VieNeu Dubbing WebUI cục bộ

Ngày khảo sát: 13/09/2026. Bản sửa 3: đối chiếu 9 ảnh desktop, các câu trả lời đã chốt, xuất MKV hai audio tracks và hướng Docker. Các phase bên dưới là kế hoạch đầy đủ; trạng thái bản triển khai hiện tại được ghi riêng trong [README-DUBBING.vi.md](../README-DUBBING.vi.md). Không xem thời gian ước tính hoặc thông số đề xuất là kết quả benchmark.

## 1. Mã nguồn và kết quả tìm lại giao diện desktop

- Đã clone vào `D:\Project\vieneu-dubbling`, nhánh `main`, commit `3206ed960e317e69bfe09f9d553aecbf1090f32e`.
- Tag `app-v0.14.0` trỏ cùng commit. Remote hiện trả về một nhánh `main`.
- API release trả một asset đính kèm: `VieNeu_0.14.0_x64-setup.exe`, 55.904.281 byte. Source ZIP và tarball là archive của repository tại tag do GitHub tự tạo.
- Đã tải và kiểm tra danh sách source ZIP: 156 mục tính cả thư mục; không có dự án Tauri, Cargo.toml, package.json hoặc frontend desktop.
- Lịch sử Git có `web_ui/` tại commit `94bd88b`: React, Vite, TypeScript, giao diện nhập văn bản, chọn giọng và phát streaming. Không phải trình lồng tiếng video/SRT.
- Repository công khai `pnnbao97/VieNeu-App` có frontend Next.js, đăng nhập và Prisma; trang TTS mới hiển thị tiêu đề và lời chào, không có trình lồng tiếng desktop.
- Đã kiểm tra thêm các repo VieNeu công khai của người phát hành EmberDuong: `VieNeu-App-1`, `VieNeu-TTS`, `VieNeu-TTS-1`; lần lượt là khung web, landing page và bản mã TTS tương tự.
- Kết luận giới hạn: VieNeu-TTS có mã công khai và LICENSE Apache-2.0. Chưa tìm thấy source desktop v0.14.0 trong các nguồn trên; không suy ra toàn bộ sản phẩm không open source. Thông báo v4 không open source nói về v4, không xác nhận nơi công bố source desktop.
- Đã đối chiếu 9 ảnh desktop của người dùng; chưa cài/chạy EXE. Ảnh đủ để đặc tả bố cục, nhưng không xác minh thuật toán âm thanh, toàn bộ menu tốc độ hoặc hệ số giảm âm.

Nguồn:

- [Release v0.14.0](https://github.com/pnnbao97/VieNeu-TTS/releases/tag/app-v0.14.0)
- [Release API](https://api.github.com/repos/pnnbao97/VieNeu-TTS/releases/tags/app-v0.14.0)
- [Source tại tag](https://github.com/pnnbao97/VieNeu-TTS/tree/app-v0.14.0)
- [GitHub giải thích source archives trong release](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases)
- [VieNeu-App](https://github.com/pnnbao97/VieNeu-App)
- [React demo cũ](https://github.com/pnnbao97/VieNeu-TTS/tree/94bd88b/web_ui)

## 2. Phân tích dự án hiện tại

| Thành phần | Hiện trạng | Hướng sử dụng |
|---|---|---|
| `apps/gradio_main.py`, `ui_constants.py`, `ui_utils.py` | Gradio, đọc truyện/văn bản, hội thoại, voice cloning, SRT, nhiều lựa chọn model/device | Tham khảo luồng TTS; thay màn hình bằng WebUI chuyên lồng tiếng |
| `apps/srt_speech.py` | Parser SRT, sinh từng câu CPU, xếp timeline, WAV/MP3 | Tái sử dụng logic phù hợp; thay thuật toán đẩy lùi câu |
| `apps/user_voices.py` | Lưu/nạp giọng người dùng | Có thể dùng kho giọng hiện có; không bắt nhập thêm file giọng |
| `apps/web_stream.py`, `client/client.html` | Demo FastAPI streaming | Tham khảo API; không dùng nguyên trạng vì tải model ngay khi import và chưa có quản lý dự án/job |
| `src/vieneu/v3turbo.py`, `_v3_turbo_engine/` | Engine v3 Turbo, CPU ONNX, GPU PyTorch, preset và clone giọng, 48 kHz | Giữ lõi CPU ONNX |
| `src/vieneu/factory.py`, các backend khác | v3 Nano, standard, fast, turbo, remote, XPU | Không đưa lựa chọn ngoài v3 Turbo vào WebUI mới |
| `src/vieneu_utils/` | Chuẩn hóa văn bản, phiên âm, chia câu, ghép âm thanh | Giữ phần engine cần |
| `src/vieneu/assets/` | Preset giọng, dữ liệu mẫu | Tái sử dụng preset v3 Turbo |
| `finetune/` | LoRA, chuẩn bị dữ liệu, merge, đóng gói giọng | Ngoài bản cài lồng tiếng |
| `examples/`, `docs/`, `docker/` | Ví dụ, tài liệu, cấu hình CPU/GPU/server | Giữ mẫu kiểm tra; viết tài liệu cài Windows riêng |
| `tests/`, `.github/workflows/` | Kiểm thử engine/utils và CI Python; phát hành PyPI | Bổ sung kiểm thử timeline/mix và Windows; không tái sử dụng quy trình publish upstream cho bản riêng |
| `pyproject.toml`, `uv.lock`, `config.yaml` | Package 3.6.4; Python, uv, dependencies và danh sách model | Tách dependencies sản phẩm; pin môi trường đã kiểm chứng |

Công nghệ: Python (repo chọn 3.12), Gradio, ONNX Runtime, NumPy, SoundFile, soxr, sea-g2p, tokenizers, Hugging Face Hub; GPU/legacy dùng thêm PyTorch, Transformers, LMDeploy hoặc llama.cpp. CPU tối thiểu không cần CUDA.

Các điểm phải sửa:

- `lay_on_timeline()` dùng `max(start, cursor)` nên câu dài làm lệch câu sau; chưa áp dụng khung kết thúc SRT để khớp video.
- Parser hiện dễ bỏ qua block lỗi và sửa thời lượng không hợp lệ; bản editor cần báo lỗi theo dòng, không âm thầm mất câu.
- MP3 hiện phụ thuộc khả năng libsndfile rồi fallback WAV; bản mới cần encode MP3 bằng FFmpeg và báo lỗi đúng định dạng.
- Chưa có đầu vào video, trộn âm gốc, giảm âm khi lời lồng tiếng phát, hoặc editor tốc độ từng câu.
- Chưa thấy pipeline desktop sách nói/dịch/STT/dựng video để xóa khỏi mã này. Bản mới chỉ lắp các thành phần lồng tiếng cần thiết.

## 3. Phạm vi đã chốt

- Chạy cục bộ trên Windows, mở trình duyệt; mặc định server bind `127.0.0.1`. Lõi xử lý phải chạy được trên Linux để đóng gói Docker sau này (mục 7). Domain và nhiều người dùng nằm ngoài phạm vi hiện tại.
- Đầu vào bắt buộc: video và SRT đã có lời cần đọc. Không nhận diện lời thoại, dịch, hoặc trợ lý AI.
- Model v3 Turbo, CPU ONNX; mặc định fp32. Tải tài nguyên trong thiết lập đầu, sau đó kiểm tra hoạt động offline.
- Giữ chọn giọng, sửa từng câu, chỉnh tốc độ từng câu, nghe thử và tạo lại câu.
- Giữ mốc SRT, tăng tốc có giới hạn, đánh dấu câu không vừa khung.
- Hai lựa chọn tải về: âm thanh MP3 (mặc định) và video MKV chứa đúng hai audio track: âm gốc và bản lồng tiếng. Quy trình MKV dùng mkvmerge, chi tiết mục 6.
- Giữ đủ bốn chế độ âm gốc dưới đây. Đề xuất mặc định chế độ đầu tiên.

### 3.1. Đối chiếu từng ảnh và quyết định phạm vi

Ảnh được dùng làm bằng chứng về giao diện đang hiển thị, không biến mô tả/quảng cáo trong ảnh thành yêu cầu mới.

| Ảnh | Điều quan sát được | Áp dụng cho bản riêng |
|---|---|---|
| 1 | Editor hai cột, video trái, danh sách thẻ câu phải, timeline dưới, giọng chung và tốc độ từng câu, tự khớp tối đa 1,6x | Giữ bố cục và tương tác lồng tiếng; bỏ nhận diện, dịch, nội dung gốc/bản dịch kép |
| 2 | Danh sách dự án dạng thẻ, số câu/đã tạo, tên video, nút tạo dự án | Giữ danh sách dự án và tiến độ; bỏ Về Phòng thu và Chỉ làm phụ đề |
| 3 | Phòng thu đọc văn bản, podcast, clone và thẻ cảm xúc | Không đưa Phòng thu/Podcast/Clone thành chức năng trong bản đầu; ảnh này chỉ tham chiếu phong cách UI, không dùng dải tốc độ 0,5–3x làm bằng chứng cho editor lồng tiếng |
| 4 | Kho 23 giọng, tìm/lọc, yêu thích, quảng cáo kho 500 giọng và đồng bộ máy chủ | Giữ chọn/nghe preset cục bộ; không có kho trả phí hoặc đồng bộ máy chủ. Màn hình quản lý đầy đủ để giai đoạn sau |
| 5 | Sửa tên, mô tả, thẻ và câu nghe thử của giọng | Là metadata, không phải huấn luyện hay đổi chất giọng. Để giai đoạn sau |
| 6 | Từ điển thay cách đọc, thử câu, khớp cả từ/hoa thường, nhập luật từ file | Để giai đoạn sau theo xác nhận của người dùng |
| 7 | v3 Turbo fp32, CPU/GPU, GPU batch và cài bộ tăng tốc | Giữ trạng thái v3 Turbo fp32/CPU; bỏ Nano/GPU/batch GPU và tải bộ tăng tốc trong bản cơ sở |
| 8 | Cài STT, số luồng CPU, trợ lý AI/API, cập nhật desktop | Bỏ STT/AI/cập nhật desktop. CPU tự động theo engine đã benchmark; không sao chép con số “Tự động (2)” thành cấu hình bắt buộc |
| 9 | Menu tải có chế độ nền, MP3/SRT/video và cảnh báo 251 câu lùi lại tối đa 101,9 giây | Giữ preset nền, MP3 và bổ sung MKV hai audio track theo yêu cầu mới. Cảnh báo cho thấy không nên sao chép hành vi xuất làm lệch câu |

Không giữ tài khoản/đăng nhập, quảng cáo nâng cấp, thống kê, phòng thu, sách nói, dựng video, tạo hàng loạt độc lập hoặc thư viện Giọng đã tạo độc lập. Audio từng câu và bản xuất vẫn lưu trong dự án lồng tiếng. Nút “Tạo giọng tất cả” trong một dự án được giữ.

### 3.2. Đặc tả giao diện đã rút ra từ ảnh

- Sidebar tối hẹp, nền gần đen, panel xám đậm, nút/viền chọn màu tím và trạng thái thành công màu xanh. Dùng tên/logo riêng; không đưa logo watermark desktop vào preview.
- Điều hướng cơ sở: Lồng tiếng và Cài đặt; chân sidebar có CPU · v3 Turbo và trạng thái sẵn sàng/đang tải/lỗi. Thư viện giọng và từ điển chỉ thêm nếu được chọn.
- Danh sách dự án: tạo mới, mở lại, đổi tên, xóa có xác nhận; thẻ có tên, video, số câu hợp lệ, đã tạo và thời điểm sửa.
- Tạo mới: chọn video và SRT, kiểm tra xong mới mở editor; không buộc tải giọng mẫu hoặc nhập API key.
- Editor: thanh trên có quay về dự án, tên dự án, hoàn tác/làm lại cho chỉnh sửa nội dung, “Tạo giọng tất cả (N câu)” và “Tải về”. N là số câu thiếu/lỗi/thay đổi cần tạo, không tính tất cả câu đã hợp lệ.
- Cột trái khoảng 40%, cột phải khoảng 60% vùng nội dung trên desktop; tỷ lệ là đề xuất từ ảnh. Cột có cuộn riêng, thanh công cụ và timeline luôn truy cập được. Ở cửa sổ nhỏ chuyển bố cục để không che nút thao tác.
- Cột trái: video; “Xem trước bản lồng tiếng”; nhập/thay video và SRT; giọng chung; tốc độ chung; tự khớp và mức tăng tối đa. Thay SRT phải cảnh báo sẽ thay nội dung và cache câu của dự án.
- Cột phải: thẻ câu gồm số thứ tự, start/end, nội dung duy nhất sửa được, giọng kế thừa hoặc riêng, tốc độ kế thừa hoặc riêng, nghe thử, tạo lại, trạng thái và độ vượt. Giữ thêm/xóa câu thủ công và sửa thời gian trong form; không kéo mép clip để sửa mốc trong bản đầu.
- Giọng/tốc độ kế thừa phải biểu diễn bằng giá trị null hoặc cờ kế thừa: thay giọng chung chỉ làm mất hiệu lực câu đang kế thừa, không ghi đè lựa chọn riêng.
- Timeline nằm dưới hai cột: đoạn theo SRT, playhead, zoom, cuộn ngang, bấm để tua/chọn câu. Không có kéo-thả cắt ghép nhiều track hoặc waveform chi tiết; xuất MKV chỉ remux theo mục 6.
- Trạng thái tách biệt: “đã tạo” không đồng nghĩa “vừa khung”; có Chưa tạo / Đang tạo / Đã tạo / Cần tạo lại / Lỗi và Vừa khung / Dùng khoảng nghỉ / Tràn khung.
- Menu Tải về có bốn preset nền, “Chỉ âm thanh · MP3” và “Video · MKV (2 track âm thanh)”; bỏ SRT, MP3+SRT, video đốt phụ đề và checkbox kèm phụ đề. Chức năng Dựng video độc lập vẫn bị loại bỏ.
- Preview bản lồng dùng cùng bản phối PCM và cùng tham số timing/mix với export. Tắt audio của video gốc khi phát bản phối để không nghe nền hai lần; đồng bộ play/pause/seek và kiểm tra drift. Có thể hiện nội dung SRT đang chọn trên preview, không có chọn ngôn ngữ/bản dịch.

### 3.3. Giọng mẫu và cài đặt: khả thi nhưng không sao chép giả định

File `src/vieneu/assets/voices_v3_turbo.json` hiện có **23 preset**, gồm Kim Thanh, Adam, Minh Đức, Minh Quân, Anh Khôi… Có cơ sở tái sử dụng kho giọng cục bộ. Một số tên hiển thị desktop có hậu tố khác (ví dụ Minh Quân 1); không suy ra dữ liệu giọng giống hệt chỉ dựa vào tên/số lượng. Khi triển khai cần nghe thử và đối chiếu.

Màn hình cài đặt cơ sở chỉ hiển thị model/backend, trạng thái tài nguyên, vị trí dữ liệu và lỗi thiết lập. Chưa cần lựa chọn luồng CPU; engine có tham số threads nhưng giá trị tốt nhất cần đo trên máy thực. Không dùng số liệu tốc độ/VRAM quảng cáo trong ảnh làm cam kết hiệu năng.

### 3.4. Ba lựa chọn người dùng đã xác nhận

1. Chọn/nghe giọng ngay trong Lồng tiếng; thư viện giọng riêng và từ điển phát âm làm sau.
2. Cho câu dùng khoảng nghỉ sau end SRT tới start câu kế tiếp; chỉ tự tăng tốc khi cần để tránh lấn câu sau. Giữ nguyên start và metadata SRT.
3. Nếu vẫn quá dài sau khi tăng tốc tới giới hạn: **cho xuất sau cảnh báo, giữ start và chấp nhận lời chồng nhau**. Đây là ngoại lệ được người dùng cho phép đối với mục tiêu không lấn câu tiếp theo. Không tự kéo lùi các câu sau.

Không còn câu hỏi bắt buộc về phạm vi. Các giá trị tốc độ/âm lượng cụ thể chưa thể suy ra đầy đủ từ ảnh; dùng đề xuất công khai trong phase 1 và điều chỉnh qua nghe thử. Cảnh báo xuất phải liệt kê số câu tràn, vị trí và độ chồng; người dùng có thể quay lại sửa hoặc tiếp tục xuất. Không cảnh báo xác nhận lặp lại nếu cùng project revision và lựa chọn đã được chấp nhận.

| Nhãn giao diện | Hành vi |
|---|---|
| Nhỏ lại, hạ thêm khi lồng tiếng nói | Hạ nền toàn thời gian, hạ thêm trong đoạn có tiếng lồng |
| Giữ nguyên, chỉ hạ khi lồng tiếng nói | Nền giữ nguyên ngoài đoạn lồng, hạ khi tiếng lồng phát |
| Rất nhỏ | Nền ở mức rất thấp cố định |
| Tắt âm gốc | Chỉ giọng lồng tiếng, giữ đủ chiều dài video |

Giảm âm gốc tác động cả nhạc và giọng nói đã trộn trong video; đây không phải tách giọng gốc khỏi nhạc.

## 4. Kiến trúc đề xuất

React + TypeScript + Vite cho editor; FastAPI + Uvicorn phục vụ API và frontend build sẵn; engine Python hiện có chạy trong worker CPU duy nhất. SQLite lưu dự án/câu/job; audio và video nằm trong thư mục dự án trên đĩa. FFmpeg/ffprobe xử lý media.

Frontend build sẵn giúp người dùng cuối không cần Node.js. Không cần Redis hoặc dịch vụ đám mây. Khai báo FastAPI/Uvicorn là dependency trực tiếp, không dựa vào dependency bắc cầu của Gradio.

```text
frontend/                  # Màn hình lồng tiếng
apps/dubbing_web/          # API, quản lý dự án, job, launcher
src/vieneu_dubbing/        # SRT, TTS adapter, timing, mix, export
data/projects/<id>/        # Media, câu WAV, bản phối và metadata
tests/dubbing/             # Kiểm thử nghiệp vụ mới
scripts/                   # Setup/Start Windows
```

Audio trung gian dùng PCM/WAV 48 kHz; chỉ mã hóa MP3 một lần ở cuối. Các file dài xử lý theo khối và trên đĩa để tránh giữ toàn bộ video/audio trong RAM.

Tham khảo chính thức: [FastAPI static files](https://fastapi.tiangolo.com/tutorial/static-files/), [Vite build/deploy](https://vite.dev/guide/static-deploy.html), [FFmpeg filters](https://ffmpeg.org/ffmpeg-filters.html).

## Phase 1 — Chốt giao diện và dữ liệu mẫu

**Mục tiêu:** Đặc tả đủ rõ để xây đúng giao diện và hành vi desktop mong muốn.

- Đối chiếu ảnh hoặc bản desktop v0.14.0 thực tế: bố cục lồng tiếng, bảng câu, điều khiển tốc độ, hộp xuất âm thanh.
- Đã hoàn thành đối chiếu bố cục từ 9 ảnh và xác nhận mục 3.4; phần còn lại là đặc tả trạng thái và chọn thông số thủ công/tự khớp để nghe thử. Không cần tìm lại ảnh cho các màn hình đã rõ.
- Ghi lại nhãn, trạng thái tải/chạy/lỗi; chỉ giữ Lồng tiếng và cài đặt tối thiểu.
- Xác định giới hạn tốc độ, mức giảm âm nền và thời gian chuyển âm. Nếu chưa đo được app gốc, đánh dấu thông số mới là đề xuất, không coi là thông số upstream.
- Chuẩn bị bộ video/SRT gồm câu ngắn, câu dài, khoảng lặng, phụ đề lỗi và video không có audio.

**Công cụ:** Desktop/ảnh tham chiếu, Markdown, ffprobe.

**Bàn giao:** Đặc tả màn hình và bộ mẫu nghiệm thu. **Ước tính:** 0,5–1 ngày.

## Phase 2 — Tách ứng dụng và cố định CPU v3 Turbo

**Mục tiêu:** Có backend tối thiểu chạy độc lập, không cần khóa API.

- Tạo package lồng tiếng và entry point mới; giữ SDK upstream để giảm rủi ro sửa engine.
- Cố định khởi tạo `Vieneu(mode="v3turbo", device="cpu", backend="onnx", precision="fp32")`.
- Nạp model một lần trong worker; hiển thị trạng thái tải/thiếu model/lỗi. Không chạy inference ngay khi import module API.
- Tách dependencies WebUI mới, loại Gradio và GPU extras khỏi bản cài sản phẩm nếu không còn dependency thực tế.
- Đóng gói frontend, font, icon cục bộ; xác định đầy đủ model/tokenizer/codec cần cache để chạy offline.
- Tạo API dự án, danh sách giọng, tiến độ và tải kết quả; ghi SQLite và file theo ID.
- Dữ liệu câu dùng ID ổn định, original_text, edited_text, start/end, voice_override, speed_override, WAV gốc, phiên bản render và trạng thái. Job giữ snapshot phiên bản dự án; kết quả từ job cũ không được ghi đè chỉnh sửa mới.

**Công cụ:** Python 3.12, uv, FastAPI, ONNX Runtime, SQLite.

**Bàn giao:** API sinh một câu bằng CPU và lưu dự án. **Ước tính:** 2–3 ngày.

## Phase 3 — Nhập video/SRT và editor từng câu

**Mục tiêu:** Nhập hai file và chỉnh lời/tốc độ bằng giao diện tương tự desktop.

- Upload video/SRT; dùng ffprobe xác thực thời lượng, stream âm thanh và codec; kiểm tra kích thước file, đường dẫn và dung lượng đĩa.
- Parser báo dòng lỗi, encoding lỗi, mốc âm/đảo, cue chồng lấn hoặc vượt chiều dài video. Không dịch hay đoán lại lời thoại.
- Bảng câu có thời gian, nội dung, giọng, tốc độ, thời lượng audio, trạng thái và nút nghe/tạo lại.
- Xây thẻ câu, sidebar, danh sách dự án và timeline theo mục 3.2; chỉ render phần danh sách đang nhìn thấy để dự án 522 câu như ảnh vẫn cuộn mượt. Hoàn tác/làm lại lưu các thao tác sửa dữ liệu, không nhân bản file media.
- Preview video bằng trình duyệt; với codec không hỗ trợ, tạo proxy preview cục bộ khi cần. Proxy không phải đầu ra video cho tải về.
- Tự lưu chỉnh sửa. Câu có text/voice thay đổi phải mang trạng thái cần tạo lại; đổi tốc độ chỉ xử lý lại WAV gốc.

**Công cụ:** React, TypeScript, Vite, HTML media, FastAPI, ffprobe.

**Bàn giao:** Editor dùng được với SRT thực và timeline điều hướng. **Ước tính:** 4–6 ngày.

## Phase 4 — Tổng hợp và giữ mốc thời gian

**Mục tiêu:** Mỗi câu bắt đầu đúng mốc; câu dài không kéo lùi các câu sau.

- Worker CPU xử lý từng câu; cập nhật tiến độ, cho dừng giữa các câu và làm tiếp câu chưa hoàn thành.
- Cache WAV gốc theo nội dung, giọng, phiên bản model và tham số sinh; tốc độ được áp dụng từ WAV gốc để tránh giảm chất lượng qua nhiều lần xử lý.
- Tách tốc độ thủ công `s` (theo câu hoặc kế thừa chung) khỏi hệ số tự khớp `a`. Ảnh đồng thời hiện 1,7x và tối đa 1,6x, nên không thể diễn giải 1,6x là trần tốc độ tuyệt đối. Đề xuất `a_max = 1,6` là giới hạn tăng thêm; cần chốt ở phase 1, chưa xác minh là công thức desktop.
- Với WAV dài `D`, tốc độ thủ công `s`, cửa sổ cho phép `W`: `a_required = max(1, D/(s*W))`. Nếu `a_required <= a_max`, tốc độ thực `s*a_required`; nếu vượt, dùng tối đa `s*a_max` cho preview và báo phần vượt. Đề xuất dải thủ công 0,5–3x và bảo vệ tích tốc độ tối đa 3x; không gán dải này cho desktop lồng tiếng từ ảnh Phòng thu.
- `W` dùng khoảng nghỉ lấy `start_(i+1)-start_i`, câu cuối tới hết video. Nếu hai câu cùng start hoặc start ngoài video, đánh dấu xung đột và không chia cho W bằng/nhỏ hơn 0; giữ tốc độ thủ công cho preview và cho xuất theo chính sách cảnh báo. Start âm hoặc end không lớn hơn start là dữ liệu lỗi cần sửa.
- Dùng time-stretch giữ cao độ; clip ngắn có khoảng lặng. Giữ nguyên start/end SRT đã nhập hoặc người dùng sửa thủ công; phần audio dùng khoảng nghỉ nếu chế độ đó được chọn phải có trạng thái riêng.
- Nếu vượt giới hạn, hiện độ dài vượt; cho xuất sau cảnh báo theo mục 3.4. Mix các clip tại start cố định kể cả khi chồng nhau; không ghi đè clip trước. Không tự cắt lời, AI rút gọn, kéo lùi câu hoặc xuất âm thanh cũ.
- Đề xuất cho trường hợp lời cuối vượt hết video: giữ phần lời còn lại, nối nền im lặng và báo MP3 dài hơn video; thời lượng xuất `max(video_duration, max(start_i + rendered_duration_i))`. Tránh mâu thuẫn giữa giữ nguyên lời và ép chiều dài video. Preview video dừng ở cuối hình nhưng audio có thể phát hết phần đuôi; UI ghi rõ.
- Cue chồng lấn hoặc vượt video được báo riêng, không âm thầm đẩy lùi hoặc cắt bỏ. WAV chưa có/lỗi thời phải tạo lại trước khi xuất; quyền xuất chồng lời không có nghĩa cho phép dùng audio cũ hoặc bỏ câu.

**Công cụ:** VieNeu SDK, NumPy/SoundFile, FFmpeg `atempo`, pytest.

**Bàn giao:** Timeline khớp và chỉnh tốc độ từng câu. **Ước tính:** 3–4 ngày.

## Phase 5 — Bốn chế độ âm gốc và xuất MP3

**Mục tiêu:** Tạo một bản phối âm thanh đúng thời lượng video.

- Trích audio gốc, chuẩn hóa sample rate; giữ stereo của nền, đưa lời mono vào giữa hai kênh. Video không audio dùng nền im lặng.
- Dựng envelope giảm âm từ vị trí/độ dài lời lồng đã xử lý, có chuyển mức mượt; không cần STT. Ngưỡng hoạt động có thể lấy từ biên độ WAV lồng nếu cần tránh hạ nền trong khoảng im lặng dài.
- Áp dụng đầy đủ bốn preset. Các mức dB, attack/release được chốt qua nghe thử và lưu nội bộ, không thêm bảng cài đặt phức tạp.
- Mix nền và giọng, kiểm soát peak bằng limiter; giữ phần nền cuối tới hết video, kể cả khi SRT kết thúc sớm.
- Khi nhiều lời chồng nhau, envelope giảm nền dựa trên hợp các đoạn đang nói, không cộng dồn mức giảm cho từng câu. Kiểm tra limiter không làm méo đoạn chồng. Nếu lời vượt video thì kéo dài đầu ra theo quy tắc phase 4 và ghi rõ trước khi tải.
- Xuất MP3, đề xuất 48 kHz stereo 192 kbps; kiểm tra encoder khi setup. Không tự fallback thành WAV mà vẫn gắn nhãn MP3.
- Hiển thị nghe thử, tải MP3 và xuất MKV hai audio track theo phase 5B. Không xuất phụ đề.
- Hủy hiệu lực bản phối cũ khi đổi câu, tốc độ hoặc preset; tránh tải nhầm kết quả chưa cập nhật.
- Dựng preview từ chính bản phối dùng để encode MP3, phục vụ media có hỗ trợ tua; bản phối gắn với project revision. Thử play/pause/seek nhiều lần để kiểm tra lời không trôi khỏi hình. Không render video mới chỉ để nghe thử.

**Công cụ:** FFmpeg (`volume`/envelope, `amix`, `alimiter`, `libmp3lame`), ffprobe.

**Bàn giao:** Preview đồng bộ, MP3 và kiểm thử đủ bốn chế độ. **Ước tính:** 2–3 ngày.

## Phase 5B — Xuất MKV hai audio track

**Mục tiêu:** Remux video gốc và đúng hai audio track, giữ nguyên video và audio gốc đã chọn, thêm bản phối lồng tiếng.

- Nhận diện container/track, xử lý nhánh MKV và không-MKV, quản lý tệp tạm theo mục 6.
- Tạo API export MKV có tiến độ/hủy, kiểm tra kết quả bằng JSON identify rồi mới cho tải.
- Bổ sung giao diện chọn track gốc nếu đầu vào có nhiều audio track; dùng cùng track này làm nền cho MP3 và bản lồng tiếng.
- Kiểm thử số track, thứ tự/tên/default flag, đồng bộ và trường hợp lỗi.

**Công cụ:** MKVToolNix (mkvmerge, mkvextract khi cần), FFmpeg/ffprobe, Python subprocess.

**Bàn giao:** File MKV có một video chính và đúng hai audio track. **Ước tính:** 2–3 ngày.

## Phase 6 — Cài đặt Windows và hoàn thiện luồng sử dụng

**Mục tiêu:** Người dùng khởi động bằng một thao tác.

- Tạo Setup/Start, tự kiểm tra runtime và FFmpeg, tải model có tiến độ lần đầu, mở trình duyệt khi server sẵn sàng.
- Đóng gói frontend build sẵn; ghi log dễ đọc và thông báo thiếu tài nguyên/đĩa đầy/cổng bận.
- Bỏ các màn hình sách nói, dựng video, AI, nhận diện, dịch, API key và chọn backend thừa khỏi ứng dụng mới.
- Cô lập file theo project; kiểm tra Origin/Host cho API cục bộ, không bật public share; không phục vụ đường dẫn tùy ý ngoài project.
- Quy định lưu dự án, dọn file tạm và phục hồi job sau khi ứng dụng đóng bất ngờ.
- Viết hướng dẫn ngắn và giữ ghi nhận nguồn của các thành phần tái sử dụng.
- Tách launcher Windows khỏi CLI/server đa nền tảng; cấu hình đường dẫn và executable qua môi trường theo mục 7. Kiểm tra smoke test trên Linux headless, không cần phát hành Docker image trong giai đoạn này. **Bổ sung 1–2 ngày** cho tính tương thích Linux/Docker.

**Công cụ:** PowerShell/launcher Python, uv, frontend build, logging.

**Bàn giao:** Bản chạy cục bộ và hướng dẫn cài. **Ước tính:** 2–3 ngày.

## Phase 7 — Nghiệm thu chức năng, đồng bộ và hiệu năng

**Mục tiêu:** Xác minh toàn bộ luồng video + SRT → chỉnh câu → MP3 hoặc MKV hai audio track.

- Unit test parser, giới hạn tốc độ, không dịch start của câu sau và trạng thái cache cũ.
- Integration test media tổng hợp: vị trí lời, khoảng lặng, nền stereo, bốn mức âm gốc, peak và thời lượng output. Tính đến delay/padding của MP3 khi đo đồng bộ sau giải mã.
- Kiểm tra UI: nhập file, sửa câu, đổi tốc độ, nghe, tạo lại, hủy/tiếp tục, đổi preset và tải bản mới nhất.
- Thử đường dẫn tiếng Việt, file thiếu audio, video codec khó preview, SRT chồng lấn, cue quá dài, model chưa tải và ngắt mạng sau setup.
- Benchmark trên CPU máy đích với video ngắn, 10 phút và 30–60 phút: đo thời gian tạo, RAM, đĩa và khả năng UI phản hồi. Không cam kết realtime trước khi đo.
- Đối chiếu ảnh desktop ở cùng kích thước cửa sổ; ghi nhận các khác biệt do giới hạn trình duyệt.
- Thử 522–1.000 câu, cửa sổ 1366×768 và 1920×1080; kiểm tra cuộn/zoom/chọn câu, kế thừa giọng/tốc độ và job hoàn thành sau khi câu đã được sửa.
- Tiêu chí timing trước mã hóa: start sai lệch không quá 10 ms; preview sau seek mục tiêu dưới 100 ms sau khi ổn định; file MP3 giải mã có xét encoder delay/padding, mục tiêu sai lệch không quá 50 ms so với timeline PCM. Đây là mục tiêu nghiệm thu cần đo, không phải kết quả đã đạt.

**Công cụ:** pytest, kiểm tra trình duyệt, FFmpeg/ffprobe, đo tài nguyên Windows.

**Bàn giao:** Báo cáo nghiệm thu và bản ổn định. **Ước tính:** 3–4 ngày.

## 5. Thời gian và tiêu chí hoàn tất

Tổng ước tính cập nhật: **19,5–29 ngày công cho một kỹ sư** (làm tròn 20–29), cộng **3–5 ngày dự phòng** codec/preview/đóng gói. Gồm mức cơ sở 16,5–24 ngày, phase 5B thêm 2–3 ngày và chuẩn bị tương thích Linux/Docker thêm 1–2 ngày. Chưa gồm phát hành/vận hành Docker image chính thức, domain hoặc nhiều người dùng. Không bao gồm thời gian chờ phản hồi hoặc tải model qua mạng chậm.

Nếu chọn giữ thư viện giọng đầy đủ: thêm 1,5–2,5 ngày cho tìm/lọc, yêu thích, sửa metadata, tạo/cache mẫu; giữ voice ID gốc và metadata override riêng, đổi tên không làm đổi giọng hoặc mất liên kết câu.

Nếu triển khai từ điển phát âm ở giai đoạn sau: thêm 2–3 ngày cho luật thay thế không đệ quy, thứ tự ưu tiên rõ ràng, khớp từ Unicode/hoa thường, import/validate, nghe thử và cache theo phiên bản từ điển. Lưu text hiển thị riêng text đưa vào engine; đổi luật chỉ làm mất hiệu lực câu bị ảnh hưởng. Hai tiện ích này đã được xác nhận nằm ngoài bản đầu.

Hoàn tất khi:

- Nhập video và SRT, chọn giọng, sửa lời/tốc độ từng câu được.
- v3 Turbo chạy CPU; sau setup đủ tài nguyên có thể tổng hợp và xuất khi mất mạng.
- Câu quá dài được báo; không kéo lùi câu sau, không âm thầm cắt lời hoặc dùng WAV lỗi thời.
- Bốn chế độ âm gốc hoạt động; file tải về là MP3 nghe được, theo thời lượng video hoặc dài hơn khi cần giữ lời vượt cuối video như quy tắc phase 4; sai số codec được kiểm tra.
- Khi câu không vừa, cảnh báo cho phép tiếp tục xuất; MP3 giữ đúng start, trộn được các lời chồng nhau và không bị ghi đè hoặc đẩy lùi. Trường hợp không tràn, tận dụng khoảng nghỉ và chỉ tăng tốc khi cần.
- Không có chức năng nhận diện/dịch/AI/sách nói/dựng video hoặc yêu cầu API trả phí trong luồng sản phẩm.
- Có launcher Windows và báo cáo kiểm tra trên máy đích.
- Xuất MKV thành công phải có đúng hai audio track, video không encode lại, audio gốc không bị áp dụng giảm nền; đổi track nghe được bằng trình phát hỗ trợ MKV. Nhánh không-MKV không lặp lại audio nguồn thành track thứ ba.
- Lõi có smoke test Linux headless, cấu hình data/cache/tool path bên ngoài mã nguồn và không phụ thuộc launcher Windows.

Đã có ảnh tham chiếu đủ để tái dựng bố cục và phong cách. Khả thi bằng stack hiện tại, nhưng ảnh không cung cấp source, hệ số giảm âm hoặc công thức tốc độ; không cam kết tái tạo thuật toán nội bộ y hệt. Rủi ro chính là thời gian tổng hợp CPU, quản lý revision/cache, preview đồng bộ và codec video; phase 2 phải chạy thử CPU thực trước khi hoàn thiện toàn bộ UI. Không cần STT, dịch hay API trả phí cho các yêu cầu đã chốt.

## 6. Bổ sung chức năng xuất video MKV — đúng hai audio track

### 6.1. Mô tả chức năng và hợp đồng đầu ra

Đầu ra luôn có đuôi `.mkv` và container Matroska, một video chính và **đúng hai audio track**:

1. **Âm thanh gốc**: sao chép track nguồn đã chọn, không giảm âm, không trộn giọng và không mã hóa lại.
2. **Lồng tiếng**: bản phối đã có giọng mới và nền theo một trong bốn preset; nếu chọn Tắt âm gốc, track này chỉ có lời mới. Tái sử dụng MP3 đã tạo cho đúng revision để không encode lần nữa.

Hai track là hai lựa chọn nghe thay thế trong trình phát, không phải yêu cầu phát cả hai đồng thời. Đề xuất track lồng tiếng là mặc định, tên rõ ràng, ngôn ngữ `vi`; giữ ngôn ngữ gốc nếu biết, không đoán. Không thêm SRT đã nhập hay đốt phụ đề; bản cơ sở không sao chép subtitle/attachment từ nguồn, giữ chapters từ video khi hỗ trợ. Video chính không tái mã hóa.

### 6.2. Kiểm tra trước khi chạy

- Dùng `mkvmerge -J` nhận diện container và lấy track ID, kết hợp ffprobe kiểm tra thời lượng/timestamp. Không chỉ dựa vào đuôi file.
- Lưu riêng ID mkvmerge và stream index FFmpeg; chúng không nhất thiết giống nhau. Không hardcode ID trong ứng dụng.
- Đầu vào có nhiều audio track: người dùng chọn một track gốc qua tên/ngôn ngữ/số kênh/nghe thử. Đề xuất sẵn track mang cờ default, nếu không có thì track đầu; chỉ track đã chọn được giữ và dùng làm nền.
- Bản phối phải mới nhất, các câu có WAV hợp lệ; chính sách cảnh báo chồng lời vẫn áp dụng.
- Kiểm tra mkvmerge/FFmpeg, hỗ trợ codec và dung lượng đĩa. Ghi output tạm theo job; chỉ đổi tên thành kết quả tải về sau khi xác minh.

### 6.3. Nhánh A — Đầu vào đã là MKV

1. Nhận diện video chính và track gốc đã chọn.
2. Gọi mkvmerge trực tiếp với MKV nguồn và MP3 lồng tiếng; lọc rõ video/audio, không mang theo các audio track khác.
3. Đặt tên/default flag, thứ tự hai audio track và kiểm tra đầu ra.

Ví dụ minh họa: `mkvmerge -J` đã xác nhận nguồn có video ID 0, audio gốc ID 1; MP3 có audio ID 0. Các lệnh dưới đây là mẫu, chưa chạy trên media thực.

```text
mkvmerge -J "input.mkv"
mkvmerge -J "dubbed.mp3"
mkvmerge -o "output.mkv" --track-order 0:0,0:1,1:0 --video-tracks 0 --audio-tracks 1 --no-subtitles --no-attachments --track-name "1:Original" --default-track-flag 1:no "input.mkv" --no-video --no-subtitles --no-chapters --no-global-tags --audio-tracks 0 --track-name "0:Vietnamese Dub" --language 0:vi --default-track-flag 0:yes "dubbed.mp3"
```

Tùy chọn cho từng input phải nằm trước input tương ứng. Bản sản phẩm cũng kiểm soát track tags/forced flags từ nguồn khi cần để không giữ cờ phát ưu tiên gây nhầm.

### 6.4. Nhánh B — Đầu vào không phải MKV

1. Nhận diện container/codec và track gốc.
2. **Tách riêng audio gốc** bằng FFmpeg stream copy vào `.mka` (Matroska chỉ audio). MKA giúp tránh phải đoán đuôi elementary stream theo codec.
3. Gọi mkvmerge với video nguồn đã tắt toàn bộ audio, MKA audio gốc và MP3 lồng tiếng. Đây là bước tạo MKV cuối cùng bằng mkvmerge.
4. Kiểm tra và công bố kết quả.

Ví dụ nguồn MP4 có video mkvmerge ID 0, audio cần giữ là FFmpeg `0:a:0`; audio trong MKA và MP3 đều đã được identify là ID 0:

```text
ffprobe -v error -show_streams -show_format -of json "input.mp4"
ffmpeg -nostdin -i "input.mp4" -map 0:a:0 -vn -sn -dn -c:a copy "original.mka"
mkvmerge -J "input.mp4"
mkvmerge -J "original.mka"
mkvmerge -o "output.mkv" --track-order 0:0,1:0,2:0 --video-tracks 0 --no-audio --no-subtitles --no-attachments "input.mp4" --no-video --no-subtitles --no-chapters --no-global-tags --audio-tracks 0 --track-name "0:Original" --default-track-flag 0:no "original.mka" --no-video --no-subtitles --no-chapters --no-global-tags --audio-tracks 0 --track-name "0:Vietnamese Dub" --language 0:vi --default-track-flag 0:yes "dubbed.mp3"
```

**Các lệnh mẫu giả định timestamp nguồn bắt đầu đồng bộ tại 0.** Sản phẩm phải đo độ lệch audio/video trước và sau tách, lưu mốc chuẩn timeline và áp dụng `--sync <audio-id>:<offset-ms>` khi cần. Không cộng offset hai lần nếu MKA đã giữ nó. MP4 edit lists, encoder delay, timestamp âm/non-zero và VFR cần test riêng; không ép CFR hoặc đổi fps.

`mkvextract` chỉ nhận nguồn Matroska, không phải công cụ tách trực tiếp MP4/AVI/MOV. Ví dụ nếu cần chẩn đoán/tách audio AAC từ một MKV/MKA đã biết codec và ID:

```text
mkvextract "source.mkv" tracks 1:"original.aac"
```

Không dùng `.aac` cho mọi codec. Nhánh MKV thông thường không cần mkvextract. Nếu cần dùng riêng bộ MKVToolNix cho bước tách của input khác MKV và mkvmerge đọc được nguồn, có thể tạo MKA bằng `mkvmerge --no-video --audio-tracks <id> ...`, rồi ghép; quy trình chính vẫn dùng FFmpeg để tách theo yêu cầu.

### 6.5. Các trường hợp biên và cách xử lý

| Trường hợp | Hành vi |
|---|---|
| Video không có audio gốc | Không thể tạo một track gốc thật. Bản cơ sở báo rõ và không cho xuất chế độ MKV hai track; MP3 vẫn hoạt động. Không giả tạo track im lặng rồi gọi là âm gốc. Nếu sau này muốn track im lặng, phải là chế độ được chọn rõ và đặt tên đúng |
| Nguồn có nhiều audio | Giữ đúng một track do người dùng chọn và một track lồng. Không tự giữ tất cả |
| Nguồn có nhiều video | Chọn video chính; không mang theo ảnh cover hoặc video phụ ngoài lựa chọn |
| mkvmerge không đọc được container nhưng FFmpeg đọc được | Thử remux trung gian video bằng FFmpeg stream copy, giữ audio đã tách; bước cuối vẫn mkvmerge. Không tự transcode |
| Codec không remux được vào Matroska, file hỏng hoặc mã hóa/DRM | Báo codec/lỗi cụ thể, không tạo output một phần hoặc đổi định dạng ngầm |
| Audio gốc không stream-copy được | Dừng xuất MKV với lý do rõ; không âm thầm mã hóa lại track gốc |
| Lời lồng vượt chiều dài hình | Giữ audio theo chính sách hiện tại, cảnh báo MKV có audio dài hơn video. Trình phát có thể giữ hình cuối hoặc hết hình; không hứa tự kéo dài video qua remux |
| Thiếu tool hoặc đĩa đầy, hủy giữa chừng | Lỗi có thể khắc phục; không ghi đè nguồn/kết quả trước; dọn file tạm thuộc đúng job |
| mkvmerge trả mã 1 | Là cảnh báo; đọc log và kiểm định đầu ra trước khi quyết định cho tải. Mã 2 là lỗi; không đánh dấu thành công |
| Trình duyệt không phát/đổi track MKV | Tải file bình thường; preview WebUI dùng bản phối riêng. Nghiệm thu chuyển track bằng player hỗ trợ Matroska, không phụ thuộc browser |

### 6.6. Kiểm định đầu ra

- Chạy `mkvmerge -J output.mkv`: container Matroska, audio count đúng 2, đúng tên/thứ tự/default flag và một video chính. Kiểm tra thêm bằng ffprobe.
- Không chỉ đếm track: so sánh codec, số kênh, sample rate và kiểm tra dữ liệu audio gốc/video đã copy bằng phép so sánh payload phù hợp hoặc giải mã trên fixture; không so hash toàn file vì container thay đổi.
- Nghe/chuyển từng track, tua đầu/giữa/cuối, đo offset với nguồn và WAV timeline; kiểm tra bốn preset chỉ ảnh hưởng track lồng.
- Test MKV, MP4, AVI, MOV được tool hỗ trợ; input nhiều audio, không audio, Unicode/spaces, offset khác 0, VFR và audio vượt cuối video trên Windows/Linux.
- Xuất MP3/MKV cùng revision phải dùng cùng nội dung lồng; thay lựa chọn track gốc phải hủy hiệu lực bản phối nền và output liên quan.

Nguồn kỹ thuật: [mkvmerge manual](https://mkvtoolnix.download/doc/mkvmerge.html), [mkvextract manual](https://mkvtoolnix.download/doc/mkvextract.html). Cú pháp đã đối chiếu tài liệu; chưa chạy lệnh remux thực tế trong giai đoạn lập kế hoạch.

## 7. Thiết kế để hỗ trợ Docker sau này

**Mục tiêu:** Windows là cách đóng gói đầu tiên, không phải phụ thuộc của lõi ứng dụng. Docker triển khai sau vẫn dùng cùng API, worker và pipeline export.

- Dùng Python pathlib và subprocess với danh sách argument, `shell=False`; không phụ thuộc PowerShell/cmd, ký tự ổ đĩa, registry hoặc dialog Windows trong logic xử lý. PowerShell chỉ là launcher tùy chọn.
- Lệnh server headless thống nhất, ví dụ `python -m apps.dubbing_web`; việc mở browser nằm trong launcher Windows và có thể tắt. Linux không cần desktop session.
- Cấu hình `APP_HOST`, `APP_PORT`, `APP_DATA_DIR`, `APP_TEMP_DIR`, `HF_HOME`, `FFMPEG_BIN`, `FFPROBE_BIN`, `MKVMERGE_BIN`, `MKVEXTRACT_BIN` qua môi trường/config. Tool lookup theo PATH hoặc cấu hình, không gắn cứng `.exe`.
- Frontend gọi API bằng URL tương đối cùng origin; người dùng chọn/upload file bằng trình duyệt. Không gửi đường dẫn Windows của client để server Linux tự mở.
- Tách data bền vững, model cache và job temp khỏi source/frontend. Docker sau này mount `/data` và `/models`, đặt temp đủ dung lượng; SQLite nằm trên volume local, một worker ghi và một instance cơ sở.
- Windows mặc định bind loopback. Trong container dùng `0.0.0.0` theo cấu hình và publish ra `127.0.0.1` của host khi chạy local; không đồng nghĩa mở Internet. Domain/auth/multi-user là giai đoạn riêng.
- Dependencies CPU được pin và giải quyết cho cả Windows AMD64/Linux x86_64; MKVToolNix/FFmpeg cài theo OS và kiểm tra version/capability lúc khởi động. Không sao chép `.venv` hoặc executable Windows sang image Linux.
- Linux/container chạy non-root, kiểm tra quyền volume, health endpoint phân biệt server sống/model sẵn sàng, log stdout/stderr; xử lý SIGTERM và shutdown Windows để dừng job/subprocess an toàn, khôi phục job chưa xong sau restart.
- Frontend build tĩnh; không cần Node.js lúc runtime. Không yêu cầu CUDA; giới hạn CPU/thread/RAM qua cấu hình khi chạy container.
- Ngay bản đầu có CI/smoke test Linux cho upload, parse, job giả lập, remux và đường dẫn; có kiểm tra inference CPU thật riêng khi có model. Dockerfile/Compose production và vận hành image được làm sau, không tính là đã bàn giao ở bản Windows.

**Tiêu chí sẵn sàng cho giai đoạn Docker:** cùng CLI chạy headless trên Linux, mọi dữ liệu nằm ở thư mục cấu hình, không có tác vụ nghiệp vụ bắt buộc gọi shell Windows, các test MKV hai track qua được trên hai OS. Phần chuẩn bị này thêm 1–2 ngày vào phase 6; không cần thay kiến trúc khi bắt đầu đóng gói container.


### Cập nhật phạm vi ngày 15/09/2026
Từ điển đã lưu áp dụng chung cho tất cả dự án và nghe mẫu giọng. Dự án hiện có tự cập nhật, chỉ các câu đổi lời đọc cần tạo lại; file âm thanh đã xuất không bị sửa. Phiên bản hàng đợi đã tạo giữ snapshot cũ, phiên bản tạo mới dùng luật hiện hành. Không còn bước áp dụng riêng cho dự án.
Phòng thu để clone và lưu giọng custom được bổ sung vào giai đoạn 4 của `docs/EXECUTION_PLAN.vi.md`, chưa triển khai.
