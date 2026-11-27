from lib.config import Config

_TRANSLATIONS = {
    "en": {
        # LCD
        "lcd_connecting_wifi": "Connecting to {ssid}...",
        "lcd_syncing_time": "Syncing time...",
        "lcd_syncing_info": "Syncing info...",
        "lcd_advertise_at": "Advertise at",
        "lcd_generating_qr": "Generating QR...",
        "lcd_qr_failed": "Failed to load QR!",
        "lcd_time_items_status": "Time  | Items | Status",
        "lcd_no_schedules": "No schedules",
        # Status
        "status_pending": "pending",
        "status_processing": "processing",
        "status_completed": "completed",
        "status_failed": "failed",
        # BLE
        "ble_wifi_success": "WiFi connected and saved!",
        "ble_wifi_failed": "Could not connect to WiFi '{ssid}'!",
        "ble_general_saved": "General config saved!",
        "ble_timeout_saved": "Timeout config saved!",
        "ble_config_error": "Config error: {error}",
        # Notify
        "notify_required_failures": "Dispense finished with {count} required failure(s).",
        "notify_schedule_failed": "Schedule failed",
        "notify_drop_failed": "Drop failed",
        "notify_medicine_not_taken": "Medicine not taken",
        "notify_untaken": "Untaken medicine detected! User did not take pills.",
        "notify_optional_failures": "Medicine taken, but {count} optional item(s) failed to drop.",
        "notify_schedule_warning": "Schedule completed with warning",
        "notify_drop_warning": "Drop completed with warning",
        "notify_success": "Medicine schedule cycle completed successfully!",
        "notify_schedule_completed": "Schedule completed",
        "notify_drop_completed": "Drop completed",
        # Emit
        "emit_sync_info_received": "Sync info command received",
        "emit_sync_info_success": "Sync info command success!",
        "emit_sync_info_failed": "Sync info command failed!",
        "emit_sync_schedule_received": "Sync schedule command received",
        "emit_sync_schedule_success": "Sync schedule command success!",
        "emit_sync_schedule_failed": "Sync schedule command failed!",
        "emit_drop_received": "Drop command received",
        "emit_drop_success": "Drop command success!",
        "emit_drop_failed": "Drop command failed!",
    },
    "vi": {
        # LCD
        "lcd_connecting_wifi": "Dang ket noi {ssid}...",
        "lcd_syncing_time": "Dang dong bo thoi gian...",
        "lcd_syncing_info": "Dang dong bo thong tin...",
        "lcd_advertise_at": "Dia chi BLE",
        "lcd_generating_qr": "Dang tao ma QR...",
        "lcd_qr_failed": "Khong the tai ma QR!",
        "lcd_time_items_status": "Gio   | Thuoc | TThai",
        "lcd_no_schedules": "Khong co lich",
        # Status
        "status_pending": "cho",
        "status_processing": "dang chay",
        "status_completed": "xong",
        "status_failed": "loi",
        # BLE
        "ble_wifi_success": "Da ket noi va luu WiFi!",
        "ble_wifi_failed": "Khong the ket noi WiFi '{ssid}'!",
        "ble_general_saved": "Da luu cau hinh chung!",
        "ble_timeout_saved": "Da luu cau hinh timeout!",
        "ble_config_error": "Loi cau hinh: {error}",
        # Notify
        "notify_required_failures": "Hoàn tất phát thuốc nhưng có {count} mục bắt buộc thất bại.",
        "notify_schedule_failed": "Lịch phát thuốc thất bại",
        "notify_drop_failed": "Phát thuốc thất bại",
        "notify_medicine_not_taken": "Thuốc chưa được lấy",
        "notify_untaken": "Phát hiện thuốc chưa được lấy! Người dùng chưa lấy thuốc.",
        "notify_optional_failures": "Đã lấy thuốc, nhưng có {count} mục không bắt buộc không phát được.",
        "notify_schedule_warning": "Lịch phát thuốc hoàn tất nhưng có cảnh báo",
        "notify_drop_warning": "Phát thuốc hoàn tất nhưng có cảnh báo",
        "notify_success": "Chu trình phát thuốc đã hoàn tất thành công!",
        "notify_schedule_completed": "Lịch phát thuốc đã hoàn tất",
        "notify_drop_completed": "Phát thuốc đã hoàn tất",
        # Emit
        "emit_sync_info_received": "Đã nhận lệnh đồng bộ thông tin",
        "emit_sync_info_success": "Đồng bộ thông tin thành công!",
        "emit_sync_info_failed": "Đồng bộ thông tin thất bại!",
        "emit_sync_schedule_received": "Đã nhận lệnh đồng bộ lịch",
        "emit_sync_schedule_success": "Đồng bộ lịch thành công!",
        "emit_sync_schedule_failed": "Đồng bộ lịch thất bại!",
        "emit_drop_received": "Đã nhận lệnh phát thuốc",
        "emit_drop_success": "Phát thuốc thành công!",
        "emit_drop_failed": "Phát thuốc thất bại!",
    },
}


def translate(key: str, **values) -> str:
    """Translate a message using the configured language.

    Args:
        key: Translation key.
        **values: Optional values used to format the translated message.

    Returns:
        Translated and formatted message. Falls back to English if the
        configured language or translation key is unavailable.
    """
    language = Config().general.get("language", "en")
    translations = _TRANSLATIONS.get(language, _TRANSLATIONS["en"])
    message = translations.get(key, _TRANSLATIONS["en"].get(key, key))
    return message.format(**values) if values else message
