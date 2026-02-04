---
name: project-identity-config-xlsx
description: Quy định về file config.xlsx để định danh Tên khách hàng và Mã hợp đồng.
---
---

# Reference: Định danh Dự án (Config từ Cột Excel)

Hệ thống sẽ không dựa vào tên folder để nhận diện. AI bắt buộc phải mở file `config.xlsx` trong folder đã chọn để lấy thông tin định danh chính xác theo từng cột.

## 1. Cấu trúc bảng tính `config.xlsx`
AI sẽ tìm kiếm và đọc dữ liệu tại các cột có tiêu đề (Header) tương ứng:

| Tiêu đề cột (Header) | Nội dung cần lấy |
| :--- | :--- |
| **Mã hợp đồng** | Lấy giá trị ở dòng dữ liệu đầu tiên (Ví dụ: `HD2026-001`) |
| **Tên khách hàng** | Lấy giá trị ở dòng dữ liệu đầu tiên (Ví dụ: `Nguyễn Văn A`) |

> **Lưu ý:** AI phải nhận diện theo tên cột, không quan trọng cột đó nằm ở vị trí A, B hay C trong file Excel.



## 2. Quy trình trích xuất thông tin
1. **Tìm kiếm:** Sau khi người dùng chọn folder, AI tìm file có tên `config.xlsx`.
2. **Truy vấn:** Sử dụng `pandas` để lọc đúng cột "Mã hợp đồng" và "Tên khách hàng".
3. **Hiển thị:** - Đưa thông tin này lên Header của Dashboard.
    - Dùng thông tin này để đặt tên file khi **Xuất PDF**.
4. **Cảnh báo:** Nếu file `config.xlsx` không có đúng tên cột như quy định, AI phải báo lỗi ngay: *"Không tìm thấy cột 'Mã hợp đồng' hoặc 'Tên khách hàng' trong file config.xlsx"*.

## 3. Tích hợp mở rộng
Ngoài 2 cột chính, file này có thể chứa thêm cột:
- **Ghi chú chung:** Để hiển thị các cảnh báo đặc biệt (ví dụ: "Hàng gấp", "Cẩn thận vận chuyển").

## 4. Hướng dẫn lập trình cho AI
```python
# Logic mẫu để AI đọc dữ liệu
import pandas as pd

df_config = pd.read_excel('config.xlsx')
ma_hd = df_config['Mã hợp đồng'].iloc[0]
ten_kh = df_config['Tên khách hàng'].iloc[0]