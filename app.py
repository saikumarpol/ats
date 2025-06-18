import os
import re
import nltk
from flask import Flask, render_template, request, flash, redirect, url_for
from werkzeug.utils import secure_filename
import PyPDF2
import pdfplumber
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords

# Download required NLTK resources
try:
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    nltk.download('punkt_tab')
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'  # Replace with a secure key
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['ALLOWED_EXTENSIONS'] = {'pdf'}

# Ensure upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Common job-related keywords (customize based on target roles)
JOB_KEYWORDS = [
    'python', 'java', 'javascript', 'sql', 'machine learning', 'data analysis',
    'web development', 'cloud computing', 'aws', 'azure', 'docker', 'kubernetes',
    'communication', 'teamwork', 'problem-solving', 'leadership', 'project',
    'internship', 'research', 'development', 'software', 'engineering'
]

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def extract_text_from_pdf(pdf_path):
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = ''
            for page in pdf.pages:
                text += page.extract_text() or ''
        return text
    except Exception as e:
        return None

def analyze_resume(text):
    if not text:
        return 0, {"error": "Unable to extract text from PDF."}, []

    # Initialize score and feedback
    score = 0
    feedback = {}
    suggestions = []

    try:
        # 1. Keyword Matching (40% weight)
        tokens = word_tokenize(text.lower())
        tokens = [word for word in tokens if word.isalnum()]
        stop_words = set(stopwords.words('english'))
        filtered_tokens = [word for word in tokens if word not in stop_words]
        
        keyword_count = sum(1 for keyword in JOB_KEYWORDS if keyword in filtered_tokens)
        keyword_score = min((keyword_count / len(JOB_KEYWORDS)) * 40, 40)
        score += keyword_score
        feedback['Keywords'] = f"Found {keyword_count} relevant keywords. Score: {keyword_score:.1f}/40"
        if keyword_count < 5:
            suggestions.append("Add more job-specific keywords like 'Python', 'SQL', or 'teamwork' to match job descriptions.")

        # 2. Resume Length (20% weight)
        word_count = len(filtered_tokens)
        if 150 <= word_count <= 400:
            length_score = 20
        elif 100 <= word_count < 150 or 400 < word_count <= 500:
            length_score = 15
        else:
            length_score = 10
        score += length_score
        feedback['Length'] = f"Word count: {word_count}. Score: {length_score}/20"
        if word_count < 150:
            suggestions.append("Your resume is too short. Add more details about projects or skills.")
        elif word_count > 500:
            suggestions.append("Your resume is too long. Aim for 1 page with concise content.")

        # 3. Formatting Check (20% weight)
        formatting_score = 20
        if len(text.split('\n')) < 10:
            formatting_score -= 10
            suggestions.append("Ensure proper formatting with clear sections (e.g., Education, Projects).")
        if not re.search(r'\b\d{4}\b', text):  # Check for years (e.g., graduation year)
            formatting_score -= 5
            suggestions.append("Include years for education or experience.")
        score += formatting_score
        feedback['Formatting'] = f"Score: {formatting_score}/20"

        # 4. Readability (20% weight)
        readability_score = 20
        long_words = sum(1 for word in filtered_tokens if len(word) > 15)
        if long_words > 5:
            readability_score -= 5
            suggestions.append("Avoid overly complex words to improve readability.")
        if text.count('.') < 5:
            readability_score -= 5
            suggestions.append("Use more sentences or bullet points for clarity.")
        score += readability_score
        feedback['Readability'] = f"Score: {readability_score}/20"

    except Exception as e:
        return 0, {"error": f"Analysis failed: {str(e)}"}, ["Ensure the resume is a valid PDF and try again."]

    return round(score, 1), feedback, suggestions

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'resume' not in request.files:
            flash('No file uploaded', 'danger')
            return redirect(request.url)
        
        file = request.files['resume']
        if file.filename == '':
            flash('No file selected', 'danger')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            text = extract_text_from_pdf(file_path)
            score, feedback, suggestions = analyze_resume(text)
            
            # Clean up uploaded file
            try:
                os.remove(file_path)
            except:
                pass
            
            return render_template('result.html', score=score, feedback=feedback, suggestions=suggestions)
        else:
            flash('Invalid file format. Please upload a PDF.', 'danger')
    
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)