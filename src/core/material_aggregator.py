from typing import Dict, List
import pandas as pd

def aggregate_materials_by_name(all_details_map: Dict[str, List[Dict]]) -> pd.DataFrame:
    """
    Aggregates details by 'item_name' to create a Material Statistics summary.
    
    Args:
        all_details_map: Dict { 'product_code': [ {item_data}, ... ] }
        
    Returns:
        DataFrame with columns: [STT, Tên hàng, Số lượng, Đơn vị, Mã SP - Tên SP]
    """
    material_groups = {}
    
    for prod_code, items in all_details_map.items():
        # Get product name from first item if available, or just use prod_code lookup if passed separately.
        # But here items usually contain 'product_name'.
        prod_name = ""
        if items:
            prod_name = items[0].get('product_name', '')
            
        full_prod_label = f"{prod_code} - {prod_name}" if prod_name else prod_code
        
        for item in items:
            item_name = item.get('item_name', '').strip()
            if not item_name: continue
            
            # Key by (item_name, unit) to separate if units differ? 
            # Request purely says "Tên hàng", implies merging regardless of unit? 
            # Usually units should match for name. Let's group by name.
            # But if units differ, summing quantity is dangerous. 
            # Let's key by (item_name, unit) for safety.
            unit = item.get('unit', '').strip()
            key = (item_name, unit)
            
            if key not in material_groups:
                material_groups[key] = {
                    'item_name': item_name,
                    'quantity': 0,
                    'remaining': 0,
                    'unit': unit,
                    'related_products': set()
                }
            
            # Add quantity
            qty = item.get('quantity', 0)
            try:
                # Handle string quantities if present (though calculator.py tries to keep them numeric)
                if isinstance(qty, str): 
                     # Clean string
                     qty = float(qty.replace(',', '.')) if qty.replace(',', '.').replace('.', '', 1).isdigit() else 0
                material_groups[key]['quantity'] += float(qty)
            except:
                pass
                
            # Add remaining
            rem = item.get('remaining', 0)
            try:
                if isinstance(rem, str):
                    rem = float(rem.replace(',', '.')) if rem.replace(',', '.').replace('.', '', 1).isdigit() else 0
                material_groups[key]['remaining'] += float(rem)
            except:
                pass
                
            # Add related product
            material_groups[key]['related_products'].add(full_prod_label)
            
    # Convert to List
    rows = []
    for idx, (key, data) in enumerate(sorted(material_groups.items()), 1):
        rem_val = data.get('remaining', 0)
        
        # Determine Status
        status = "Hoàn thành"
        if rem_val > 0.001: # Use epsilon for float comparison
             status = "Thiếu"
        elif rem_val < -0.001:
             status = "Phát sinh" # Changed from "Dư"
             
        rows.append({
            'Tên hàng': data['item_name'],
            'Số lượng': round(data['quantity'], 2), # Round for clean display
            'Tồn': round(rem_val, 2),
            'Đơn vị': data['unit'],
            'Mã SP - Tên SP': sorted(list(data['related_products'])),
            'Trạng thái': status
        })
        
    # Create DF
    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=['Tên hàng', 'Số lượng', 'Tồn', 'Đơn vị', 'Trạng thái', 'Mã SP - Tên SP'])
        
    # Add STT check is done in UI or here? UI is better for display index.
    # Return DF
    return df
