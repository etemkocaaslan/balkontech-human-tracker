import os
import subprocess

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

# TODO this tokens only last ~1 hour so we need to get new ones and update token for the tester
ACCESS_TOKEN = "ya29.a0ARGnu0ZwJJF5YNJOo2SgQfF29btOu-FTclQpjVE-GjDfa9Q9rVyCHd50Oyx1WaVRNCXERyDgBKNSAgl5yM8kBJOOED3XigyFSXHOEkkzjDbQV7he4kg1fSfx3lry8-6B150Eq-GeZPfVWEkpAZQ6ywM8pUm6Q1A5Zp2gw24dSO1E0j_x6wnHdPOrgHY2R1qw08opLkYaCgYKAZMSARQSFQHGX2MiK4KPGZs3y10EkB0B3Ra4Zw0206"
UPLOAD_FOLDER_ID = "1BlgZfNqyEK833po8EAxqsuPbhjg5HJ4t"

# Ortak repo kokune gore file_id'yi yazacagimiz dosya (client ve server ayni repo altinda oldugu icin)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
LAST_FILE_ID_PATH = os.path.join(REPO_ROOT, "last_file_id.txt")


def convert_to_mp4(file_path):
    """
    Converts any video file to mp4 using ffmpeg.
    Returns the path to the converted file.
    """
    base_name, _ = os.path.splitext(file_path)
    output_path = f"{base_name}_converted.mp4"

    if file_path.lower().endswith(".mp4"):
        print(f"File {file_path} is already an MP4. Skipping conversion.")
        return file_path

    print(f"Converting {file_path} to MP4 format...")
    
    # FFmpeg komutunu dinamik olarak olusturuyoruz
    command = ["ffmpeg"]
    
    # ASF dosyalari icindeki HEVC (H265) kodekleri FFmpeg tarafindan otomatik taninmayabilir.
    # Bu yuzden eger dosya .asf ise, girdiden once okuyucuya bunun hevc oldugunu soyluyoruz.
    if file_path.lower().endswith(".asf"):
        command.extend(["-c:v", "hevc"])
        
    command.extend([
        "-i", file_path,
        "-c:v", "libx264",  # Ciktitaki video formati (Genis uyumluluk icin H264)
        "-c:a", "aac",      # Ciktitaki ses formati
        "-strict", "experimental",
        "-y",               # Overwrite output file without asking
        output_path
    ])

    try:
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"Conversion successful: {output_path}")
        return output_path
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg conversion failed: {e.stderr.decode('utf-8')}")
        return None
    except FileNotFoundError:
        print("FFmpeg is not installed or not found in the system PATH.")
        return None


def upload_video_resumable(file_path, file_name=None):
    """
    Uploads a video to Google Drive and returns the file ID.
    """
    creds = Credentials(token=ACCESS_TOKEN)

    try:
        service = build("drive", "v3", credentials=creds)

        file_metadata = {
            "name": file_name or os.path.basename(file_path),
            "parents": [UPLOAD_FOLDER_ID],
        }

        media = MediaFileUpload(
            file_path,
            mimetype="video/mp4",
            resumable=True,
            chunksize=1024 * 1024 * 5,
        )

        print(f"Starting upload for {file_path}...")
        request = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id",
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"Uploaded {int(status.progress() * 100)}%")

        file_id = response.get("id")
        print(f'File with ID: "{file_id}" has been uploaded.')
        return file_id

    except HttpError as error:
        print(f"An error occurred during upload: {error}")
        return None


if __name__ == "__main__":
    # Define the input file path (change the extension to test conversion, e.g., .avi, .mkv)
    # TODO make this dynamic when user uploads the file get the path from there
    input_video_path = "../../video.mp4"

    # 1. Convert the video (if necessary)
    converted_video_path = convert_to_mp4(input_video_path)

    if converted_video_path:
        # 2. Upload the converted video
        uploaded_file_id = upload_video_resumable(converted_video_path)

        if uploaded_file_id:
            # file_id'yi ortak dosyaya yaz, download.py otomatik oradan okuyacak
            with open(LAST_FILE_ID_PATH, "w") as f:
                f.write(uploaded_file_id)
            print(f"UPLOADED_FILE_ID={uploaded_file_id}")
            print(f"file_id kaydedildi: {LAST_FILE_ID_PATH}")
        else:
            print("Upload failed.")
    else:
        print("Conversion failed. Skipping upload.")