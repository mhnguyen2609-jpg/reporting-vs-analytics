---
name: project-selection-workflow
description: Quy trình tìm kiếm folder, chọn dự án và hiển thị Dashboard kèm chức năng xuất PDF.
---

# 🚀 Reference: Workflow Tìm kiếm & Hiển thị

Quy trình này hướng dẫn AI cách truy cập vào `D:\Cong viec` để người dùng chọn đúng Hợp đồng cần xem.

## 1. Bước 1: Tìm kiếm & Drill-down (Lọc folder)
Hệ thống sẽ thực hiện quét thư mục theo cấp bậc:
- **Cấp 1:** Chọn Năm (Ví dụ: 2026).
- **Cấp 2:** Tìm kiếm theo Mã hợp đồng hoặc Tên khách hàng (AI phải thực hiện tìm kiếm mờ - Fuzzy search trong tên folder).
- **Cấp 3:** Hiển thị danh sách kết quả trùng khớp để người dùng Click chọn.

## 2. Bước 2: Hiển thị Định danh (Header)
Sau khi người dùng chọn một folder cụ thể, Dashboard phải hiển thị lớn và rõ ràng ở trên cùng:
- **Mã Hợp đồng:** (Ví dụ: HD123)
- **Tên Khách hàng:** (Ví dụ: Nguyễn Văn A)
*Thông tin này được trích xuất từ tên folder hoặc nội dung file Excel bên trong.*

## 3. Bước 3: Sidebar & Dashboard
Khi đã chọn xong dự án:
- **Bên trái (Sidebar):** Hiển thị bảng "Tổng Chỉ Huy" (Vật tư ưu tiên, CAD, Ván, CNC) theo tỷ lệ `xx/yy` và thanh Progress Bar.
- **Bên phải (Main):** Hiển thị bảng chi tiết từng Mã SP (SP01, SP02...).



## 4. Bước 4: Chức năng Xuất PDF
- **Nút bấm:** [Xuất PDF]
- **Hành động:** AI sẽ chụp lại toàn bộ Dashboard hiện tại (bao gồm cả bảng tổng và bảng chi tiết) và chuyển đổi thành định dạng PDF.
- **Tên file xuất:** `Bao_cao_tien_do_[Ma_HD]_[Ngay_thang].pdf`.

## 5. Quy định cho AI
- Không được load toàn bộ dữ liệu ngay từ đầu để tránh chậm máy. Chỉ khi người dùng chọn folder thì mới bắt đầu tính toán `xx/yy`.
- Chức năng xuất PDF phải đảm bảo giữ đúng màu sắc (Xanh/Vàng/Đỏ) của các thanh tiến độ để người xem báo cáo dễ nắm bắt.