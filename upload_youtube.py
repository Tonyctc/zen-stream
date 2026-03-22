#!/usr/bin/env python3
"""
YouTube Uploader — Upload videos to YouTube via API.
Requires: google-api-python-client, google-auth-oauthlib

Setup:
  1. Go to https://console.cloud.google.com/
  2. Create project → Enable YouTube Data API v3
  3. Create OAuth 2.0 credentials → Download client_secrets.json
  4. Place client_secrets.json in this directory
  5. First run will open browser for authorization

Usage:
  python3 upload_youtube.py --file video.mp4 --title "My Video"
  python3 upload_youtube.py --file video.mp4 --title "Title" --description "Desc" --tags "tag1,tag2"
  python3 upload_youtube.py --file video.mp4 --preset zen
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime


# ─── Lazy imports (only when actually uploading) ─────────────────────

def get_youtube_service():
    """Authenticate and return YouTube API service."""
    try:
        from googleapiclient.discovery import build
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        import pickle
    except ImportError:
        print("ERROR: Required packages not installed.")
        print("Run: pip install google-api-python-client google-auth-oauthlib")
        sys.exit(1)

    SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
    CLIENT_SECRETS = os.path.join(os.path.dirname(__file__), 'client_secrets.json')
    TOKEN_FILE = os.path.join(os.path.dirname(__file__), 'token.pickle')

    if not os.path.exists(CLIENT_SECRETS):
        print(f"ERROR: {CLIENT_SECRETS} not found.")
        print("Download from Google Cloud Console → APIs → Credentials")
        sys.exit(1)

    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, 'wb') as f:
            pickle.dump(creds, f)

    return build('youtube', 'v3', credentials=creds)


def upload_video(file_path, title, description='', tags='', category_id='10',
                 privacy_status='public', made_for_kids=False, thumbnail=None):
    """Upload a video to YouTube."""
    youtube = get_youtube_service()

    if not os.path.exists(file_path):
        print(f"ERROR: File not found: {file_path}")
        return None

    file_size = os.path.getsize(file_path) / (1024 * 1024)
    print(f"\nUploading: {title}")
    print(f"File: {file_path} ({file_size:.1f} MB)")
    print(f"Privacy: {privacy_status}")

    body = {
        'snippet': {
            'title': title,
            'description': description,
            'tags': [t.strip() for t in tags.split(',') if t.strip()],
            'categoryId': str(category_id),
        },
        'status': {
            'privacyStatus': privacy_status,
            'selfDeclaredMadeForKids': made_for_kids,
        }
    }

    from googleapiclient.http import MediaFileUpload

    media = MediaFileUpload(
        file_path,
        chunksize=1024*1024*10,  # 10MB chunks
        resumable=True,
        mimetype='video/mp4',
    )

    request = youtube.videos().insert(
        part='snippet,status',
        body=body,
        media_body=media,
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            pct = int(status.progress() * 100)
            print(f"  Upload: {pct}%", end='\r', flush=True)

    video_id = response['id']
    url = f'https://youtube.com/watch?v={video_id}'
    print(f"\n  Uploaded: {url}")

    # Upload thumbnail if provided
    if thumbnail and os.path.exists(thumbnail):
        print(f"  Uploading thumbnail...")
        youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(thumbnail),
        ).execute()

    return video_id


# ─── CLI ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='YouTube Video Uploader')
    parser.add_argument('--file', required=True, help='Path to video file')
    parser.add_argument('--title', required=True, help='Video title')
    parser.add_argument('--description', default='', help='Video description')
    parser.add_argument('--tags', default='', help='Comma-separated tags')
    parser.add_argument('--category', default='10', help='YouTube category ID (default: 10 = Music)')
    parser.add_argument('--privacy', default='public',
                        choices=['public', 'private', 'unlisted'])
    parser.add_argument('--thumbnail', default=None, help='Path to thumbnail image')
    parser.add_argument('--preset', default=None,
                        help='Use preset metadata (zen, sleep, focus, aurora, nature)')

    args = parser.parse_args()

    # Apply preset if specified
    if args.preset:
        from zen_stream import PRESETS
        preset = PRESETS.get(args.preset)
        if preset:
            args.title = args.title or preset['title']
            args.description = args.description or preset['description']
            args.tags = args.tags or preset['tags']

    upload_video(
        file_path=args.file,
        title=args.title,
        description=args.description,
        tags=args.tags,
        category_id=args.category,
        privacy_status=args.privacy,
        thumbnail=args.thumbnail,
    )


if __name__ == '__main__':
    main()
