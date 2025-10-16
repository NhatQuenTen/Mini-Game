# 🪨📄✂️ Rock-Paper-Scissors Online Game

## 📌 Giới thiệu

Đây là ứng dụng **Rock-Paper-Scissors (Oẳn tù tì) online** được lập trình bằng **Python**.
Gồm 2 phần:
- **Server (`gameserver.py`)**: Quản lý kết nối, điều phối game, tính kết quả, lưu điểm số.
- **Client (`gameclient.py`)**: Ứng dụng giao diện đồ họa (Tkinter) cho người chơi, hỗ trợ nhập tên, chọn host/port, và chơi trực tiếp.
Trò chơi hỗ trợ **2 người chơi online** thông qua socket TCP.

------------------------------------------------------------------------

## ⚙️ Yêu cầu hệ thống

-   Python **3.8+**
-   Thư viện chuẩn: `socket`, `threading`, `json`, `tkinter`
-   Hệ điều hành: Windows 

------------------------------------------------------------------------

## 🚀 Cách chạy

# 1. Chạy Server

-   Server sẽ lắng nghe ở `0.0.0.0:12345` (mặc định).\
-   Có thể thay đổi `HOST` và `PORT` trong file `gameserver.py`.

------------------------------------------------------------------------

# 2. Chạy Client

-   Nhập:
    -   **Name**: tên hiển thị của bạn.
    -   **Host**: IP hoặc hostname của server (mặc định: `localhost`).
    -   **Port**: cổng server (mặc định: `12345`).
-   Nhấn **Connect** để kết nối.

------------------------------------------------------------------------

## 🎮 Luật chơi

-   Trò chơi dành cho **2 người chơi**.
-   Khi đủ 2 người, server sẽ bắt đầu **Round 1**.
-   Người chơi bấm chọn **Rock / Paper / Scissors**.
-   Server nhận và so sánh nước đi:
    -   Rock \> Scissors
    -   Scissors \> Paper
    -   Paper \> Rock
-   Điểm số sẽ được cộng cho người thắng.
-   Sau mỗi round, kết quả hiển thị popup:
    -   ✅ Win
    -   ❌ Lose
    -   🤝 Tie
-   Ván tiếp theo sẽ tự động bắt đầu.

------------------------------------------------------------------------

## 📂 Cấu trúc thư mục
    .
    ├── gameclient.py   # Client GUI (Tkinter)
    ├── gameserver.py   # Server (Socket TCP)
    └── README.md       # Tài liệu hướng dẫn

------------------------------------------------------------------------

## 🔑 Các chức năng chính

### Server (`gameserver.py`)

-   Xử lý nhiều client, tối đa **2 người chơi**.
-   Nhận và quản lý thông điệp JSON:
    -   `join`, `move`, `quit`.
-   Điều phối round, tính kết quả, gửi broadcast tới cả 2 client.
-   Quản lý điểm số và vòng chơi.
-   Xử lý tình huống ngắt kết nối.

### Client (`gameclient.py`)

-   Giao diện hiện đại bằng **Tkinter**.
-   Người chơi nhập **tên, host, port**.
-   Hiển thị **trạng thái, điểm số, vòng hiện tại**.
-   Nút chọn **Rock/Paper/Scissors**.
-   Popup thông báo kết quả từng round.
-   Tự động xử lý ngắt kết nối.

------------------------------------------------------------------------

## ⚠️ Lưu ý

-   Server chỉ cho phép **2 người chơi** cùng lúc.
-   Nếu một người thoát, client còn lại sẽ nhận thông báo "Opponent left".
-   Khi test trên 2 máy khác nhau:
    -   Đảm bảo mở **cổng 12345** trên server.
    -   Hoặc dùng **LAN / VPN (VD: Radmin VPN, Hamachi)**.

------------------------------------------------------------------------

## 📜 Lưu ý

Mã nguồn mở, bạn có thể tùy chỉnh và phát triển thêm (ví dụ: nhiều người chơi hơn, bảng xếp hạng, lưu lịch sử).
