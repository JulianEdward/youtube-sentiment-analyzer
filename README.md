# YouTube Comment Sentiment Analyzer

Extracts comments from YouTube videos and analyzes sentiment using TextBlob (fast) or Hugging Face (accurate).

## How It Works

1. User enters a YouTube URL or uploads a JSON file
2. Backend extracts all comments (or reads from JSON)
3. Each comment is analyzed for sentiment (positive/negative/neutral) and polarity score
4. Results are displayed with statistics and a sortable table
5. Data can be exported as JSON

## Installation

### 1. Create and activate virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

### 2. Install requirements

```bash
pip install -r requirements.txt
```

### 3. Create `.env` file

```
YOUTUBE_API_KEY=your_youtube_api_key_here
DEBUG=True # false by default
```

### 4. Run the application

```bash
python app.py
```

### 5. Open browser

Navigate to `http://localhost:5000`

## requirements.txt

```
Flask>=2.0.0
google-api-python-client>=2.108.0
python-dotenv>=1.0.0
textblob>=0.17.0
transformers>=4.35.0
torch>=2.0.0
```

## Getting a YouTube API Key

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable **YouTube Data API v3**
4. Go to **Credentials** → **Create API Key**
5. Copy the key into `.env`

## Usage

- **TextBlob mode**: Faster, lexicon-based. Good for large comment volumes.
- **Hugging Face mode**: Slower, AI-powered. Better for nuanced/sarcastic comments.

Supports YouTube URLs and JSON file uploads