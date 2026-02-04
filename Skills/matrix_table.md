---
name: matrix-table-logic-pro
description: Ma trận chi tiết quy tắc so sánh dữ liệu SHOP, NESTING, DMVT cho toàn bộ hệ thống.
---
---

# 📊 Ma trận Đối soát Matrix: Quy tắc Logic Toàn diện

Bảng Matrix là công cụ đối soát chi tiết theo từng dòng (Mã SP) để phát hiện sai lệch giữa kế hoạch và thực tế sản xuất.

## 1. Công thức tổng quát
Trạng thái tiến độ của từng ô dựa trên Hiệu số Delta ($\Delta$):
$$\Delta = \text{Tiêu chuẩn (TC)} - \text{Thực tế (TT)}$$

## 2. Chi tiết logic từng cột (Mapping dữ liệu)
AI phải truy xuất đúng cặp file và sử dụng logic **Cộng dồn Số lượng** cho tất cả các khâu:

| Hạng mục | File Tiêu chuẩn (TC) | File Thực tế (TT) | Cột Định danh (Key) | Logic xử lý |
| :--- | :--- | :--- | :--- | :--- |
| **A. CAD (Bản vẽ)** | Từ khóa `SHOPT` | Từ khóa `SHOP` | **Mã SP** | **Sum(Số lượng)** |
| **B. CNC (Sản xuất)** | Từ khóa `NESTING` | Từ khóa `CAT` | **Tên hàng** | **Sum(Số lượng)** |
| **C. VẬT TƯ** | Từ khóa `DMVT` | Từ khóa `DMVTN` | **Tên hàng** | **Sum(Số lượng)** |
| **D. VÁN** | Từ khóa `DMVT-VAN` | Từ khóa `DMVTN-VAN`| **Mã hiệu** | **Sum(Số lượng)** |

## 3. Ma trận hiển thị Icon & Màu sắc
Dựa vào giá trị $\Delta$, AI sẽ nhuộm màu và hiển thị Icon cho ô tương ứng:

| Điều kiện         | Icon | Màu sắc                 | Ý nghĩa kỹ thuật                            |
| :---------------- | :--- | :---------------------- | :------------------------------------------ |
| **$\Delta = 0$**  | ✅    | **Xanh Biển (#1E88E5)** | Hoàn thành khớp kế hoạch 100%               |
| **$\Delta > 0$**  | 🔼   | **Vàng (#FF9800)**      | Đang thực hiện (Thực tế < Tiêu chuẩn)       |
| **$\Delta < 0$**  | ❌    | **Đỏ (#F44336)**        | Sai lệch (Thực tế vượt tiêu chuẩn/Sai file) |
| **Thiếu dữ liệu** | ❌    | **Đỏ (#F44336)**        | Mã SP có trong TC nhưng file TT không có    |



## 4. Quy định hiển thị Progress Bar "Tràn Ô"
Để tối ưu giao diện trên thiết bị di động (iPhone), AI phải cấu hình:
- **Full-cell:** Thanh màu phải lấp đầy toàn bộ diện tích ô.
- **Overlay:** Con số phần trăm (%) phải nằm đè lên trên thanh màu và căn giữa.
- **Màu sắc:** Sử dụng mã màu Xanh biển, Vàng, Đỏ như bảng tại Mục 3.

## 5. Xử lý ngoại lệ và Cảnh báo Lệch pha
- **Cảnh báo dây chuyền:** Nếu khâu trước (CAD) đã ✅ mà khâu sau (CNC) vẫn ❌ -> Ô CNC phải hiện nền **Đỏ** rõ rệt để báo hiệu tắc nghẽn sản xuất.
- **Bỏ trống:** Chỉ để trống ô (màu xám) nếu Mã SP đó không tồn tại trong cả file TC và TT của hạng mục đó.

## 6. Hướng dẫn kỹ thuật cho AI
- Sử dụng Pandas: `df.groupby('Cột_Key')['Số lượng'].sum()`.
- Sử dụng Streamlit: `st.column_config.ProgressColumn(format="%d%%")`.