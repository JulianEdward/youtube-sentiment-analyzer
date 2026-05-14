import re

try:
    from textblob import TextBlob
    TEXTBLOB_AVAILABLE = True
except ImportError:
    TEXTBLOB_AVAILABLE = False

try:
    from transformers import pipeline
    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False

class SentimentAnalyzer:
    def __init__(self, mode='textblob'):
        self.mode = mode
        self.classifier = None
        
        if mode == 'huggingface' and HF_AVAILABLE:
            print("Loading Hugging Face model...")
            self.classifier = pipeline(
                "sentiment-analysis",
                model="distilbert-base-uncased-finetuned-sst-2-english",
                device=-1
            )
            print("Model ready")
        elif mode == 'textblob' and not TEXTBLOB_AVAILABLE:
            print("TextBlob not installed. Run: pip install textblob")
    
    def analyze_text(self, text):
        if not text or len(text.strip()) < 3:
            return {'polarity': 0, 'sentiment': 'neutral'}
        
        if self.mode == 'huggingface' and self.classifier:
            try:
                result = self.classifier(text[:512])[0]
                label = result['label'].lower()
                confidence = result['score']
                polarity = confidence if label == 'positive' else -confidence
                return {'polarity': round(polarity, 3), 'sentiment': label}
            except:
                return {'polarity': 0, 'sentiment': 'neutral'}
        
        # TextBlob mode
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity
        
        if polarity > 0.2:
            sentiment = 'positive'
        elif polarity < -0.2:
            sentiment = 'negative'
        else:
            sentiment = 'neutral'
        
        return {'polarity': round(polarity, 3), 'sentiment': sentiment}
    
    def analyze_comments(self, comments):
        results = []
        mode_name = "Hugging Face" if self.mode == 'huggingface' else "TextBlob"
        print(f"Analyzing {len(comments)} comments using {mode_name}...")
        
        for i, comment in enumerate(comments):
            sentiment = self.analyze_text(comment['comment'])
            results.append({
                'author': comment['author'],
                'comment': comment['comment'],
                'sentiment': sentiment['sentiment'],
                'polarity': sentiment['polarity']
            })
            
            if (i + 1) % 100 == 0:
                print(f"  Processed {i + 1}/{len(comments)} comments")
        
        return results