---
name: timeline-milestones-logic
description: Quy định hiển thị trục thời gian (Timeline) lấy ngày từ ô C8 và quản lý các mốc tiến độ dự án.
---

# 📅 Quy chuẩn Trục Thời Gian (Timeline Milestones)

Hệ thống cung cấp công cụ trực quan hóa tiến độ theo thời gian thực, giúp theo dõi các sự kiện quan trọng và kế hoạch sản xuất ngay phía trên bảng thống kê.

## 1. Thành phần giao diện (UI Components)
Dựa trên thiết kế mockup, giao diện điều khiển Timeline bao gồm:
- **Input Header:** - Ô nhập "Ngày" (Date Input).
    - Ô nhập "Mô tả" nội dung sự kiện.
    - Bảng chọn "Ghi chú/Kế hoạch".
- **Action Buttons (Bộ nút chức năng):** - **Thêm**: Chèn một mốc mới vào trục.
    - **Xóa mốc**: Loại bỏ mốc đang chọn.
    - **Xóa tất cả**: Xóa toàn bộ lịch sử Timeline.
    - **Làm mới**: Cập nhật lại số liệu thực tế từ Excel.

## 2. Cấu trúc nội dung tại mỗi mốc (Milestone Data)
Mỗi điểm nút (Dot) trên Timeline hiển thị các thông tin được truy xuất từ file `config.xlsx` và dữ liệu thực tế:

- **Ngày - Tháng (Mốc thời gian):** AI phải đọc giá trị chính xác tại ô **C8** của file Excel được chọn.
    - Định dạng hiển thị: `DD/MM`.
- **Thông số kỹ thuật (Info Box):** Hiển thị trạng thái hoàn thành tổng quát tại thời điểm đó:
    - **Shop duyệt (CAD)**: xx/yy.
    - **Ván**: xx/yy.
    - **Sản xuất (CNC)**: xx/yy.
    - **Vật tư**: xx/yy.
- **Ghi chú & Kế hoạch:** Nội dung văn bản mô tả kế hoạch cho mốc thời gian đó.



## 3. Logic xử lý dữ liệu ô C8
- **Truy xuất:** AI sử dụng tọa độ `row 8, column C` (trong Pandas là `iloc[7, 2]`) để lấy ngày mốc.
- **Fallback:** Nếu ô **C8** trống hoặc lỗi định dạng, AI lấy ngày hiện tại của hệ thống làm giá trị mặc định.
- **Đồng bộ:** Mỗi khi dữ liệu tại ô C8 thay đổi, trục Timeline phải tự động dịch chuyển mốc tương ứng.

## 4. Quy tắc hiển thị & Màu sắc
- **Màu Xanh Biển (#1E88E5):** Dành cho các mốc thời gian đã hoàn thành (TT = TC).
- **Màu Vàng (#FF9800):** Dành cho các mốc đang thực hiện hoặc kế hoạch sắp tới.
- **Đường kẻ ngang:** Nối liền các mốc, thể hiện dòng thời gian xuyên suốt của dự án.

## 5. Hướng dẫn kỹ thuật cho AI
- **Data Persistence:** Lưu trữ danh sách các mốc vào một sheet `Timeline` trong file `config.xlsx` để không bị mất dữ liệu khi tắt App.
- **UI:** Sử dụng `st.columns` để tạo hàng nút bấm và `st.container` kèm CSS để vẽ trục Timeline nằm ngang theo đúng tỉ lệ mockup.