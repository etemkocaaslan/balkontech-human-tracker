import io
import os
import sys

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2.credentials import Credentials

# TODO: Auth refactoring is out of scope for this task.
# The token needs to be refreshed periodically. Use environment variable or
# proper OAuth flow for production.
ACCESS_TOKEN = os.environ.get(
    "GOOGLE_DRIVE_ACCESS_TOKEN",
    "ya29.a0ARGnu0ZwJJF5YNJOo2SgQfF29btOu-FTclQpjVE-GjDfa9Q9rVyCHd50Oyx"
    "1WaVRNCXERyDgBKNSAgl5yM8kBJOOED3XigyFSXHOEkkzjDbQV7he4kg1fSfx3lry8"
    "-6B150Eq-GeZPfVWEkpAZQ6ywM8pUm6Q1A5Zp2gw24dSO1E0j_x6wnHdPOrgHY2R1qw"
    "08opLkYaCgYKAZMSARQSFQHGX2MiK4KPGZs3y10EkB0B3Ra4Zw0206",
)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
DOWNLOAD_DIR = os.path.join(PROJECT_ROOT, "storage", "videos")

UPLOAD_FOLDER_ID = "1BlgZfNqyEK833po8EAxqsuPbhjg5HJ4t"


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
    if len(sys.argv) < 2:
        print(f"Usage: python download.py <file_id> [output_name]")
        sys.exit(1)

    file_id = sys.argv[1]
    file_name = sys.argv[2] if len(sys.argv) > 2 else f"downloaded_{file_id}.mp4"

    downloaded_path = download_file(real_file_id=file_id, file_name=file_name)

    if downloaded_path:
        print(f"Download complete: {downloaded_path}")
    else:
        print("Download failed.")