import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# Google Drive'a dosya yükleme yetkisi
SCOPES = ["https://www.googleapis.com/auth/drive.file"]

# Dosya yolları (Senin belirttiğin tam yollar)
BASE_DIR = "/home/halil/repos/balkontech-human-tracker"
CREDENTIALS_PATH = os.path.join(BASE_DIR, "credentials.json")
TOKEN_PATH = os.path.join(BASE_DIR, "token.json")

def get_credentials():
    """
    Google Drive API için gerekli yetkileri alır. 
    Süresi dolduysa otomatik yeniler (refresh token).
    """
    creds = None

    # token.json dosyası daha önceden alınmış erişim (access) ve yenileme (refresh) token'larını saklar.
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    
    # Geçerli bir token yoksa (ilk çalışma) veya süresi dolmuşsa yeni token al
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Token süresi dolmuş, otomatik yenileniyor...")
            creds.refresh(Request())
        else:
            print("Tarayıcı açılıyor, lütfen Google hesabınızla giriş yapıp izin verin...")
            # credentials.json dosyasından flow oluştur
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Gelecekteki kullanımlar için token'ı kaydet
        with open(TOKEN_PATH, "w") as token:
            token.write(creds.to_json())
            
    return creds

if __name__ == "__main__":
    # Sadece bu dosyayı çalıştırarak yetkilendirmenin çalışıp çalışmadığını test edebilirsin
    credentials = get_credentials()
    if credentials and credentials.valid:
        print("Yetkilendirme başarılı! token.json oluşturuldu/güncellendi.")
    else:
        print("Yetkilendirme başarısız oldu.")