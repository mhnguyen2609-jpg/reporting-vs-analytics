# Process & Business Logic (ETL) / Quy trình & Logic Nghiệp vụ

## 1. Data Extraction Pipeline / Quy trình Trích xuất Dữ liệu
The system uses a "Context-Aware" scanning strategy to identify and categorize Excel files from unstructured folders.
*Hệ thống sử dụng chiến lược quét "Nhận thức Ngữ cảnh" để nhận diện và phân loại file Excel từ các thư mục không có cấu trúc.*

### Identification Logic (`file_scanner.py`)
Files are identified based on filename keywords and their parent folder context.
*File được nhận diện dựa trên từ khóa trong tên file và ngữ cảnh thư mục cha.*

**Priority Order (Longest Match First) / Thứ tự Ưu tiên (Khớp dài nhất trước):**
1.  **`VAN_NHAP`**: Files containing `DMVTN-VAN`.
2.  **`VAN_XUAT`**: Files containing `DMVT-VAN`, `DMVN-VAN`, or `XUAT` (in VAN context/ngữ cảnh Ván).
3.  **`SHOP_TC`**: Files containing `SHOPT`.
4.  **`SHOP_TT`**: Files containing `SHOP` (without T/không có chữ T).
5.  **`VT_NHAP`**: Files containing `DMVTN`.
6.  **`VT_XUAT`**: Files containing `DMVT` (Default fallback for other exports/Mặc định cho các loại xuất khác).

### Excel Normalization (`excel_parser.py`)
Because user input is unpredictable, the parser uses **Fuzzy Header Detection**:
*Do đầu vào người dùng không dự đoán được, bộ phân tích sử dụng **Nhận diện Header Mờ**:*

-   Scans first 20 rows to find a valid header row containing specific keywords (e.g., "Số lượng", "Mã SP").
    *(Quét 20 dòng đầu để tìm dòng header hợp lệ chứa từ khóa.)*
-   **Column Mapping / Ánh xạ Cột:**
    -   `quantity` <- `['số lượng', 'sl', 'khối lượng', ...]`
    -   `don_vi` <- `['đơn vị', 'dvt', ...]`
    -   `ma_sp` <- `['mã sp', 'model', 'product code', ...]`
    -   `ten_hang` <- `['tên hàng', 'tên vật tư', 'tên sp', ...]`

### Date Extraction Logic (Cell C8) / Logic Trích xuất Ngày (Ô C8)
The system extracts the **Creation Date** from cell **C8** (Row 8, Column C) of every Excel file.
*Hệ thống trích xuất **Ngày lập** từ ô **C8** (Dòng 8, Cột C) của mọi file Excel.*

-   **Input Formats / Định dạng Đầu vào:** Supports `dd/mm/yyyy`, `dd.mm.yyyy`, or `dd-mm-yyyy`.
-   **Normalization / Chuẩn hóa:** All dates are forced to **`dd/mm/yyyy`** format for consistency.
    *(Tất cả ngày tháng được ép về định dạng `dd/mm/yyyy` để nhất quán).*

---

## 2. Smart Caching System (`cache_manager.py`) / Hệ thống Cache Thông minh
To optimize performance on Google Drive (slow I/O), the system implements a **Smart Sync** mechanism.
*Để tối ưu hiệu năng trên Google Drive (tốc độ I/O chậm), hệ thống cài đặt cơ chế **Đồng bộ Thông minh**.*

### The Problem / Vấn đề
-   Scanning thousands of Excel files on Drive takes minutes.
    *(Quét hàng nghìn file Excel trên Drive mất nhiều phút.)*
-   Users need instant access to dashboards.
    *(Người dùng cần truy cập dashboard ngay lập tức.)*

### The Solution: Shared Cache / Giải pháp: Cache Chia sẻ
1.  **Persistence Layer / Lớp Bền vững:**
    -   Metadata & Aggregates are saved to a hidden **Google Sheet** (`CACHE_DB_{YEAR}`) in the Year folder.
        *(Metadata & Tổng hợp được lưu vào **Google Sheet** ẩn trong thư mục Năm.)*
    -   Details (large datasets) are saved as `DETAILS_CACHE_{YEAR}.json` on Drive.
        *(Chi tiết (dữ liệu lớn) được lưu file JSON trên Drive.)*
    -   Timestamps are stored to track file changes.
        *(Lưu dấu thời gian để theo dõi thay đổi file.)*

2.  **Sync Workflow (`load_all_contracts_data_logic`) / Quy trình Đồng bộ:**
    -   **Step 1:** Load Cache (from Local JSON or Google Sheet). *(Tải Cache từ Local hoặc Sheet).*
    -   **Step 2:** Fetch **ModifiedTime** for all contract folders (Batch Request). *(Lấy thời gian sửa đổi của tất cả folder HĐ).*
    -   **Step 3:** Compare `Current Timestamp` vs `Cached Timestamp`. *(So sánh thời gian hiện tại vs cache).*
    -   **Step 4:** **Incremental Reload**: Only re-download and re-process contracts that have changed. *(Tải lại tăng cường: Chỉ tải lại những HĐ có thay đổi).*
    -   **Step 5:** Update Cache and Save back to Drive. *(Cập nhật Cache và lưu lại Drive).*

---

## 3. Data Transformation & Analytics (`calculator.py`)

### Aggregation Rules / Quy tắc Tổng hợp
Dashboard metrics are calculated based on file types (`_source_type`).

| Metric | Source Type (TC - Planned/Kế hoạch) | Source Type (TT - Actual/Thực tế) | Logic |
| :--- | :--- | :--- | :--- |
| **CAD (Shop)** | `SHOP_TC` | `SHOP_TT` | Sum Quantity |
| **CNC (SX)** | `NESTING`, `NHAP` | `CAT`, `XUAT` | Sum Quantity |
| **VÁN** | `VAN_NHAP` | `VAN_XUAT` | Sum Quantity |
| **VẬT TƯ** | `VT_NHAP` | `VT_XUAT` | Count Unique Items (Types/Loại) |

### Matrix Logic / Logic Ma trận
The Matrix View builds a relationship between different production phases for each product.
*View Ma trận xây dựng mối quan hệ giữa các giai đoạn sản xuất cho từng sản phẩm.*

1.  **Master Key:** Union of all `Mã SP` found in any file. *(Tập hợp tất cả Mã SP từ mọi file).*
2.  **Left Join:** The Master Key is used as the backbone. Data from Shop, CNC, and Supplies are joined onto this backbone. *(Dùng Master Key làm xương sống để ghép dữ liệu Shop, CNC, Vật tư).*
3.  **Status Calculation (Delta):**
    -   `Delta = TC - TT`
    -   If `Delta == 0`: **Done** (Blue) *(Hoàn thành)*
    -   If `Delta < 0`: **Extra/In Progress** (Amber - `TT > TC`) *(Đang làm/Vượt)*
    -   If `Delta > 0`: **Missing** (Red - `TT < TC`) *(Thiếu)*

### Material Statistics Logic / Logic Thống kê Vật tư
Aggregates material usage across all products.

1.  **Group By:** `Item Name` (Tên hàng).
2.  **Metrics Calculation:**
    -   **Quantity (Số lượng):** Sum of `Actual Used` (DMVT).
    -   **Remaining (Tồn):** `Plan (DMVTN) - Actual (DMVT)`.
        -   *Note: If item originates from DMVT only (no Plan), Plan=0, so Tồn = -Actual (Negative).*
3.  **Status Determination:**
    -   `Tồn > 0`: **Thiếu (Missing)**. *(Still have plan budget)*.
    -   `Tồn == 0`: **Hoàn thành (Done)**. *(Plan equals Actual)*.

---

## 4. Pre-computation Workflow (Performance Optimization) / Quy trình Tính toán trước
To resolve memory constraints and startup crashes (Segfaults) on Streamlit Cloud, the system supports a **Static Loading Mode**.
*Để giải quyết vấn đề bộ nhớ và lỗi crash khi khởi động trên Cloud, hệ thống hỗ trợ **Chế độ Tải Tĩnh**.*

### Workflow Steps / Các bước thực hiện
1.  **Local Processing (`src/scripts/precompute.py`)**:
    -   Run locally to scan thousands of Excel files. *(Chạy trên máy local để quét hàng ngàn file)*
    -   Uses `load_all_contracts_data_local` logic (Same as Runtime).
    -   Generates 2 JSON artifacts in `data/`:
        -   `master_data_{YEAR}.json`: Aggregated statistics. *(Thống kê tổng hợp)*
        -   `details_data_{YEAR}.json`: Full file list and content for Detail View. *(Danh sách file và nội dung cho View Chi tiết)*

2.  **Deployment (Git Push)**:
    -   Commit these JSON files to the repository. *(Đẩy file JSON lên repo)*

3.  **Cloud Startup (`app.py`)**:
    -   Detects `data/master_data_{YEAR}.json`.
    -   **Bypasses** Google Drive API and Excel Parsing completely. *(Bỏ qua hoàn toàn quét Drive và Excel)*
    -   Loads data instantly into RAM. *(Tải ngay lập tức vào RAM)*

### Benefits / Lợi ích
-   **Zero Crash Risk:** No heavy processing at startup. *(Không lo crash)*
-   **Instant Load:** < 1 second startup time. *(Khởi động < 1s)*
-   **Offline Capable:** Can run without Drive API if JSONs are present. *(Chạy được khi không có mạng)*
