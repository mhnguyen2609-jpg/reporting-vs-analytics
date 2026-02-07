---
name: timeline-milestones-logic
description: Tài liệu chi tiết về logic, cấu trúc dữ liệu và giao diện hiển thị của Trục Thời Gian (Timeline).
---

# 📅 Quy chuẩn Trục Thời Gian (Timeline Milestones)

Hệ thống Timeline được thiết kế để trực quan hóa tiến độ sản xuất theo thời gian thực, kết hợp dữ liệu tự động từ file bản vẽ và dữ liệu nhập thủ công từ người dùng.

## 1. Cơ chế hoạt động (Core Mechanism)

Timeline hoạt động dựa trên việc hợp nhất (merge) hai nguồn dữ liệu:
1.  **Tự động (Auto):** Trích xuất từ nội dung file dự án (ví dụ: ngày thống kê từ ô C8 trong file Excel).
2.  **Thủ công (Manual):** Người dùng thêm/sửa/xóa trực tiếp trên giao diện ứng dụng.

### Quy tắc Hợp nhất (Merging Logic)
- **Khóa chính (Key):** Sử dụng Ngày (Date) chuẩn hóa định dạng `YYYY-MM-DD`.
- **Ưu tiên:**
    - Nếu cùng một ngày có cả dữ liệu Tự động và Thủ công, hệ thống sẽ hợp nhất thông tin.
    - Mô tả (Description) sẽ được nối thêm nếu trùng lặp.
- **Sắp xếp:** Tự động sắp xếp tăng dần theo thời gian.

## 2. Quản lý Dữ liệu (Data Management)

Hiện tại, dữ liệu Timeline được quản lý qua `Session State` của Streamlit.

### Cấu trúc Dữ liệu (Data Structure)
Một đối tượng Milestone bao gồm:
```json
{
  "date": "DD/MM/YYYY",       // Chuỗi hiển thị trên UI
  "full_date": "YYYY-MM-DD", // Giá trị dùng để sắp xếp và merge
  "desc": "Mô tả nội dung...", // Nội dung mốc
  "type": "Kế hoạch"     // Loại mốc (Kế hoạch / Ghi chú)
}
```

### Thao tác người dùng (User Actions)
Giao diện cung cấp các công cụ trong khối `expander` "📅 Timeline tiến độ":
- **Thêm/Sửa (Add/Edit):** Form nhập Ngày, Loại (Dropdown), và Mô tả (Text Area).
- **Xóa (Delete):** Nút "❌" để xóa các mốc thủ công.
- **Chỉnh sửa (Edit):** Nút "✏️" để load dữ liệu cũ lên form và cập nhật.

## 3. Giao diện hiển thị (Visualization)

Timeline được render dưới dạng HTML tùy chỉnh (`src/ui/components.py`) với bố cục **Snake Layout** (Xương cá/Ziczac) để tối ưu không gian hiển thị.

### Bố cục "Snake Layout"
- **Trục giữa:** Một đường kẻ ngang cố định ở giữa (`top: 50%`).
- **Phân bố Item:**
    - **Item Chẵn (Even):** Nằm phía trên trục (`bottom: 50%`).
    - **Item Lẻ (Odd):** Nằm phía dưới trục (`top: 50%`).
- **Thẻ nội dung (Card):**
    - Hiển thị Ngày tháng nổi bật.
    - Hiển thị Mô tả chi tiết.
    - Nếu có dữ liệu thống kê (Auto), hiển thị các chỉ số (Shop, Ván, SX, VT).

### Mã màu & Trạng thái
- **Logic màu sắc:**
    - **Hoàn thành (Done):** Màu Xanh Biển (#1E88E5) - Khi Tình trạng thực tế (TT) == Tổng cộng (TC).
    - **Chưa hoàn thành:** Màu Vàng/Cam - Khi còn hạng mục chưa xong.
- **Biểu tượng:** Sử dụng các icon trực quan cho từng loại tài nguyên (Shop, Ván, CNC, Vật tư).

## 4. Hướng dẫn tích hợp (Integration Guide)

Khi phát triển thêm tính năng, cần tuân thủ:
1.  **Dữ liệu đầu vào:** Luôn đảm bảo `full_date` có định dạng `YYYY-MM-DD` để logic sắp xếp hoạt động đúng.
2.  **Lưu trữ:** Hiện tại dữ liệu thủ công chỉ tồn tại trong phiên làm việc (`st.session_state`). Nếu cần lưu lâu dài, cần bổ sung logic ghi vào file cấu hình (ví dụ: `config.json` hoặc file Excel ẩn).
3.  **UI:** Sử dụng hàm `render_timeline_html` trong `src.ui.components` để tạo HTML string từ danh sách milestones đã xử lý.