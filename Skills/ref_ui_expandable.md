---
name: expandable-row-interaction
description: Logic hiển thị bảng chi tiết chèn ngay bên dưới dòng được chọn.
---

# Logic hiển thị chèn dòng (Inline Expansion)

Hệ thống phải tạo không gian để hiển thị chi tiết sản phẩm ngay bên dưới dòng hợp đồng khi người dùng click vào.

## 1. Cơ chế thực hiện
- Sử dụng `st.expander` cho mỗi dòng Hợp đồng.
- Khi mở Expander, các dòng phía dưới tự động đẩy xuống để nhường chỗ cho bảng chi tiết.



## 2. Nội dung bên trong Expander
- Hiển thị bảng chi tiết gồm các cột: `Mã SP`, `ĐẶT`, `VẬT`, `VAT`, `CAD`, `CNC`.
- Các ô trạng thái (ĐẶT, VẬT, VAT, CAD, CNC) phải được định dạng theo `matrix_table.md`.

## 3. Cấu trúc Code gợi ý
```python
for contract_id in list_contracts:
    with st.expander(f" {contract_id}"):
        df_detail = get_data_for_contract(contract_id)
        st.dataframe(df_detail.style.apply(matrix_logic))