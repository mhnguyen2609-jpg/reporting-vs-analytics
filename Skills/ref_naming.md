# Reference: Naming & Labeling
Dựa vào từ khóa trong tên file để gán cột `source_type`.

| Từ khóa trong tên file | Nhãn (Source_Type) |
| :--- | :--- |
| `DMVTN-VAN` | `VAN_NHAP` |
| `DMVT-VAN` | `VAN_XUAT` |
| `DMVTN` (không có VAN) | `VT_NHAP` |
| `DMVT` (không có VAN) | `VT_XUAT` |
| `SHOPT` | `SHOP_TC` (Tiêu chuẩn) |
| `SHOP` (không có T) | `SHOP_TT` (Thực tế) |
| `NESTING` | `NESTING_TC` |
| `CAT` | `CAT_TT` |

**Lưu ý:** Ưu tiên nhãn có từ khóa dài hơn nếu trùng lặp (ví dụ: `DMVTN-VAN` phải là Ván nhập, không phải Vật tư nhập).