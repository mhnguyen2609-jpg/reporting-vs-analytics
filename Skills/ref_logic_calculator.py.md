---
name: backend-calculation-logic
description: Quy định các hàm xử lý dữ liệu (Tính tổng xx/yy, Lọc vật tư ưu tiên, Đối soát chênh lệch).
---

# ⚙️ Reference: Logic Tính Toán (Process Logic)

File này đóng vai trò là "Cỗ máy" xử lý dữ liệu thô từ Excel thành các con số hiển thị trên Dashboard.

## 1. Nhiệm vụ 1: Đọc Định danh (Project Info)
- Mở file `config.xlsx`.
- Tìm chính xác cột **"Mã hợp đồng"** và **"Tên khách hàng"**.
- Trả kết quả về cho App để hiển thị Header.

## 2. Nhiệm vụ 2: Tính tổng xx/yy (Aggregator)
AI phải thực hiện quét (Scan) và cộng tổng cột "Số lượng" cho 5 hạng mục:
- **Vật tư Ưu tiên:** Chỉ cộng các dòng có tên chứa "sắt, inox, da, vải" hoặc ghi chú "ưu tiên".
- **Vật tư Thường:** Cộng các dòng còn lại trong file Vật tư.
- **CAD:** Tổng `SHOP TT` / Tổng `SHOP TC`.
- **Ván:** Tổng `VAT TT` / Tổng `VAT TC`.
- **CNC:** Tổng `CAT` / Tổng `NESTING`.

## 3. Nhiệm vụ 3: Tính toán Bảng chi tiết (Detail Logic)
Cho từng Mã SP (SP01, SP02...), file này phải tính ra:
- **Tỷ lệ %:** (Thực tế / Tiêu chuẩn) * 100.
- **Trạng thái:** Trả về màu sắc hoặc Icon dựa trên hiệu số (Delta).

## 4. Nhiệm vụ 4: Chuẩn bị dữ liệu Xuất PDF
- Thu thập tất cả bảng biểu đã tính toán.
- Đóng gói thành định dạng sạch để hàm in PDF bốc đi nhanh chóng.

## 5. Quy định lập trình (Dành cho AI)
- Luôn sử dụng `errors='coerce'` khi chuyển đổi dữ liệu để tránh lỗi nếu file Excel có ô trống hoặc chữ lạ.
- Kết quả trả về phải là một Dictionary hoặc DataFrame đã được làm sạch hoàn toàn.