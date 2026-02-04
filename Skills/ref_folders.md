# 📁 Reference: Folder Structure
Hệ thống quản lý dữ liệu sản xuất phân cấp theo Năm và Hợp đồng.

## Sơ đồ cây mục tiêu
- **Gốc:** `D:\Cong viec`
- **Level 1:** Năm (Ví dụ: `2024`, `2025`)
- **Level 2:** Mã hợp đồng (`STT. Mã hợp đồng_Tên khách hàng`)
- **Level 3:** Thư mục chức năng (`VT`, `CNC`, `DMVT`, `SHOP`, `NHAP`, `XUAT`)



## Chiến lược quét file (Scanning)
- Sử dụng cơ chế quét đệ quy (recursive) tìm file `.xlsx`.
- Bỏ qua các file tạm có dấu `~$`.
- Metadata (Năm, Tên hợp đồng) phải được trích xuất từ đường dẫn file và thêm thành cột trong DataFrame.