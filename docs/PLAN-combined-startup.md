# Kế hoạch triển khai: Hợp nhất lệnh chạy LiteLLM và YOLOv8 thành 1 tập lệnh duy nhất

Tài liệu này chi tiết hóa kế hoạch tạo một tập lệnh PowerShell (`start-all.ps1`) hoặc nâng cấp tập lệnh (`start.ps1`) hiện tại để tự động khởi chạy song song cả **LiteLLM Proxy (Port 4000)** và **YOLOv8 Proctoring Server (Port 8001)** chỉ bằng một lệnh duy nhất.

---

## 📌 Tổng quan dự án (Overview)
Hiện tại, dự án AI yêu cầu chạy độc lập hai máy chủ:
1. **YOLOv8 Proctoring Server**: Chạy trên cổng `8001` (`main.py` thông qua FastAPI/Uvicorn).
2. **LiteLLM Proxy**: Chạy trên cổng `4000` (`litellm` thông qua cấu hình `litellm_config.yaml`).

Việc chạy hai lệnh riêng biệt trong hai cửa sổ terminal gây phiền phức và khó kiểm soát tiến trình chạy ngầm. Kế hoạch này sẽ hợp nhất việc khởi chạy vào một tập lệnh thông minh, hỗ trợ kiểm tra cổng bận, luồng log hợp nhất (Unified Log Stream) và tự động dọn dẹp tiến trình khi bấm `Ctrl+C`.

---

## 📐 Loại dự án (Project Type)
* **Dự án**: AI / BACKEND (Python FastAPI & LiteLLM Proxy)
* **Hệ điều hành**: Windows (Sử dụng PowerShell `.ps1`)

---

## 🎯 Tiêu chí thành công (Success Criteria)
1. Khởi động cả hai máy chủ bằng đúng một lệnh duy nhất: `.\start.ps1` hoặc `.\start-all.ps1`.
2. Tự động kiểm tra xem cổng `4000` hoặc `8001` có bị chiếm dụng trước khi chạy không để cảnh báo sớm.
3. Log của cả hai máy chủ được in chung trên một cửa sổ terminal nhưng được gắn nhãn màu sắc riêng (ví dụ: `[LiteLLM]` màu Cyan, `[YOLOv8]` màu Yellow) để dễ theo dõi.
4. Khi nhấn `Ctrl+C` tại terminal chính, cả hai tiến trình con chạy ngầm đều được tắt an toàn (Graceful Shutdown), không để lại tiến trình rác chạy ẩn trên hệ thống.

---

## 🛠️ Công nghệ sử dụng (Tech Stack)
* **PowerShell 7+ / 5.1**
* **PowerShell Background Jobs & Runspaces** (Để chạy song song các tiến trình)
* **Windows API / Get-Process** (Để quản lý và giải phóng tài nguyên)

---

## 📁 Cấu trúc file đề xuất (File Structure)
```
c:/AuAc/AuraAcademic_AI/
├── docs/
│   └── PLAN-combined-startup.md (Kế hoạch này)
├── start.ps1 (Cập nhật tập lệnh hiện tại để hợp nhất khởi chạy)
└── main.py (Giữ nguyên)
```

---

## 📋 Chi tiết các tác vụ cần thực hiện (Task Breakdown)

### Tác vụ 1: Thiết lập cấu trúc song song & Kiểm tra cổng bận
* **Mô tả**: Thiết lập cơ chế kiểm tra cổng `4000` và `8001` trước khi chạy. Nếu cổng bị chiếm dụng, thông báo tiến trình đang chiếm giữ.
* **Người thực hiện**: `backend-specialist`
* **Kỹ năng**: `powershell-windows`
* **Độ ưu tiên**: Cao (Blocker cho các bước sau)
* **Đầu vào**:
  * Yêu cầu kiểm tra cổng bằng lệnh `Get-NetTCPConnection` hoặc `netstat`.
* **Đầu ra**:
  * Khối mã kiểm tra cổng bận được tích hợp vào đầu kịch bản `start.ps1`.
* **Xác thực (Verify)**: Chạy thử khi đang mở sẵn một ứng dụng trên cổng 4000, kiểm tra xem script có cảnh báo chuẩn xác không.

### Tác vụ 2: Khởi chạy song song bằng PowerShell Jobs và Hợp nhất luồng Log
* **Mô tả**: Khởi chạy `.\venv\Scripts\litellm` và `.\venv\Scripts\python.exe main.py` dưới dạng các tiến trình con song song. Đọc luồng log đầu ra của từng Job theo thời gian thực và ghi ra console chính kèm theo tiền tố màu để phân biệt.
* **Người thực hiện**: `backend-specialist`
* **Kỹ năng**: `powershell-windows`
* **Độ ưu tiên**: Cao
* **Đầu vào**:
  * Các lệnh thực thi trong môi trường ảo `venv`.
* **Đầu ra**:
  * Đoạn mã quản lý Job song song (`Start-Job` hoặc sử dụng luồng bất đồng bộ) và in log thời gian thực.
* **Xác thực (Verify)**: Chạy script và xác nhận màn hình in ra cả log của logo LiteLLM và log "Loading YOLOv8 models..." của `main.py`.

### Tác vụ 3: Xử lý dọn dẹp tiến trình an toàn khi dừng (Ctrl+C)
* **Mô tả**: Đăng ký bắt sự kiện đóng/hủy của PowerShell (dùng khối lệnh `finally` hoặc xử lý ngắt tín hiệu). Khi người dùng nhấn `Ctrl+C`, tự động gửi tín hiệu dừng (`Stop-Job` hoặc `taskkill`) để giải phóng hoàn toàn các máy chủ con.
* **Người thực hiện**: `backend-specialist`
* **Kỹ năng**: `powershell-windows`
* **Độ ưu tiên**: Cao
* **Đầu vào**:
  * Quản lý tiến trình bằng Process ID (PID).
* **Đầu ra**:
  * Cơ chế tắt an toàn được tích hợp hoàn chỉnh.
* **Xác thực (Verify)**: Chạy script, nhấn `Ctrl+C` dừng chương trình, chạy lệnh `Get-Process` kiểm tra xem các cổng 4000 và 8001 có thực sự được giải phóng hoàn toàn không.

---

## 🏁 Phase X: Kiểm tra và Đánh giá (Verification)
Sau khi triển khai xong, các bước kiểm tra cuối cùng sẽ bao gồm:
- [ ] Chạy thử lệnh khởi động duy nhất `.\start.ps1` thành công không phát sinh lỗi.
- [ ] Kiểm tra tính chính xác của cơ chế cảnh báo cổng bận.
- [ ] Xác nhận luồng log hiển thị trực quan, có phân biệt màu sắc.
- [ ] Xác nhận nhấn `Ctrl+C` giải phóng hoàn toàn cả 2 tiến trình con.
