---
name: project-master-skill
description: Tài liệu kỹ thuật tổng hợp (Hub) về Kiến trúc, Quy trình và Giao diện hệ thống. (System Architecture, Process & UI Documentation Hub)
---

# PROJECT MASTER SKILL DOCUMENTATION

## 📚 Documentation Hub / Trung tâm Tài liệu

This document serves as the entry point for the project's technical specifications. The documentation has been split into three focused modules for better maintainability.
*Tài liệu này đóng vai trò là điểm truy cập cho các thông số kỹ thuật của dự án. Tài liệu đã được chia thành 3 module chuyên biệt để dễ bảo trì.*

### 1. [System Architecture / Kiến trúc Hệ thống](structure.md)
> **Ref:** `Skills/structure.md`
>
> Detailed breakdown of the **Directory Structure**, **Module Responsibilities**, and external integrations.
> *Chi tiết về **Cấu trúc Thư mục**, **Trách nhiệm Module**, và tích hợp bên ngoài.*
>
> - **Core:** `cache_manager.py`, `calculator.py`
> - **UI:** `design.py`, `components.py`
> - **Utils:** `drive_adapter.py`

### 2. [Process & ETL Logic / Quy trình & Logic ETL](process.md)
> **Ref:** `Skills/process.md`
>
> Deep dive into how data flows through the system.
> *Đi sâu vào cách dữ liệu lưu thông trong hệ thống.*
>
> - **File Scanning:** Recursive identification strategy. *(Chiến lược nhận diện đệ quy)*
> - **Excel Parsing:** Fuzzy header detection and error handling. *(Nhận diện header mờ và xử lý lỗi)*
> - **Smart Cache:** The dual-layer caching mechanism (Local + Google Drive). *(Cơ chế Cache 2 lớp)*
> - **Analytics:** Formulas for TC/TT calculation and Matrix logic. *(Công thức tính toán TC/TT và Matrix)*

### 3. [User Interface & Visualization / Giao diện & Trực quan hóa](ui.md)
> **Ref:** `Skills/ui.md`
>
> Specification of the frontend components.
> *Thông số kỹ thuật các component giao diện.*
>
> - **Design System:** Palette, Typography, and Icons. *(Hệ thống thiết kế)*
> - **Component Implementation:** Custom HTML/CSS for Master Table and Matrix Grids.
> - **Interactivity:** JavaScript logic for expandable rows.

---

## 🛠 Quick Reference (Common Tasks) / Tham khảo Nhanh

### How to add a new File Type? / Cách thêm Loại File mới?
1.  **Identify:** Add keyword to `process.md` rules and `constants.py`.
    *(Thêm từ khóa vào rule và constants.py)*
2.  **Process:** Add aggregation logic in `calculator.py`.
    *(Thêm logic tổng hợp trong calculator.py)*
3.  **Display:** Update `components.py` to render the new category.
    *(Cập nhật components.py để hiển thị danh mục mới)*

### How to debug "Data Not Loading"? / Cách sửa lỗi "Không tải được dữ liệu"?
1.  Check **Drive Adapter** logs in the terminal.
    *(Kiểm tra log Drive Adapter trong terminal)*
2.  Verify **Cache Consistency**: Delete `cache/*.json` to force a full reload.
    *(Kiểm tra tính nhất quán Cache: Xóa cache/*.json để buộc tải lại)*
3.  Check **File Keywords**: Ensure files match the naming conventions in `process.md`.
    *(Kiểm tra Từ khóa File: Đảm bảo file đúng quy ước đặt tên)*

### How to update UI Colors? / Cách cập nhật Màu giao diện?
1.  Edit `src/ui/design.py`.
2.  The central `Colors` class controls all component styles.
    *(Class Colors trung tâm quản lý toàn bộ style component)*
