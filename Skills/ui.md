# User Interface & Visualization / Giao diện Người dùng & Trực quan hóa

## 1. Design System (`src/ui/design.py`) / Hệ thống Thiết kế
The project enforces a centralized design system to ensure consistency.
*Dự án áp dụng hệ thống thiết kế tập trung để đảm bảo tính nhất quán.*

### Color Palette / Bảng màu
-   **Status Colors / Màu Trạng thái:**
    -   `STATUS_DONE` (#1E88E5 - Blue): Completed / Matches Plan. *(Hoàn thành / Khớp KH)*
    -   `STATUS_MISSING` (#FF0000 - Red): Behind Schedule / Missing. *(Chậm tiến độ / Thiếu)*
    -   `STATUS_EXTRA` (#CC5500 - Orange): Ahead of Schedule / In Progress. *(Vượt KH / Đang làm)*
-   **Theme Colors / Màu Chủ đề:**
    -   Dark Mode oriented (`#0f172a`, `#1e3a5f`). *(Hướng Dark Mode)*
    -   Text: Low contrast variations (`#cbd5e1`, `#e2e8f0`). *(Text tương phản thấp)*

### Icons / Biểu tượng
-   **Check (`✔`)**: Completed. *(Hoàn thành)*
-   **Cross (`✖`)**: Missing. *(Thiếu)*
-   **Arrow (`➚`)**: Extra/Over-delivery. *(Vượt/Dư)*

---

## 2. UI Components (`src/ui/components.py`)

### A. Master Overview Table / Bảng Tổng quan
A custom HTML component rendered via `st.components.v1.html` to bypass Streamlit's native table limitations.
*Component HTML tùy chỉnh được render qua `st.components.v1.html` để vượt qua giới hạn của bảng Streamlit gốc.*

-   **Columns & Dimensions / Cột & Kích thước:**
    -   `Code/Name` (Column 1): **20%**
    -   `Category` (Column 2-3): **25%**
    -   `Volume` (Column 4): **15%**
    -   `Complete` (Column 5): **15%**
    -   `Progress %` (Column 6): **12%**
    -   *(Note: Remaining ~13% buffer for spacing/padding).*
    -   **Row Height:** `min-height: 28px` per category row.

#### Layout Structure / Cấu trúc Bố cục
The table uses the `rowspan` technique to group multiple rows under a single Contract.
*Bảng sử dụng kỹ thuật `rowspan` để nhóm nhiều dòng dưới một Hợp đồng.*

**Grid Arrangement (7 Rows per Contract) / Sắp xếp Lưới (7 Dòng mỗi HĐ):**
1.  **Row 1:** `Contract Cell (Rowspan=7)` | `CAD` | `Values...`
2.  **Row 2:** `CNC` | `Values...`
3.  **Row 3:** `VAN` | `Values...`
4.  **Row 4:** `VẬT TƯ (Rowspan=2)` | `Nhóm hàng` | `Values...`
5.  **Row 5:** `Số lượng` | `Values...`
6.  **Row 6:** `VẬT TƯ ƯU TIÊN (Rowspan=2)` | `Nhóm hàng` | `Values...`
7.  **Row 7:** `Số lượng` | `Values...`

#### Visual Techniques / Kỹ thuật Hiển thị
-   **Sticky Header:** `position: sticky; top: 0;` keeps headers visible while scrolling. *(Giữ header cố định khi cuộn).*
-   **In-Cell Progress Bar / Thanh Tiến độ trong ô:**
    -   Implemented using a wrapper `div` (`position: relative`) and a fill `div` (`position: absolute; left: 0;`).
    -   Allows text ("50%") to overlay the color bar clearly using `z-index`.
    -   *(Thực hiện bằng thẻ `div` lồng nhau với `absolute positioning`, cho phép text đè lên thanh màu).*
-   **Empty State (No Data) / Trạng thái Trống:**
    -   Cells with no data (`TC == 0`) are rendered with a **Diagonal Cross Pattern** (X).
    -   **CSS:** Uses `linear-gradient` to draw two crossing lines (to top right + to top left).
    -   *(Các ô không có dữ liệu được hiển thị với họa tiết **Gạch chéo** (dấu X) tạo bởi gradient CSS).*

### B. Matrix Grid View / Grid Ma trận
A responsive, high-density grid used to visualize thousands of products.
*Grid mật độ cao, phản hồi nhanh, dùng để hiển thị hàng nghìn sản phẩm.*

#### CSS Grid Layout / Bố cục CSS Grid
Instead of a standard table, we use `display: grid` for pixel-perfect control.
*Thay vì dùng bảng thường, sử dụng `display: grid` để kiểm soát chính xác từng pixel.*

-   **Column Definition / Định nghĩa Cột:**
    -   `90px`: **Product Code** (Mã SP) - *Unique identifier for the product model.*
    -   `220px`: **Product Name** (Tên SP) - *Descriptive name of the product.*
    -   **5 Status Columns (32px each) / 5 Cột Trạng thái:**
        1.  **CAD:** Technical Drawings (Bản vẽ kỹ thuật).
        2.  **Order (ĐẶT HÀNG):** Customer order status.
        3.  **CNC:** Manufacturing status (Cắt/Gia công).
        4.  **Priority (Vật tư ưu tiên):** High-priority materials (e.g., Fabric, Leather).
        5.  **Supplies (Vật tư):** General materials/hardware.
    -   *(Total Fixed Width / Tổng chiều rộng cố định: ~470px).*

#### Vertical Headers / Header Xoay dọc
To save horizontal space for status columns (which only contain icons), headers are rotated.
*Để tiết kiệm không gian ngang cho các cột trạng thái (chỉ chứa icon), header được xoay dọc.*
-   **CSS:** `writing-mode: vertical-rl; transform: rotate(180deg);`
-   **Height:** `70px` fixed height to accommodate rotated text.
-   **Result:** Headers read bottom-to-top, fitting narrow 32px columns. *(Kết quả: Header đọc từ dưới lên, vừa vặn cột 32px).*

#### Expandable Details / Chi tiết Mở rộng (Inline Expansion)
-   **Interaction:** JavaScript `onclick` event on the product row. *(Sự kiện click JS).*
-   **Detail Table Dimensions & Descriptions / Kích thước & Mô tả Bảng Chi tiết:**
    -   `90px`: **Code (Mã)** - *Product Model Code.*
    -   `Auto`: **Name (Tên)** - *Full Product Name.*
    -   `Auto`: **Item Name (Tên Hàng)** - *Specific material or component name.*
    -   `60px`: **Qty (Số lượng)** - *Required quantity.*
    -   `50px`: **Remain (Tồn)** - *Remaining/Stock quantity.*
    -   `55px`: **Unit (Đơn vị)** - *Unit of measurement (cái, kg, m, etc.).*
    -   `100px`: **Creation Date (Ngày Lập DS)** - *When the list was created.*
    -   `100px`: **Completion (Hoàn Thành)** - *Date of completion.*
    -   `85px`: **Status (Trạng thái)** - *Current status (e.g., Hoàn thành, Thiếu).*
    -   `100px`: **Note (Ghi chú)** - *Additional remarks or warnings.*
-   **Mechanism:**
    1.  User clicks a row.
    2.  JS finds the hidden `div` immediately following the row.
    3.  Toggles `display: none` -> `display: block`.
    4.  Injects a full-width HTML Table containing detailed items (Quantity, Unit, Note).
    *(Cơ chế: JS tìm div ẩn bên dưới dòng, bật hiển thị và chèn bảng chi tiết đầy đủ).*

### C. Timeline / Dòng thời gian
Visualizes production milestones.
*Trực quan hóa các mốc sản xuất.*

-   **Layout Strategy:** "Snake" Layout (Xương cá).
-   **CSS Implementation:**
    -   Central Line: Absolute positioned `div` at `top: 50%`.
    -   **Alternating Items:**
        -   **Even Items (Chẵn):** `bottom: 50%` (Above line / Trên dòng kẻ).
        -   **Odd Items (Lẻ):** `top: 50%` (Below line / Dưới dòng kẻ).

---

## 3. Transparent UI Design / Thiết kế Giao diện Trong suốt

To enhance the modern look and feel, background colors for major data components have been removed.
*Để tăng vẻ hiện đại, các màu nền của các thành phần dữ liệu chính đã được loại bỏ.*

### Implementation Details / Chi tiết Triển khai
-   **CSS Strategy:** Use `background: transparent` and `rgba(255,255,255,0.1)` borders.
    *(Chiến lược CSS: Sử dụng nền trong suốt và viền trắng mờ 10%).*
-   **Affected Components:**
    -   **Master Table:** Header and Body backgrounds removed.
    -   **Timeline:** Container and Card backgrounds set to transparent.
    -   **Matrix Grid:** Product rows and Detail rows are transparent.
    -   **Material Stats:** Table background removed.
-   **Global Override:** Streamlit's default dataframe style is overridden via injected CSS:
    ```css
    [data-testid="stDataFrame"] { background-color: transparent !important; }
    ```
