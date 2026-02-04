---
name: project-overview-master-table
description: Bảng tổng chỉ huy hiển thị tiến độ 3 cột (TC, TT, % kèm Progress Bar) cho mọi hạng mục.
---
---
# Reference: Bảng Tổng Chỉ Huy (Master Dashboard)

Bảng này là trung tâm điều hành, tổng hợp dữ liệu từ các hạng mục để đưa ra con số tổng quát. Mọi thành phần hiển thị phải tuân thủ nghiêm ngặt các quy tắc dưới đây.

## 1. Cấu trúc hiển thị 3 cột
Tại Bảng Tổng Chỉ Huy (Sidebar) và Bảng Ma Trận Chi Tiết (Main Dashboard), mỗi hạng mục phải thể hiện đủ bộ 3 chỉ số:
1. **TC (Tiêu chuẩn):** Tổng khối lượng cần làm (yy).
2. **TT (Thực tế):** Tổng khối lượng đã xong (xx).
3. **Tiến độ (%):** Con số phần trăm hoàn thành kèm theo thanh Progress Bar trực quan.

## 2. Quy định Định danh cột theo từng Hạng mục (Data Mapping)
Để đối soát chính xác, AI phải sử dụng đúng cột "Khóa" (Key) và cột "Số lượng" (Value) cho từng hạng mục như sau:

| Hạng mục | Cột Định danh (Key) | Cột Giá trị (Value) |
| :--- | :--- | :--- |
| **VẬT TƯ (Ưu tiên & Thường)** | **Tên hàng** | **Số lượng** |
| **CNC (Sản xuất/Cắt)** | **Tên hàng** | **Số lượng** |
| **CAD (Shop)** | **Mã SP** | **Số lượng** |
| **VÁN (Vật tư ván)** | **Mã hiệu** | **Số lượng** |

- **Quy tắc cộng dồn:** AI tìm tất cả các dòng có cùng "Khóa" trong file tương ứng, sau đó cộng tổng (SUM) giá trị tại cột **"Số lượng"**. Tuyệt đối không cộng các cột khác (STT, Kích thước...).

## 3. Logic tính toán và Phân loại hạng mục

| Hạng mục                    | Khối lượng (TT)                      | Hoàn thành (TC)                      | Điều kiện lọc (Filter)                                               |
| :-------------------------- | :----------------------------------- | :----------------------------------- | :------------------------------------------------------------------- |
| **VT ƯU TIÊN (nhóm hàng)**  | Tổng `Tên hàng (Unique)` tại `DMVTN` | Tổng `Tên hàng (Unique)` tại `DMVTN` | Cột **Tên hàng** chứa "sắt, inox, da, vải" HOẶC Ghi chú có "ưu tiên" |
| **VT ƯU TIÊN (khối lượng)** | Tổng `Số lượng` tại `DMVTN`          | Tổng `Số lượng` tại `DMVT`           | Cột **Tên hàng** chứa "sắt, inox, da, vải" HOẶC Ghi chú có "ưu tiên" |
| **VT THƯỜNG (nhóm hàng)**   | Tổng `Tên hàng (Unique)` tại `DMVTN` | Tổng `Số lượng` còn lại              | Các dòng vật tư không thuộc nhóm ưu tiên                             |
| **VT THƯỜNG (Khối lượng)**  | Tổng `Số lượng` tại `DMVTN`          | Tổng `Số lượng` còn lại              | Các dòng vật tư không thuộc nhóm ưu tiên                             |
| **CAD (Shop)**              | Tổng `Số lượng` tại `SHOP TT`        | Tổng `Số lượng` tại `SHOP TC`        | So khớp theo cột **Mã SP**                                           |
| **VÁN (VAT)**               | Tổng `Số lượng` tại `DMVTN-VAN`      | Tổng `Số lượng` tại `DMVT-VAN`       | So khớp theo cột **Mã hiệu**                                         |
| **CNC (Sản xuất)**          | Tổng `Số lượng` tại `CAT`            | Tổng `Số lượng` tại `NESTING`        | So khớp theo cột **Tên hàng**                                        |

## 4. Chỉ số Unique (Mã sản phẩm Duy nhất)
Bên cạnh tổng khối lượng (xx/yy), AI phải tính toán số lượng mã duy nhất dựa trên cột định danh của hạng mục đó:
- **Công thức:** `Số mã đã có TT (Unique) / Tổng số mã có trong TC (Unique)`.
- **Hiển thị:** Ghi trong ngoặc đơn ngay sau số lượng tổng. 
- **Ví dụ:** `110 / 130 (12/15 Mã)`.

## 5. Quy định về Progress Bar (Full-Cell Overlay)
- **Tràn ô (Full-width):** Thanh màu chiếm 100% diện tích chiều rộng và chiều cao của ô.
- **Lớp phủ số % (Text Overlay):** Con số phần trăm hiển thị **đè lên trên** thanh màu và nằm ở chính giữa ô.

### Logic màu sắc động (Dynamic Colors):
- **🔵 Màu Xanh Biển (#1E88E5):** Khi tiến độ đạt chính xác 100%.
- **🟡 Màu Vàng (#FF9800):** Khi tiến độ đang chạy (từ 0% đến 99%).
- **🔴 Màu Đỏ (#F44336):** Cảnh báo lệch pha (Hiện khi ô là 0% nhưng khâu trước đó đã có tiến độ > 0%).
- **⚪ Màu Xám:** Khi tất cả hạng mục trong dòng đều là 0%.

## 6. Hướng dẫn kỹ thuật cho AI (Streamlit)
Sử dụng `st.column_config.ProgressColumn(format="%d%%")`. AI phải lập trình hàm `groupby` linh hoạt:
- Nếu là CAD -> `groupby('Mã SP')`.
- Nếu là Ván -> `groupby('Mã hiệu')`.
- Các loại còn lại -> `groupby('Tên hàng')`.