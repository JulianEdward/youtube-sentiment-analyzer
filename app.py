import os
import json
import threading
import uuid
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, Response
from werkzeug.utils import secure_filename

from comment_extractor import YouTubeCommentExtractor
from sentiment_analyzer import SentimentAnalyzer

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

analysis_results = {}
analysis_jobs = {}

class AnalysisJob:
    def __init__(self, job_id, source_type, source_data, mode):
        self.job_id = job_id
        self.source_type = source_type
        self.source_data = source_data
        self.mode = mode
        self.status = 'pending'
        self.progress = 0
        self.result = None
        self.error = None
        self.created_at = datetime.now()

def run_analysis(job_id, source_type, source_data, mode):
    job = analysis_jobs.get(job_id)
    if not job:
        return
    
    try:
        job.status = 'running'
        job.progress = 10
        
        comments = []
        
        if source_type == 'url':
            print(f"[Job {job_id}] Extracting comments from URL...")
            extractor = YouTubeCommentExtractor()
            comments = extractor.extract_all_comments(source_data)
            
        elif source_type == 'json':
            print(f"[Job {job_id}] Loading comments from JSON...")
            
            if isinstance(source_data, dict):
                json_data = source_data
            else:
                with open(source_data, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
            
            if 'comments' in json_data:
                raw_comments = json_data['comments']
            elif 'reviews' in json_data:
                raw_comments = json_data['reviews']
            elif 'items' in json_data:
                raw_comments = json_data['items']
            else:
                raw_comments = json_data if isinstance(json_data, list) else []
            
            for item in raw_comments:
                if isinstance(item, dict):
                    author = item.get('author', item.get('user', item.get('name', 'Anonymous')))
                    comment = item.get('comment', item.get('text', item.get('content', str(item))))
                    if comment and len(str(comment).split()) >= 5:
                        comments.append({
                            'author': str(author) if author else 'Anonymous',
                            'comment': str(comment)
                        })
                elif isinstance(item, str):
                    if len(item.split()) >= 5:
                        comments.append({
                            'author': 'Anonymous',
                            'comment': item
                        })
        
        if not comments:
            job.status = 'failed'
            job.error = 'No valid comments found (min 5 words each)'
            analysis_jobs[job_id] = job
            return
        
        job.progress = 50
        print(f"[Job {job_id}] Found {len(comments)} comments")
        
        analyzer = SentimentAnalyzer(mode=mode)
        analyzed_comments = analyzer.analyze_comments(comments)
        
        job.progress = 90
        
        positive = [c for c in analyzed_comments if c['sentiment'] == 'positive']
        negative = [c for c in analyzed_comments if c['sentiment'] == 'negative']
        neutral = [c for c in analyzed_comments if c['sentiment'] == 'neutral']
        
        stats = {
            'total': len(analyzed_comments),
            'positive': len(positive),
            'negative': len(negative),
            'neutral': len(neutral),
            'positive_percent': round(len(positive) / len(analyzed_comments) * 100, 1) if analyzed_comments else 0,
            'negative_percent': round(len(negative) / len(analyzed_comments) * 100, 1) if analyzed_comments else 0,
            'neutral_percent': round(len(neutral) / len(analyzed_comments) * 100, 1) if analyzed_comments else 0,
            'avg_polarity': round(sum(c['polarity'] for c in analyzed_comments) / len(analyzed_comments), 3) if analyzed_comments else 0
        }
        
        job.result = {
            'source': source_data if source_type == 'url' else 'JSON Upload',
            'source_type': source_type,
            'mode': mode,
            'stats': stats,
            'comments': analyzed_comments
        }
        
        analysis_results[job_id] = job.result
        analysis_jobs[job_id] = job
        
        job.status = 'completed'
        job.progress = 100
        print(f"[Job {job_id}] Analysis complete")
        
    except Exception as e:
        print(f"[Job {job_id}] Error: {e}")
        job.status = 'failed'
        job.error = str(e)
        analysis_jobs[job_id] = job

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    if request.is_json:
        data = request.get_json()
        url = data.get('url')
        mode = data.get('mode', 'textblob')
        
        if not url:
            return jsonify({'error': 'No URL provided'}), 400
        
        job_id = str(uuid.uuid4())
        job = AnalysisJob(job_id, 'url', url, mode)
        analysis_jobs[job_id] = job
        
        thread = threading.Thread(target=run_analysis, args=(job_id, 'url', url, mode))
        thread.daemon = True
        thread.start()
        
        return jsonify({'job_id': job_id})
    
    if 'json_file' in request.files:
        file = request.files['json_file']
        if file and file.filename:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{uuid.uuid4()}_{filename}")
            file.save(filepath)
            
            mode = request.form.get('mode', 'textblob')
            
            job_id = str(uuid.uuid4())
            job = AnalysisJob(job_id, 'json', filepath, mode)
            analysis_jobs[job_id] = job
            
            thread = threading.Thread(target=run_analysis, args=(job_id, 'json', filepath, mode))
            thread.daemon = True
            thread.start()
            
            return jsonify({'job_id': job_id})
    
    return jsonify({'error': 'No valid input provided'}), 400

@app.route('/status/<job_id>')
def get_status(job_id):
    if job_id in analysis_results:
        return jsonify({'status': 'completed', 'progress': 100, 'error': None})
    
    job = analysis_jobs.get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    
    return jsonify({
        'status': job.status,
        'progress': job.progress,
        'error': job.error,
        'mode': job.mode
    })

@app.route('/results/<job_id>')
def get_results(job_id):
    if job_id in analysis_results:
        return jsonify(analysis_results[job_id])
    
    job = analysis_jobs.get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    
    if job.status != 'completed':
        return jsonify({'error': 'Job not completed yet'}), 400
    
    return jsonify(job.result)

@app.route('/view/<job_id>')
def view_results(job_id):
    if job_id not in analysis_results and job_id not in analysis_jobs:
        return redirect(url_for('index'))
    
    return render_template('results.html', job_id=job_id)

@app.route('/export/<job_id>')
def export_results(job_id):
    if job_id in analysis_results:
        result = analysis_results[job_id]
    else:
        job = analysis_jobs.get(job_id)
        if not job or job.status != 'completed':
            return jsonify({'error': 'Results not found'}), 404
        result = job.result
    
    filename = f"sentiment_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    return Response(
        json.dumps(result, indent=2),
        mimetype='application/json',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )

import os

if __name__ == '__main__':
    debug_mode = os.getenv('DEBUG', 'False').lower() == 'true'
    print("Open: http://localhost:5000")
    app.run(debug=debug_mode, host='0.0.0.0', port=5000, threaded=True)