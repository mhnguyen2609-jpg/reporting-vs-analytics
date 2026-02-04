import os

# Default root path for project scanning
DEFAULT_ROOT_PATH = r"D:\Cong viec"

# File extensions to scan
EXCEL_EXTENSIONS = ['.xlsx', '.xls']

# Keywords for source type identification (Mapping from ref_naming.md)
# Key: Source Type (Internal Identifier), Value: Tuple of keywords to search in filename
# Priority: Checks are done in order, so more specific keywords should come first if overlaps exist ? 
# Actually ref_naming says "Prioritize longer keywords".
# We will implement logic to check longer matches first in the scanner.
NamingKeywords = {
    'VAN_NHAP': ['DMVTN-VAN'],
    'VAN_XUAT': ['DMVT-VAN', 'DMVN-VAN'],
    'VT_NHAP': ['DMVTN'], # Checks for DMVTN but NOT DMVTN-VAN (requires exclusion logic or order presedence)
    'VT_XUAT': ['DMVT'],  # Checks for DMVT but NOT DMVT-VAN
    'SHOP_TC': ['SHOPT'],
    'SHOP_TT': ['SHOP'],  # Checks for SHOP but NOT SHOPT
    'NESTING_TC': ['NESTING'],
    'CAT_TT': ['CAT']
}
