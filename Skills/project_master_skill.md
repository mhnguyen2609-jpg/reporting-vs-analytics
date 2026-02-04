---
name: project-master-skill
description: Tài liệu kỹ thuật chuyên sâu (Deep Dive) về Kiến trúc, Logic và Luồng dữ liệu của hệ thống.
---

# PROJECT MASTER SKILL DOCUMENTATION (Deep Technical Specification)

## 1. System Architecture Overview
Dự án được thiết kế theo mô hình **ETL (Extract - Transform - Load)** đơn giản hóa, tích hợp trực tiếp vào **Streamlit UI**.
- **Extract (Scanner/Parser):** Quét file hệ thống, nhận diện loại file, trích xuất dữ liệu thô từ Excel.
- **Transform (Calculator):** Làm sạch, chuẩn hóa, tính toán tổng hợp (Aggregates) và xây dựng bảng quan hệ (Matrix).
- **Load/Visualize (App):** Hiển thị dữ liệu lên giao diện Dashboard tương tác.

### Directory Structure & Responsibilities
```text
project/
├── app.py                      # [Controller/View] Main entry point, UI rendering, State Management
├── Skills/                     # [Documentation] Technical specs & Knowledge base
└── src/
    ├── core/
    │   ├── calculator.py       # [Model/Logic] Core Business Logic, Data Aggregation, Matrix Building
    │   └── constants.py        # [Config] Global constants, Regex patterns, File keywords
    └── utils/
        ├── file_scanner.py     # [Infra] File System IO, File Type Identification Strategy
        └── excel_parser.py     # [Infra] Excel Driver, Schema Normalization, Fault Tolerance
```

---

## 2. Deep Dive: Data Extraction Layer

### 2.1. File Scanning Strategy (`src/utils/file_scanner.py`)
Hệ thống sử dụng cơ chế quét đệ quy (Recursive Scan) kết hợp nhận diện ngữ cảnh (Context-aware Identification).

- **Algorithm:**
  1. Input: Root Directory (e.g., `D:\Cong viec`).
  2. Traverse: `os.walk` qua toàn bộ cây thư mục.
  3. Filter: Chỉ chấp nhận extension `.xlsx`, `.xls` (bỏ qua `~$...`).
  4. Identification: Gọi `identify_source_type(filename, folder_name)`.

- **Identification Logic (Priority Order):**
  Hệ thống so khớp từ khóa theo độ dài giảm dần (Longest Match First) để tránh nhận diện nhầm.
  1. **`VAN_NHAP`**: Chứa `DMVTN-VAN` (Ưu tiên cao nhất)
  2. **`VAN_XUAT`**: Chứa `DMVT-VAN` hoặc `DMVN-VAN` hoặc `XUAT` trong folder context.
  3. **`SHOP_TC`**: Chứa `SHOPT`
  4. **`SHOP_TT`**: Chứa `SHOP` (Nếu không có T)
  5. **`VT_NHAP`**: Chứa `DMVTN`
  6. **`VT_XUAT`**: Chứa `DMVT` (Fallback nếu không phải VAN)
  
  *Context Rule:* Nếu filename match `VT_NHAP` nhưng folder cha là `XUAT` -> Override thành `VT_XUAT`.

### 2.2. Excel Parsing Strategy (`src/utils/excel_parser.py`)
Parser được thiết kế để chịu lỗi (Fault Tolerant) với cấu trúc Excel không ổn định của con người.

- **Dynamic Header Detection (`find_header_row`):**
  - Không giả định header ở dòng 1.
  - Quét 20 dòng đầu tiên.
  - Dòng được coi là header nếu chứa ít nhất **2 từ khóa**: `['số lượng', 'tên hàng', 'mã sp', 'mã hiệu', 'stt', 'khối lượng']`.

- **Column Normalization (`normalize_columns`):**
  Mapping mờ (Fuzzy Mapping) các tên cột về chuẩn nội bộ (Internal Schema):
  - `quantity` (float) <-- `['số lượng', 'sl', 'quantity', 'soluong', 'khối lượng']`
  - `don_vi` (str) <-- `['đơn vị', 'don vi', 'unit', 'dvt']`
  - `ma_sp` (str) <-- `['mã sp', 'mã sản phẩm', 'model', 'product code', 'key']`
  - `ten_hang` (str) <-- `['tên hàng', 'tên vật tư', 'tên sản phẩm', 'item name']`
  - `ma_hieu` (str) <-- `['mã hiệu', 'ký hiệu', 'code']`

- **Critical Data Fixes:**
  - **SHOP File Anomaly:** Phát hiện file SHOP thường để trống cột `Số lượng` (NaN).
  - **Fix Logic:** `if 'SHOP' in source_type and (quantity == 0 or NaN) -> quantity = 1`.

---

## 3. Deep Dive: Transformation Layer (Business Logic)

### 3.1. Standardized Data Schema
Mọi file Excel sau khi parse đều được chuyển về DataFrame với schema chuẩn:
```python
{
    'key': str,           # Khóa chính (Mã SP / Tên Hàng / Mã Hiệu) tùy loại nguồn
    'quantity': float,    # Số lượng chuẩn hóa
    'don_vi': str,        # Đơn vị tính
    'ten_hang': str,      # Tên hiển thị
    'ghi_chu': str,       # Note
    '_source_type': str,  # Meta: Nguồn (SHOPT, DMVT...)
    '_file_path': str     # Meta: Đường dẫn gốc
}
```

### 3.2. Aggregation Logic (`calculate_aggregates`)
Tính toán chỉ số **TC (Tiêu Chuẩn/Kế Hoạch)** và **TT (Thực Tế)** cho Dashboard tổng quan.

- **CAD Aggregation:**
  - `TC = SUM(quantity)` where type=`SHOP_TC`, group by `Mã SP`.
  - `TT = SUM(quantity)` where type=`SHOP_TT`, group by `Mã SP`.
  
- **VẬT TƯ Aggregation (Complex):**
  - **Filter Ưu Tiên:** Check `item_name` chứa: `['sắt', 'inox', 'da', 'nỉ', 'đệm', 'đá', 'vải', 'ưu tiên']`.
  - **Logic Nhóm Hàng:** Đếm `COUNT(DISTINCT item_name)` thay vì SUM quantity.
  - **Logic Khối Lượng:** `SUM(quantity)`.
  
- **Logic Tính %:**
  - `Percent = (TT / TC) * 100`.
  - Nếu `TC = 0`: % = 0 (tránh chia cho 0).

### 3.3. Matrix Building Logic (`build_matrix_table`)
Xây dựng bảng quan hệ phức tạp, kết nối các giai đoạn sản xuất.

1.  **Master Key Generation:**
    - Tập hợp tất cả `key` từ tất cả các file nguồn (Union Set).
    - Đảm bảo không bỏ sót sản phẩm nào dù chỉ xuất hiện ở 1 giai đoạn.

2.  **Product Name Resolution (`_build_ten_sp_map`):**
    - Vì `Mã SP` giống nhau nhưng `Tên SP` có thể bị gõ sai/khác nhau ở các file.
    - **Strategy:** Lấy tên theo độ tin cậy nguồn:
      1. `SHOP_TT` (Chính xác nhất - đã duyệt).
      2. `SHOP_TC` (Kế hoạch).
      3. `VT_NHAP` (Fallback).
      4. `VT_XUAT` (Last resort).

3.  **Column Assembly (Joins):**
    - Sử dụng `Left Join` từ Master Key vào từng bảng dữ liệu (CAD, CNC, VT...).
    - `fillna(0)` cho các giá trị thiếu.

---

## 4. Deep Dive: Visualization Layer (UI/UX)

### A. Bảng Tổng Quan (Master Table)
Streamlit native table không đủ linh hoạt, dự án sử dụng **Custom HTML injection** (`st.components.v1.html`).

- **Master Table (`render_master_table_html`):** (Giao diện: **Bảng Tổng Quan**)
  - **Layout:** Table với `rowspan` (gộp dòng) phức tạp cho cột Contract.
  - **Visuals:** CSS Gradient Progress Bar trực tiếp trong cell `<td>`.
  - **Color Coding:**
    - `#1E88E5` (Blue): Completed (100%).
    - `#FF9800` (Amber): In Progress (0-99%).
    - `#374151` (Grey): Not Started (0%).

#### 📌 Master Table Process & Analytics
Phần này mô tả chi tiết quy trình xử lý và logic phân tích số liệu cho Bảng Tổng Quan.

**1. Data Processing Pipeline (ETL)**
Quy trình từ file Excel đến khi hiển thị lên bảng gồm 4 bước:

*   **Step 1: Loop Contracts** (`app.py:load_all_contracts_data`)
    *   Hệ thống duyệt qua từng Hợp đồng trong năm đã chọn.
    *   Với mỗi hợp đồng, gọi Scanner để lấy danh sách toàn bộ file liên quan.

*   **Step 2: Aggregation** (`calculator.py:calculate_aggregates`)
    *   Tính toán tổng hợp cho 5 hạng mục: `CAD`, `CNC`, `VAN`, `VAT_TU`, `VAT_TU_UU_TIEN`.
    *   Mỗi hạng mục trả về: `{ TC, TT, percent, nhom_hang_tc, ... }`.

*   **Step 3: Flattening**
    *   Chuyển mảng đa chiều thành List of Dict phẳng để dễ render.
    *   Mỗi hợp đồng sinh ra 5 dicts (tương ứng 5 hạng mục) trong list `all_rows`.

*   **Step 4: Rendering** (`app.py:render_master_table_html`)
    *   Loop qua List phẳng, group lại theo Contract.
    *   Tạo HTML Table với 7 dòng cố định cho mỗi Contract:
        *   Row 1: CAD
        *   Row 2: CNC
        *   Row 3: VÁN
        *   Row 4-5: VẬT TƯ (Dòng 1: Nhóm hàng, Dòng 2: Số lượng)
        *   Row 6-7: VẬT TƯ ƯU TIÊN (Dòng 1: Nhóm hàng, Dòng 2: Số lượng)

**2. Analytics Formulary**
Các công thức tính toán chỉ số hiển thị trên bảng:

| Hạng mục | Chỉ số | Công thức Analytic | Ý nghĩa |
| :--- | :--- | :--- | :--- |
| **CAD / CNC / VÁN** | **TC** | `SUM(quantity)` của file Kế hoạch (SHOPT/NESTING/NHAP) | Tổng khối lượng phải làm |
| | **TT** | `SUM(quantity)` của file Thực tế (SHOP/CAT/XUAT) | Khối lượng đã hoàn thành |
| | **%** | `(TT / TC) * 100` | Tiến độ thực hiện |
| **VẬT TƯ (Tất cả)** | **Nhóm hàng (Row 1)** | `COUNT(DISTINCT item_name)` | Số đầu mục vật tư (Đã nhập bao nhiêu loại) |
| | **Số lượng (Row 2)** | `SUM(quantity)` | Tổng số cái/kg/m (Đã nhập bao nhiêu cái) |
| **Progress Color** | **Màu sắc** | `If % >= 100: Blue` <br> `If 0 < % < 100: Amber` <br> `If % == 0: Grey` | Trạng thái trực quan |

- **Matrix Grid (`render_matrix_grids_html`):**
  - **Layout:** CSS Grid Layout chia cột động (Responsive).
  - **Rotated Headers:** Sử dụng `writing-mode: vertical-rl` và `transform: rotate(180deg)` để tiết kiệm không gian ngang.
  - **Status Icons:** Logic hiển thị icon dựa trên `Delta = TC - TT`.

#### 📌 Matrix Grid Process & Analytics
Phần này mô tả quy trình xây dựng Bảng Ma trận sản phẩm chi tiết.

**1. Data Processing Pipeline**
*   **Step 1: Master Key Generation** (`calculator.py:build_matrix_table`)
    *   Thu thập tất cả `Key` từ mọi nguồn dữ liệu (SHOP, NESTING, DMVTN, DMVT).
    *   Tạo danh sách `Unique Keys` (Index của DataFrame).

*   **Step 2: Column Building (Joins)**
    *   Thực hiện Left Join từ Index vào từng DataFrame con:
        *   `CAD_TC / CAD_TT` (Join theo Key).
        *   `CNC_TC / CNC_TT` (Join theo Key).
        *   `VAT_TU_TC / TT` (Join theo Key + Filter Priority/Normal).
    *   Fill `0` cho các ô trống (NaN).

*   **Step 3: Rendering Grid** (`app.py:render_matrix_grids_html`)
    *   Chia danh sách sản phẩm thành các nhóm (Groups) để hiển thị dạng Grid nhiều cột.
    *   Mỗi ô (Cell) sẽ tính toán Delta và chọn Icon/Màu sắc tương ứng.

**2. Analytics Formulary**
Logic xác định trạng thái của từng ô trong Matrix:

| Chỉ số | Công thức | Icon | Màu sắc | Ý nghĩa |
| :--- | :--- | :--- | :--- | :--- |
| **Delta** | `TC - TT` | | | Độ lệch giữa Kế hoạch và Thực tế |
| **Status** | `Delta == 0` | ✔ (Check) | **Blue** `#1E88E5` | Hoàn thành khớp 100% |
| | `Delta < 0` | ➚ (Arrow) | **Amber** `#FFEB3B` | Vượt kế hoạch hoặc Đang làm (TT > TC) |
| | `Delta > 0` | ✖ (Cross) | **Red** `#F44336` | Chưa hoàn thành hoặc Thiếu (TT < TC) |

---

### C. Timeline - Theo dõi Mốc Thời gian

- **File:** `app.py` -> `render_timeline_html`
- **Mục đích:** Theo dõi mốc thời gian quan trọng và tiến độ Shop/Ván/SX/VT tại thời điểm đó.

#### 📌 Timeline Process & Analytics

**1. Data Processing**
*   Timeline không lưu trữ trong Excel mà là **State-based** (giả lập hoặc lưu trong session hiện tại).
*   Các mốc (Milestones) được thêm thủ công từ giao diện.

**2. Analytics Display**
Mỗi mốc trên Timeline hiển thị kèm snapshot tiến độ tổng quan:

| Thông số | Công thức hiển thị | Ví dụ |
| :--- | :--- | :--- |
| **Shop duyệt** | `aggregated_data['CAD']['TT']` / `['TC']` | `67/67` |
| **Ván** | `aggregated_data['VAN']['TT']` / `['TC']` | `4900/4947` |
| **Sản xuất** | `aggregated_data['CNC']['TT']` / `['TC']` | `1500/2488` |
| **Vật tư** | `aggregated_data['VAT_TU']['TT']` / `['TC']` | `200/0` |

---

### D. Deep Dive: State Management (`st.session_state`)
Quản lý trạng thái phiên làm việc để tránh load lại dữ liệu nặng.
- `master_data`: Cache dữ liệu tổng hợp toàn bộ dự án (List of Dict).
- `selected_year`: Cache năm đang chọn.
- `selected_contract`: Cache hợp đồng đang active.

---

## 5. Maintenance & Troubleshooting Guide

### Common Issues
1.  **Lỗi "0 Quantity":**
    - *Triệu chứng:* CAD/Ván hiện 0 dù file có dữ liệu.
    - *Nguyên nhân:* File Excel viết sai cột hoặc parse nhầm header.
    - *Fix:* Check `excel_parser.config` hoặc logic override `quantity=1`.

2.  **Lỗi Unicode/Encoding:**
    - *Triệu chứng:* Tên file/folder bị lỗi font khi in ra console.
    - *Fix:* Hệ thống Python mặc định CP1252 trên Windows, cần force UTF-8 (đã xử lý trong Scripts).

3.  **Lỗi Nhầm Loại File:**
    - *Triệu chứng:* File `DMVT` bị nhận thành `DMVT-VAN`.
    - *Fix:* Điều chỉnh thứ tự ưu tiên trong `NamingKeywords` (`src/core/constants.py`).

### Extension Points
- **Thêm Loại File Mới:**
  1. Thêm từ khóa vào `NamingKeywords` (`constants.py`).
  2. Định nghĩa logic tính toán `categories` (`calculator.py`).
  3. Cập nhật UI render (`app.py`).

- **Thêm Cột Mới trong Matrix:**
  1. Update `build_matrix_table` để trích xuất cột mới.
  2. Update `render_matrix_grids_html` để hiển thị cột mới trong HTML.
