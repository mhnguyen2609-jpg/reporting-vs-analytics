
from src.utils.drive_adapter import GoogleDriveClient

def setup_auth():
    print("=======================================")
    print("   THIẾT LẬP XÁC THỰC GOOGLE DRIVE")
    print("=======================================")
    print("1. Hãy chắc chắn bạn đã có file 'client_secret.json' trong thư mục này.")
    print("   (Tải từ Google Cloud Console -> Credentials -> Create OAuth Client ID -> Desktop App)")
    print("2. Script sẽ mở trình duyệt để bạn đăng nhập.")
    print("3. Sau khi đăng nhập, file 'token.pickle' sẽ được tạo.")
    print("=======================================")
    
    input("Nhấn Enter để bắt đầu...")
    
    # Force interactive login
    client = GoogleDriveClient(token_path='token.pickle', credentials_path='dummy.json')
    
    if client.creds and client.creds.valid:
        print("\n✅ Tạo Token thành công! File 'token.pickle' đã được lưu.")
        print("Bây giờ bạn có thể chạy lại App.")
    else:
        print("\n❌ Tạo Token thất bại. Kiểm tra lại 'client_secret.json'.")

if __name__ == "__main__":
    setup_auth()
