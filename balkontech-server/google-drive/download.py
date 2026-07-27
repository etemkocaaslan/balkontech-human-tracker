import io
import os
import sys

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2.credentials import Credentials

# TODO this tokens only last ~1 hour so we need to get new ones and update token for the tester
ACCESS_TOKEN = "ya29.a0ARGnu0ZwJJF5YNJOo2SgQfF29btOu-FTclQpjVE-GjDfa9Q9rVyCHd50Oyx1WaVRNCXERyDgBKNSAgl5yM8kBJOOED3XigyFSXHOEkkzjDbQV7he4kg1fSfx3lry8-6B150Eq-GeZPfVWEkpAZQ6ywM8pUm6Q1A5Zp2gw24dSO1E0j_x6wnHdPOrgHY2R1qw08opLkYaCgYKAZMSARQSFQHGX2MiK4KPGZs3y10EkB0B3Ra4Zw0206"
DOWNLOAD_DIR = "../../balkontech-server/storage/videos"

# Ortak repo kokune gore upload.py'nin yazdigi file_id dosyasi (ayni repo altinda oldugu icin)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
LAST_FILE_ID_PATH = os.path.join(REPO_ROOT, "last_file_id.txt")


def download_file(real_file_id, file_name="downloaded_video.mp4"):
    """
    Downloads a file from Drive and writes it to DOWNLOAD_DIR.
    """
    creds = Credentials(token=ACCESS_TOKEN)

    try:
        service = build("drive", "v3", credentials=creds)

        # pylint: disable=maybe-no-member
        request = service.files().get_media(fileId=real_file_id)
        file_buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(file_buffer, request)

        print(f"Starting download for file ID: {real_file_id}...")
        done = False
        while not done:
            status, done = downloader.next_chunk()
            if status:
                print(f"Downloaded {int(status.progress() * 100)}%")

        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
        output_path = os.path.join(DOWNLOAD_DIR, file_name)

        with open(output_path, "wb") as f:
            f.write(file_buffer.getvalue())

        print(f"File saved to: {output_path}")
        return output_path

    except HttpError as error:
        print(f"An error occurred during download: {error}")
        return None


if __name__ == "__main__":
    # Once komut satirindan file_id verilmis mi diye bak, verilmemisse
    # upload.py'nin yazdigi ortak dosyadan otomatik oku
    if len(sys.argv) >= 2:
        file_id = sys.argv[1]
    else:
        if not os.path.exists(LAST_FILE_ID_PATH):
            print(f"file_id verilmedi ve {LAST_FILE_ID_PATH} bulunamadi. Once upload.py calistirilmali.")
            sys.exit(1)
        with open(LAST_FILE_ID_PATH, "r") as f:
            file_id = f.read().strip()
            
        # Dosya bossa programi durdur (Guvenlik amaciyla)
        if not file_id:
            print(f"HATA: {LAST_FILE_ID_PATH} dosyasi bos! Lutfen once upload islemini yapin.")
            sys.exit(1)
            
        print(f"file_id otomatik okundu: {file_id}")

    file_name = sys.argv[2] if len(sys.argv) > 2 else f"downloaded_{file_id}.mp4"

    # Indirme islemini baslat ve sonuc yolunu al
    downloaded_path = download_file(real_file_id=file_id, file_name=file_name)

    # Eger indirme basarili olduysa txt dosyasinin ICINI temizle (dosyayi silme)
    if downloaded_path and os.path.exists(LAST_FILE_ID_PATH):
        with open(LAST_FILE_ID_PATH, "w") as f:
            pass  # Dosyayi yazma modunda acip hicbir sey yazmadan kapatinca ici temizlenir
        print(f"Temizlik yapildi: '{LAST_FILE_ID_PATH}' dosyasinin ici bosaltildi.")