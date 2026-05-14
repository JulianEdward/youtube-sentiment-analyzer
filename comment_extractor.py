import os
import re
from dotenv import load_dotenv

try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    print("Install: pip install google-api-python-client")

load_dotenv()

class YouTubeCommentExtractor:
    def __init__(self):
        self.youtube_api_key = os.getenv('YOUTUBE_API_KEY')
        if not self.youtube_api_key:
            raise ValueError("YouTube API key not found in .env file")
    
    def extract_video_id(self, url):
        if 'youtu.be' in url:
            video_id = url.split('/')[-1].split('?')[0]
        elif 'youtube.com' in url:
            if 'v=' in url:
                video_id = url.split('v=')[1].split('&')[0]
            elif '/shorts/' in url:
                video_id = url.split('/shorts/')[1].split('?')[0]
            else:
                video_id = None
        else:
            video_id = None
        
        if not video_id:
            raise ValueError(f"Could not extract video ID from URL: {url}")
        
        return video_id
    
    def extract_all_comments(self, url):
        video_id = self.extract_video_id(url)
        
        try:
            youtube = build('youtube', 'v3', developerKey=self.youtube_api_key)
            comments = []
            next_page_token = None
            
            while True:
                request = youtube.commentThreads().list(
                    part='snippet',
                    videoId=video_id,
                    maxResults=100,
                    pageToken=next_page_token,
                    textFormat='plainText'
                )
                response = request.execute()
                
                for item in response['items']:
                    comment = item['snippet']['topLevelComment']['snippet']
                    
                    text = comment.get('textDisplay', '')
                    text = re.sub(r'<[^>]+>', '', text)
                    text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
                    
                    author = comment.get('authorDisplayName', 'Anonymous')
                    if not author or author.strip() == '':
                        author = 'Anonymous'
                    
                    if len(text.split()) >= 5:
                        comments.append({
                            'author': author,
                            'comment': text
                        })
                
                next_page_token = response.get('nextPageToken')
                if not next_page_token:
                    break
            
            return comments
            
        except HttpError as e:
            print(f"YouTube API Error: {e}")
            return []