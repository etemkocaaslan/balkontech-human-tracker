import os
import subprocess

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from get_credentials import get_credentials

UPLOAD_FOLDER_ID = "1BlgZfNqyEK833po8EAxqsuPbhjg5HJ4t"


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

    command = ["ffmpeg"]

    if file_path.lower().endswith(".asf"):
        command.extend(["-c:v", "hevc"])

    command.extend([
        "-i", file_path,
        "-c:v", "libx264",
        "-c:a", "aac",
        "-strict", "experimental",
        "-y",
        output_path,
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


def upload_video_resumable(file_path, file_name=None, on_progress=None):
    """
    Uploads a video to Google Drive and returns the file ID.

    Args:
        file_path: Local path to the video file.
        file_name: Display name on Drive (defaults to basename).
        on_progress: Optional callback(int percentage) for progress updates.
    """
    creds = get_credentials()

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

        request = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id",
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                pct = int(status.progress() * 100)
                if on_progress is not None:
                    on_progress(pct)
                print(f"Uploaded {pct}%")

        file_id = response.get("id")
        print(f'File with ID: "{file_id}" has been uploaded.')
        return file_id

    except HttpError as error:
        print(f"An error occurred during upload: {error}")
        return None


if __name__ == "__main__":
    input_video_path = "../../video.mp4"

    converted_video_path = convert_to_mp4(input_video_path)

    if converted_video_path:
        uploaded_file_id = upload_video_resumable(converted_video_path)

        if uploaded_file_id:
            print(f"UPLOADED_FILE_ID={uploaded_file_id}")
        else:
            print("Upload failed.")
    else:
        print("Conversion failed. Skipping upload.")