# System Architecture & Directory Structure / Kiến trúc Hệ thống & Cấu trúc Thư mục

## 1. High-Level Architecture / Tổng quan Kiến trúc
The project follows a **Modularized ETL (Extract-Transform-Load)** pattern integrated into a Streamlit application.
*Dự án tuân theo mô hình **ETL (Extract-Transform-Load) module hóa**, được tích hợp vào ứng dụng Streamlit.*

-   **Frontend (UI):** Streamlit-based Dashboard with custom HTML/CSS components.
    *(Dashboard dựa trên Streamlit với các component HTML/CSS tùy chỉnh.)*
-   **Backend (Core):** Python logic for Data Aggregation (`calculator`), Caching (`cache_manager`), and Configuration.
    *(Logic Python xử lý Tổng hợp dữ liệu (`calculator`), Quản lý bộ nhớ đệm (`cache_manager`), và Cấu hình.)*
-   **Infrastructure (Utils):** Connectors for Google Drive API and Local File System.
    *(Kết nối API Google Drive và Hệ thống tệp tin nội bộ.)*

## 2. Directory Structure / Cấu trúc Thư mục

```text
project/
├── app.py                      # [Entry Point] Main Streamlit Application (Controller/View) / Điểm nhập chính (Điều khiển/Giao diện)
├── Skills/                     # [Documentation] Technical Specifications & Knowledge Base / Tài liệu kỹ thuật & Kho kiến thức
├── src/
│   ├── core/                   # [Business Logic] Domain-specific logic / Logic nghiệp vụ
│   │   ├── cache_manager.py    # [New] Smart Caching System (Local + Drive Sync) / Hệ thống Cache thông minh
│   │   ├── calculator.py       # Data Analysis, Aggregation, & Matrix Building / Phân tích & Tổng hợp dữ liệu
│   │   ├── config_loader.py    # Configuration Management / Quản lý cấu hình
│   │   └── constants.py        # Global Constants & Regex Patterns / Hằng số & Biểu thức chính quy
│   ├── ui/                     # [Presentation Layer] UI Components & Design System / Giao diện & Thiết kế
│   │   ├── components.py       # HTML rendering functions (Master Table, Matrix Grid) / Hàm render HTML
│   │   └── design.py           # [New] Centralized Design System (Colors, Icons, Fonts) / Hệ thống thiết kế tập trung
│   └── utils/                  # [Infrastructure] Low-level utilities / Tiện ích hạ tầng
│       ├── drive_adapter.py    # [New] Google Drive API Wrapper (v3) & Sheets API (v4) / Wrapper API Drive & Sheets
│       ├── excel_parser.py     # Fault-tolerant Excel Reader & Normalizer / Bộ đọc Excel chịu lỗi
│       ├── file_scanner.py     # Recursive File Scanning & Type Identification / Quét file đệ quy
│       └── helpers.py          # Generic helpers (e.g., natural sort) / Tiện ích chung
└── credentials.json            # (Ignored) Google Service Account Credentials / Thông tin xác thực Google (Được bỏ qua)
```

## 3. Module Responsibilities / Trách nhiệm Module

### A. Core Modules (`src/core`)
-   **`cache_manager.py`**: The "Brain" of data loading. / *"Bộ não" của việc tải dữ liệu.*
    -   Manages **Shared Cache** (accessible by all users via Google Drive/Sheets).
        *(Quản lý **Shared Cache** - truy cập bởi mọi user qua Google Drive/Sheets.)*
    -   Implements **Smart Reloading**: Checks modification timestamps on Drive to only reload changed contracts.
        *(Thực hiện **Smart Reloading**: Kiểm tra thời gian sửa đổi trên Drive để chỉ tải lại các hợp đồng có thay đổi.)*
    -   Handles **Dual-Layer Caching**: `st.session_state` (Memory) -> Local JSON (Speed) -> Google Sheets (Persistence).
        *(Xử lý **Cache 2 lớp**: Memory -> Local JSON (Tốc độ) -> Google Sheets (Bền vững).)*

-   **`calculator.py`**: The "Engine" of data processing. / *"Động cơ" xử lý dữ liệu.*
    -   `calculate_aggregates()`: Computes TC/TT/Percent for dashboards.
        *(Tính toán TC/TT/Phần trăm cho dashboard.)*
    -   `build_matrix_table()`: Joins data from multiple sources to create the Matrix view.
        *(Ghép nối dữ liệu từ nhiều nguồn để tạo view Ma trận.)*
    -   `get_all_product_details()`: Flattens detailed row data for UI expansion.
        *(Làm phẳng dữ liệu chi tiết để mở rộng trên UI.)*

### B. UI Modules (`src/ui`)
-   **`design.py`**: Single source of truth for UI styling. / *Nguồn duy nhất cho style giao diện.*
    -   Defines `Colors` (Blue/Amber/Grey), `Icons` (✔/✖/➚), and `Fonts`.
        *(Định nghĩa Màu sắc, Icon và Font chữ.)*
    -   Generates CSS for complex components.
        *(Tạo CSS cho các component phức tạp.)*
    
-   **`components.py`**: Rendering logic. / *Logic hiển thị.*
    -   `render_master_table_html()`: Injects HTML table for the Project Overview.
        *(Chèn bảng HTML cho Tổng quan Dự án.)*
    -   `render_matrix_grids_html()`: Generates the Responsive Grid layout for products.
        *(Tạo layout Grid phản hồi cho sản phẩm.)*

### C. Infrastructure Modules (`src/utils`)
-   **`drive_adapter.py`**: Robust Google Drive Client. / *Client Google Drive mạnh mẽ.*
    -   Handles Authentication (Service Account / OAuth / Secrets).
        *(Xử lý xác thực.)*
    -   Abstracts Drive v3 and Sheets v4 API calls.
        *(Trừu tượng hóa các gọi API Drive v3 và Sheets v4.)*
    -   Supports Batch Requests for fetching metadata efficiently.
        *(Hỗ trợ Batch Request để lấy metadata hiệu quả.)*

-   **`file_scanner.py` & `excel_parser.py`**:
    -   Implements the "Fuzzy Logic" for identifying file types and normalizing Excel headers (as described in Process documentation).
        *(Thực hiện "Logic Mờ" để nhận diện loại file và chuẩn hóa header Excel.)*
