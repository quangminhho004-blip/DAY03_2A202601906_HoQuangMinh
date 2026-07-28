"""
🛠️ TOOL REGISTRY & SCHEMAS (Dành cho Role 2: Tool & Spec Engineer)
Đề tài: Tra Cứu Đơn Hàng & Xử Lý Đổi Trả
Sửa theo đánh giá: Chuẩn hóa dữ liệu, xử lý lỗi, trả về dictionary
"""

import os
import csv
from datetime import datetime

# Đường dẫn đến file dữ liệu
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(BASE_DIR), "data")
ORDERS_FILE = os.path.join(DATA_DIR, "orders.csv")
RETURNS_FILE = os.path.join(DATA_DIR, "returns.csv")
EVENTS_FILE = os.path.join(DATA_DIR, "order_events.csv")


def parse_price(value) -> int:
    """Chuyển đổi giá từ string (có thể có dấu phẩy/chấm) sang int"""
    try:
        cleaned = str(value).replace(",", "").replace(".", "").strip()
        if not cleaned.isdigit():
            return 0
        return int(cleaned)
    except (ValueError, TypeError):
        return 0


def load_orders():
    """
    Đọc dữ liệu đơn hàng từ file CSV.
    Chuẩn hóa order_id: strip + upper case
    """
    orders = {}
    if not os.path.exists(ORDERS_FILE):
        raise FileNotFoundError(f"Không tìm thấy file dữ liệu: {ORDERS_FILE}")
    
    with open(ORDERS_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Chuẩn hóa order_id
            order_id = row.get("order_id", "").strip().upper()
            if order_id:
                orders[order_id] = row
    return orders


def load_returns():
    """Đọc dữ liệu đổi trả từ file CSV"""
    returns = []
    if os.path.exists(RETURNS_FILE):
        with open(RETURNS_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                returns.append(row)
    return returns


def save_return(return_record: dict):
    """Lưu một yêu cầu đổi/trả mới vào file CSV"""
    file_exists = os.path.exists(RETURNS_FILE)
    
    with open(RETURNS_FILE, "a", encoding="utf-8", newline="") as f:
        fieldnames = ["return_id", "order_id", "reason", "status", "refund_amount", "created_at"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader()
        
        writer.writerow(return_record)


def load_order_events(order_id: str = None):
    """Đọc timeline đơn hàng từ file events CSV"""
    events = []
    if not os.path.exists(EVENTS_FILE):
        return events
    
    with open(EVENTS_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if order_id is None or row.get("order_id", "").strip().upper() == order_id.upper():
                events.append(row)
    return events


def get_safe_value(order: dict, key: str, default: str = "") -> str:
    """Lấy giá trị an toàn từ dict, xử lý None"""
    return (order.get(key) or "").strip() or default


def generate_return_id() -> str:
    """Tạo mã yêu cầu đổi/trả mới (RT + số thứ tự)"""
    returns = load_returns()
    if not returns:
        return "RT001"
    
    # Tìm số lớn nhất hiện có
    max_num = 0
    for r in returns:
        rid = r.get("return_id", "")
        if rid.startswith("RT"):
            try:
                num = int(rid[2:])
                max_num = max(max_num, num)
            except ValueError:
                pass
    
    return f"RT{str(max_num + 1).zfill(3)}"


def search_order(order_id: str) -> dict:
    """
    Tra cứu thông tin chi tiết của một đơn hàng.
    
    Args:
        order_id (str): Mã đơn hàng cần tra cứu (VD: 'DH001', 'dh002')
        
    Returns:
        dict: Thông tin đơn hàng hoặc thông báo lỗi
    """
    # Chuẩn hóa order_id
    normalized_order_id = order_id.strip().upper()
    
    try:
        orders = load_orders()
    except FileNotFoundError as exc:
        return {
            "success": False,
            "error_code": "DATA_FILE_NOT_FOUND",
            "message": f"LỖI DỮ LIỆU: {exc}"
        }
    
    order = orders.get(normalized_order_id)
    
    if not order:
        return {
            "success": False,
            "error_code": "ORDER_NOT_FOUND",
            "message": f"Không tìm thấy đơn hàng '{normalized_order_id}'. Vui lòng kiểm tra lại mã đơn hàng."
        }
    
    # Xử lý giá an toàn
    price = parse_price(order.get("price", "0"))
    
    # Xác định delivery date dựa trên file mới hay cũ
    delivery_date = get_safe_value(order, "estimated_delivery_date") or get_safe_value(order, "delivery_date")
    delivered_at = get_safe_value(order, "delivered_at")
    
    return {
        "success": True,
        "order": {
            "order_id": normalized_order_id,
            "product": get_safe_value(order, "product"),
            "price": price,
            "price_display": f"{price:,} VNĐ",
            "status": get_safe_value(order, "status"),
            "order_date": get_safe_value(order, "date"),
            "address": get_safe_value(order, "address"),
            "delivery_date": delivery_date,
            "delivered_at": delivered_at,
            "cancel_reason": get_safe_value(order, "cancel_reason"),
        }
    }


def get_order_status(order_id: str) -> dict:
    """
    Xem chi tiết trạng thái và timeline của đơn hàng.
    Đọc timeline từ file order_events.csv thay vì hardcode.
    
    Args:
        order_id (str): Mã đơn hàng cần kiểm tra (VD: 'DH001')
        
    Returns:
        dict: Timeline chi tiết các bước giao hàng
    """
    normalized_order_id = order_id.strip().upper()
    
    try:
        orders = load_orders()
    except FileNotFoundError as exc:
        return {
            "success": False,
            "error_code": "DATA_FILE_NOT_FOUND",
            "message": f"LỖI DỮ LIỆU: {exc}"
        }
    
    order = orders.get(normalized_order_id)
    
    if not order:
        return {
            "success": False,
            "error_code": "ORDER_NOT_FOUND",
            "message": f"Không tìm thấy đơn hàng '{normalized_order_id}'."
        }
    
    status = get_safe_value(order, "status")
    
    # Thử đọc từ file events trước
    events = load_order_events(normalized_order_id)
    
    if events:
        # Có timeline từ file
        timeline = []
        for event in events:
            icon = "✓" if event.get("event_status") == "completed" else ("→" if event.get("event_status") == "current" else "✗")
            timeline.append({
                "icon": icon,
                "date": event.get("event_date", ""),
                "status": event.get("event_status", ""),
                "description": event.get("description", "")
            })
    else:
        # Fallback: tạo timeline đơn giản từ status
        timeline = generate_fallback_timeline(order)
    
    return {
        "success": True,
        "order_id": normalized_order_id,
        "current_status": status,
        "timeline": timeline
    }


def generate_fallback_timeline(order: dict) -> list:
    """Tạo timeline đơn giản khi không có file events (fallback)"""
    timeline = []
    status = get_safe_value(order, "status")
    order_date = get_safe_value(order, "date")
    delivery_date = get_safe_value(order, "estimated_delivery_date") or get_safe_value(order, "delivery_date")
    delivered_at = get_safe_value(order, "delivered_at")
    
    # Bước 1: Đặt hàng (luôn completed)
    timeline.append({
        "icon": "✓",
        "date": order_date,
        "status": "completed",
        "description": "Đã đặt hàng thành công"
    })
    
    if status == "Đã giao":
        timeline.append({
            "icon": "✓",
            "date": order_date,
            "status": "completed",
            "description": "Đã xác nhận thanh toán"
        })
        if delivery_date:
            timeline.append({
                "icon": "✓",
                "date": f"Trước {delivery_date}",
                "status": "completed",
                "description": "Đơn hàng đang vận chuyển"
            })
        timeline.append({
            "icon": "✓",
            "date": delivered_at or delivery_date,
            "status": "completed",
            "description": "Giao hàng thành công"
        })
    elif status == "Đang giao":
        timeline.append({
            "icon": "✓",
            "date": order_date,
            "status": "completed",
            "description": "Đã xác nhận thanh toán"
        })
        timeline.append({
            "icon": "✓",
            "date": "Hôm nay",
            "status": "completed",
            "description": "Đơn hàng đang được đóng gói"
        })
        timeline.append({
            "icon": "→",
            "date": f"Dự kiến {delivery_date}",
            "status": "current",
            "description": "Giao hàng"
        })
    elif status == "Đang xử lý":
        timeline.append({
            "icon": "→",
            "date": "Đang xử lý",
            "status": "current",
            "description": "Chờ xác nhận thanh toán"
        })
    elif status == "Đã hủy":
        timeline.append({
            "icon": "✗",
            "date": "Đã hủy",
            "status": "cancelled",
            "description": f"Yêu cầu hủy được chấp nhận. Lý do: {get_safe_value(order, 'cancel_reason')}"
        })
    
    return timeline


def process_return(order_id: str, reason: str = "") -> dict:
    """
    Yêu cầu đổi hoặc trả hàng cho đơn đã giao.
    Lưu vào file returns.csv và kiểm tra trùng lặp.
    
    Args:
        order_id (str): Mã đơn hàng cần đổi/trả (VD: 'DH002')
        reason (str): Lý do đổi/trả (VD: 'Size không vừa', 'Sản phẩm lỗi')
        
    Returns:
        dict: Kết quả yêu cầu đổi/trả
    """
    normalized_order_id = order_id.strip().upper()
    reason = (reason or "").strip()
    
    # Validate lý do
    if not reason:
        return {
            "success": False,
            "error_code": "MISSING_REASON",
            "message": "LỖI: Vui lòng cung cấp lý do đổi/trả."
        }
    
    if len(reason) < 5:
        return {
            "success": False,
            "error_code": "REASON_TOO_SHORT",
            "message": "LỖI: Lý do đổi/trả quá ngắn (tối thiểu 5 ký tự)."
        }
    
    try:
        orders = load_orders()
    except FileNotFoundError as exc:
        return {
            "success": False,
            "error_code": "DATA_FILE_NOT_FOUND",
            "message": f"LỖI DỮ LIỆU: {exc}"
        }
    
    order = orders.get(normalized_order_id)
    
    if not order:
        return {
            "success": False,
            "error_code": "ORDER_NOT_FOUND",
            "message": f"Không tìm thấy đơn hàng '{normalized_order_id}'."
        }
    
    status = get_safe_value(order, "status")
    
    # Kiểm tra đơn có đủ điều kiện đổi/trả không
    if status == "Đã giao":
        # Kiểm tra đơn đã có yêu cầu đổi trả chưa
        returns = load_returns()
        existing = [r for r in returns if r.get("order_id", "").strip().upper() == normalized_order_id]
        
        if existing:
            return {
                "success": False,
                "error_code": "ALREADY_RETURNED",
                "message": f"⚠️ Đơn hàng {normalized_order_id} đã có yêu cầu đổi/trả trước đó: {existing[0].get('return_id')}"
            }
        
        # Tạo mã yêu cầu mới
        return_id = generate_return_id()
        price = parse_price(order.get("price", "0"))
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        return_record = {
            "return_id": return_id,
            "order_id": normalized_order_id,
            "reason": reason,
            "status": "pending",
            "refund_amount": str(price),
            "created_at": created_at
        }
        
        # Lưu vào file
        save_return(return_record)
        
        return {
            "success": True,
            "return_id": return_id,
            "order_id": normalized_order_id,
            "product": get_safe_value(order, "product"),
            "refund_amount": price,
            "refund_display": f"{price:,} VNĐ",
            "reason": reason,
            "status": "pending",
            "created_at": created_at,
            "instructions": [
                "1. Đóng gói sản phẩm cùng hóa đơn",
                f"2. Dán mã vận đơn: {return_id}",
                "3. Gửi tại bưu điện gần nhất"
            ],
            "note": "Yêu cầu đã được ghi nhận trong hệ thống mô phỏng. Thời gian hoàn tiền dự kiến: 3-5 ngày làm việc."
        }
    
    elif status == "Đang giao":
        return {
            "success": False,
            "error_code": "ORDER_NOT_DELIVERED",
            "message": f"⚠️ Không thể đổi/trả đơn hàng {normalized_order_id}: Đơn hàng đang trong quá trình giao."
        }
    
    elif status == "Đang xử lý":
        return {
            "success": False,
            "error_code": "ORDER_NOT_DELIVERED",
            "message": f"⚠️ Không thể đổi/trả đơn hàng {normalized_order_id}: Đơn hàng chưa được giao."
        }
    
    elif status == "Đã hủy":
        return {
            "success": False,
            "error_code": "ORDER_CANCELLED",
            "message": f"⚠️ Không thể đổi/trả đơn hàng {normalized_order_id}: Đơn hàng đã bị hủy."
        }
    
    return {
        "success": False,
        "error_code": "UNKNOWN_STATUS",
        "message": f"LỖI: Không xác định được trạng thái đơn hàng {normalized_order_id}."
    }


# Danh sách các tool được đăng ký để Agent sử dụng
AVAILABLE_TOOLS = {
    "search_order": search_order,
    "get_order_status": get_order_status,
    "process_return": process_return,
}
