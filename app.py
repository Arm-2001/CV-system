from flask import Flask, request, jsonify
from flask_cors import CORS
import PyPDF2
import docx
import re
import os
from werkzeug.utils import secure_filename
from collections import Counter
import json

app = Flask(__name__)
CORS(app)

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
UPLOAD_FOLDER = 'temp_uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx'}

# Create upload folder if it doesn't exist
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

class CVAnalyzer:
    def __init__(self):
        self.skill_keywords = {
            'programming': ['python', 'java', 'javascript', 'c++', 'c#', 'php', 'ruby', 'go', 'rust', 'swift', 'kotlin', 'typescript', 'scala', 'r'],
            'web_development': ['html', 'css', 'react', 'angular', 'vue', 'node.js', 'express', 'django', 'flask', 'bootstrap', 'jquery', 'sass', 'webpack'],
            'data_science': ['machine learning', 'deep learning', 'tensorflow', 'pytorch', 'pandas', 'numpy', 'scikit-learn', 'data analysis', 'statistics', 'ml', 'ai'],
            'databases': ['sql', 'mysql', 'mongodb', 'postgresql', 'redis', 'elasticsearch', 'oracle', 'sqlite', 'nosql'],
            'cloud': ['aws', 'azure', 'gcp', 'docker', 'kubernetes', 'terraform', 'jenkins', 'ci/cd', 'devops'],
            'mobile': ['android', 'ios', 'react native', 'flutter', 'swift', 'kotlin', 'xamarin'],
            'soft_skills': ['leadership', 'communication', 'teamwork', 'problem solving', 'analytical', 'creative', 'management', 'project management']
        }
        
        self.section_keywords = {
            'contact': ['email', 'phone', 'address', 'linkedin', 'github', 'portfolio'],
            'education': ['university', 'college', 'degree', 'bachelor', 'master', 'phd', 'certification', 'diploma'],
            'experience': ['experience', 'work', 'job', 'position', 'role', 'company', 'employment'],
            'skills': ['skills', 'technical', 'programming', 'software', 'tools', 'technologies'],
            'projects': ['project', 'developed', 'built', 'created', 'implemented'],
            'achievements': ['award', 'recognition', 'achievement', 'honor', 'certificate', 'accomplishment']
        }
        
    def extract_text_from_pdf(self, file_path):
        """Extract text from PDF file"""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text
        except Exception as e:
            return f"Error reading PDF: {str(e)}"
    
    def extract_text_from_docx(self, file_path):
        """Extract text from DOCX file"""
        try:
            doc = docx.Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        except Exception as e:
            return f"Error reading DOCX: {str(e)}"
    
    def extract_text_from_txt(self, file_path):
        """Extract text from TXT file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            return f"Error reading TXT: {str(e)}"
    
    def extract_text(self, file_path):
        """Extract text based on file extension"""
        if file_path.lower().endswith('.pdf'):
            return self.extract_text_from_pdf(file_path)
        elif file_path.lower().endswith('.docx'):
            return self.extract_text_from_docx(file_path)
        elif file_path.lower().endswith('.txt'):
            return self.extract_text_from_txt(file_path)
        else:
            return "Unsupported file format. Please use PDF, DOCX, or TXT files."
    
    def extract_contact_info(self, text):
        """Extract contact information from CV text"""
        contact_info = {}
        
        # Email extraction
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        contact_info['emails'] = emails
        
        # Phone extraction (multiple formats)
        phone_patterns = [
            r'(\+\d{1,4}[-.\s]?)?\(?\d{3,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{4}',
            r'\+\d{1,4}[-.\s]?\d{3,4}[-.\s]?\d{3,4}[-.\s]?\d{3,4}',
            r'\d{3}[-.\s]?\d{3}[-.\s]?\d{4}'
        ]
        phones = []
        for pattern in phone_patterns:
            phones.extend(re.findall(pattern, text))
        contact_info['phones'] = list(set(phones))
        
        # LinkedIn extraction
        linkedin_pattern = r'linkedin\.com/in/[\w-]+'
        linkedin = re.findall(linkedin_pattern, text.lower())
        contact_info['linkedin'] = linkedin
        
        # GitHub extraction
        github_pattern = r'github\.com/[\w-]+'
        github = re.findall(github_pattern, text.lower())
        contact_info['github'] = github
        
        # Portfolio/Website extraction
        website_pattern = r'(?:https?://)?(?:www\.)?[\w-]+\.[\w.-]+(?:/[\w.-]*)*'
        websites = re.findall(website_pattern, text.lower())
        contact_info['websites'] = [w for w in websites if 'linkedin' not in w and 'github' not in w]
        
        return contact_info
    
    def extract_skills(self, text):
        """Extract skills from CV text"""
        text_lower = text.lower()
        found_skills = {}
        
        for category, skills in self.skill_keywords.items():
            found_skills[category] = []
            for skill in skills:
                if skill.lower() in text_lower:
                    found_skills[category].append(skill)
        
        return found_skills
    
    def identify_sections(self, text):
        """Identify different sections in the CV"""
        sections = {}
        lines = text.split('\n')
        
        current_section = 'general'
        sections[current_section] = []
        
        section_headers = {
            'contact': ['contact', 'personal information', 'personal details'],
            'summary': ['summary', 'objective', 'profile', 'about', 'overview'],
            'education': ['education', 'academic', 'qualification', 'university', 'college'],
            'experience': ['experience', 'work history', 'employment', 'professional experience', 'career'],
            'skills': ['skills', 'technical skills', 'competencies', 'technologies'],
            'projects': ['projects', 'portfolio', 'personal projects'],
            'achievements': ['achievements', 'awards', 'honors', 'accomplishments'],
            'certifications': ['certifications', 'certificates', 'licenses']
        }
        
        for line in lines:
            line_lower = line.lower().strip()
            section_found = False
            
            if not line_lower:
                continue
            
            for section, keywords in section_headers.items():
                if any(keyword in line_lower for keyword in keywords) and len(line.strip()) < 50:
                    current_section = section
                    if current_section not in sections:
                        sections[current_section] = []
                    section_found = True
                    break
            
            if not section_found:
                if current_section not in sections:
                    sections[current_section] = []
                sections[current_section].append(line)
        
        return sections
    
    def analyze_length_and_structure(self, text):
        """Analyze CV length and structure"""
        words = text.split()
        word_count = len(words)
        char_count = len(text)
        lines = text.split('\n')
        line_count = len([line for line in lines if line.strip()])
        
        bullet_count = len([line for line in lines if re.match(r'^\s*[-•*▪▫◦‣⁃]\s', line)])
        
        return {
            'word_count': word_count,
            'character_count': char_count,
            'line_count': line_count,
            'bullet_points': bullet_count,
            'avg_words_per_line': word_count / line_count if line_count > 0 else 0
        }
    
    def score_contact_section(self, contact_info):
        """Score the contact information section"""
        score = 0
        feedback = []
        max_score = 100
        
        if contact_info['emails']:
            score += 30
            feedback.append("✓ Email address provided")
        else:
            feedback.append("✗ Missing email address - Essential for contact")
        
        if contact_info['phones']:
            score += 25
            feedback.append("✓ Phone number provided")
        else:
            feedback.append("✗ Missing phone number - Important for contact")
        
        if contact_info['linkedin']:
            score += 25
            feedback.append("✓ LinkedIn profile included")
        else:
            feedback.append("⚠ Consider adding LinkedIn profile")
        
        if contact_info['github']:
            score += 15
            feedback.append("✓ GitHub profile included")
        else:
            feedback.append("⚠ Consider adding GitHub profile (for technical roles)")
        
        if contact_info['websites']:
            score += 5
            feedback.append("✓ Personal website/portfolio included")
        
        return min(score, max_score), feedback
    
    def score_skills_section(self, skills):
        """Score the skills section"""
        score = 0
        feedback = []
        max_score = 100
        
        total_skills = sum(len(skill_list) for skill_list in skills.values())
        
        if total_skills >= 15:
            score += 40
            feedback.append(f"✓ Excellent variety of skills ({total_skills} skills found)")
        elif total_skills >= 10:
            score += 30
            feedback.append(f"✓ Good variety of skills ({total_skills} skills found)")
        elif total_skills >= 5:
            score += 20
            feedback.append(f"⚠ Moderate skills listed ({total_skills} skills found)")
        else:
            score += 5
            feedback.append(f"✗ Limited skills listed ({total_skills} skills found)")
        
        categories_with_skills = sum(1 for skill_list in skills.values() if skill_list)
        if categories_with_skills >= 5:
            score += 30
            feedback.append("✓ Excellent balance across skill categories")
        elif categories_with_skills >= 3:
            score += 20
            feedback.append("✓ Good balance across skill categories")
        elif categories_with_skills >= 2:
            score += 10
            feedback.append("⚠ Consider adding more diverse skills")
        else:
            feedback.append("✗ Limited skill diversity")
        
        technical_categories = ['programming', 'web_development', 'data_science', 'databases', 'cloud', 'mobile']
        has_technical = any(skills[cat] for cat in technical_categories if cat in skills)
        if has_technical:
            score += 20
            feedback.append("✓ Technical skills present")
        else:
            feedback.append("⚠ Consider adding relevant technical skills")
        
        if skills['soft_skills']:
            score += 10
            feedback.append("✓ Soft skills included")
        else:
            feedback.append("⚠ Consider adding soft skills")
        
        return min(score, max_score), feedback
    
    def score_structure_and_length(self, structure_info):
        """Score CV structure and length"""
        score = 0
        feedback = []
        max_score = 100
        
        word_count = structure_info['word_count']
        
        if 400 <= word_count <= 800:
            score += 50
            feedback.append(f"✓ Excellent length ({word_count} words)")
        elif 300 <= word_count < 400:
            score += 40
            feedback.append(f"✓ Good length ({word_count} words)")
        elif 800 < word_count <= 1000:
            score += 40
            feedback.append(f"✓ Good length ({word_count} words)")
        elif 200 <= word_count < 300:
            score += 25
            feedback.append(f"⚠ Too short ({word_count} words)")
        elif 1000 < word_count <= 1200:
            score += 25
            feedback.append(f"⚠ Too long ({word_count} words)")
        else:
            score += 10
            feedback.append(f"✗ Poor length ({word_count} words)")
        
        bullet_points = structure_info['bullet_points']
        if bullet_points >= 5:
            score += 20
            feedback.append(f"✓ Good use of bullet points ({bullet_points})")
        elif bullet_points >= 2:
            score += 15
            feedback.append(f"✓ Some bullet points used ({bullet_points})")
        else:
            score += 5
            feedback.append("⚠ Consider using bullet points")
        
        avg_words_per_line = structure_info['avg_words_per_line']
        if 6 <= avg_words_per_line <= 12:
            score += 20
            feedback.append("✓ Good line structure")
        else:
            score += 10
            feedback.append("⚠ Consider improving line structure")
        
        return min(score, max_score), feedback
    
    def score_sections(self, sections):
        """Score the presence and quality of different sections"""
        score = 0
        feedback = []
        max_score = 100
        
        essential_sections = ['education', 'experience', 'skills']
        important_sections = ['summary', 'projects']
        bonus_sections = ['achievements', 'certifications']
        
        for section in essential_sections:
            if section in sections and sections[section]:
                content = ' '.join(sections[section])
                if len(content.strip()) > 50:
                    score += 20
                    feedback.append(f"✓ {section.capitalize()} section present with good content")
                else:
                    score += 10
                    feedback.append(f"⚠ {section.capitalize()} section present but lacks detail")
            else:
                feedback.append(f"✗ Missing {section} section")
        
        for section in important_sections:
            if section in sections and sections[section]:
                score += 15
                feedback.append(f"✓ {section.capitalize()} section present")
        
        for section in bonus_sections:
            if section in sections and sections[section]:
                score += 5
                feedback.append(f"✓ {section.capitalize()} section present")
        
        return min(score, max_score), feedback
    
    def analyze_content_quality(self, text, sections):
        """Analyze content quality and depth"""
        numbers_pattern = r'\b\d+(?:\.\d+)?(?:%|k|K|million|M|billion|B)?\b'
        numbers_found = len(re.findall(numbers_pattern, text))
        
        action_verbs = ['achieved', 'developed', 'implemented', 'led', 'managed', 'created', 
                       'improved', 'increased', 'reduced', 'designed', 'built', 'optimized',
                       'delivered', 'coordinated', 'supervised', 'analyzed', 'established']
        action_verb_count = sum(1 for verb in action_verbs if verb.lower() in text.lower())
        
        impact_keywords = ['results', 'success', 'efficiency', 'performance', 'growth', 
                          'savings', 'revenue', 'productivity', 'quality', 'innovation']
        impact_count = sum(1 for keyword in impact_keywords if keyword.lower() in text.lower())
        
        quality_analysis = {
            'quantifiable_achievements': numbers_found,
            'action_verbs_used': action_verb_count,
            'impact_keywords': impact_count,
            'has_summary': 'summary' in sections or 'objective' in sections,
            'has_achievements': 'achievements' in sections or 'accomplishments' in sections
        }
        
        return quality_analysis
    
    def analyze_ats_compatibility(self, text, structure_info):
        """Analyze ATS compatibility"""
        ats_score = 0
        ats_feedback = []
        
        standard_headers = ['experience', 'education', 'skills', 'summary']
        headers_found = sum(1 for header in standard_headers if header in text.lower())
        
        if headers_found >= 3:
            ats_score += 30
            ats_feedback.append("✓ Standard section headers detected")
        else:
            ats_feedback.append("⚠ Use standard section headers")
        
        special_chars = len(re.findall(r'[^\w\s\-\.\,\(\)\@\:\/\%\&]', text))
        if special_chars < 50:
            ats_score += 20
            ats_feedback.append("✓ Clean formatting for ATS parsing")
        else:
            ats_feedback.append("⚠ Reduce special characters")
        
        if '@' in text:
            ats_score += 20
            ats_feedback.append("✓ Email format is ATS-friendly")
        
        avg_line_length = structure_info['character_count'] / structure_info['line_count']
        if avg_line_length < 80:
            ats_score += 15
            ats_feedback.append("✓ Good line length for ATS parsing")
        else:
            ats_feedback.append("⚠ Consider shorter lines")
        
        ats_score += 15
        
        return min(ats_score, 100), ats_feedback
    
    def calculate_overall_score(self, contact_score, skills_score, structure_score, sections_score):
        """Calculate weighted overall score"""
        weights = {
            'contact': 0.15,
            'skills': 0.30,
            'structure': 0.25,
            'sections': 0.30
        }
        
        overall_score = (
            contact_score * weights['contact'] +
            skills_score * weights['skills'] +
            structure_score * weights['structure'] +
            sections_score * weights['sections']
        )
        
        return round(overall_score, 1)
    
    def generate_improvement_suggestions(self, contact_score, skills_score, structure_score, sections_score, content_quality):
        """Generate specific improvement suggestions"""
        suggestions = []
        
        # Critical Issues (Score < 50)
        if contact_score < 50:
            suggestions.append({
                'priority': 'Critical',
                'area': 'Contact Information',
                'action': 'Include complete professional contact details',
                'impact': 'Essential for employer communication'
            })
        
        if sections_score < 50:
            suggestions.append({
                'priority': 'Critical',
                'area': 'Core CV Sections',
                'action': 'Develop Education, Experience, and Skills sections',
                'impact': 'Required for CV completeness'
            })
        
        # High Impact Improvements
        if skills_score < 70:
            suggestions.append({
                'priority': 'High',
                'area': 'Skills Portfolio',
                'action': 'Expand technical and soft skills representation',
                'impact': 'Improves keyword matching and competency demonstration'
            })
        
        if content_quality['quantifiable_achievements'] < 3:
            suggestions.append({
                'priority': 'High',
                'area': 'Quantifiable Results',
                'action': 'Include specific metrics and measurable outcomes',
                'impact': 'Demonstrates concrete professional value'
            })
        
        # Medium Impact Improvements
        if structure_score < 80:
            suggestions.append({
                'priority': 'Medium',
                'area': 'Document Structure',
                'action': 'Optimize word count and visual hierarchy',
                'impact': 'Enhances professional presentation and readability'
            })
        
        if not content_quality['has_summary']:
            suggestions.append({
                'priority': 'Medium',
                'area': 'Professional Summary',
                'action': 'Develop concise professional overview section',
                'impact': 'Provides strong opening impression'
            })
        
        return suggestions
    
    def analyze_cv(self, file_path):
        """Main method to analyze CV"""
        try:
            # Extract text
            text = self.extract_text(file_path)
            if not text or "Error reading" in text or "Unsupported file format" in text:
                return {"error": "Could not extract text from file. Please ensure it's a valid PDF, DOCX, or TXT file."}
            
            if len(text.strip()) < 50:
                return {"error": "File appears to be empty or contains too little text to analyze."}
            
            # Extract information
            contact_info = self.extract_contact_info(text)
            skills = self.extract_skills(text)
            sections = self.identify_sections(text)
            structure_info = self.analyze_length_and_structure(text)
            content_quality = self.analyze_content_quality(text, sections)
            ats_score, ats_feedback = self.analyze_ats_compatibility(text, structure_info)
            
            # Calculate scores
            contact_score, contact_feedback = self.score_contact_section(contact_info)
            skills_score, skills_feedback = self.score_skills_section(skills)
            structure_score, structure_feedback = self.score_structure_and_length(structure_info)
            sections_score, sections_feedback = self.score_sections(sections)
            
            overall_score = self.calculate_overall_score(contact_score, skills_score, structure_score, sections_score)
            
            # Generate suggestions
            suggestions = self.generate_improvement_suggestions(
                contact_score, skills_score, structure_score, sections_score, content_quality
            )
            
            # Compile results
            results = {
                'overall_score': overall_score,
                'scores': {
                    'contact': round(contact_score, 1),
                    'skills': round(skills_score, 1),
                    'structure': round(structure_score, 1),
                    'sections': round(sections_score, 1),
                    'ats_compatibility': round(ats_score, 1),
                    'overall': overall_score
                },
                'feedback': {
                    'contact': contact_feedback,
                    'skills': skills_feedback,
                    'structure': structure_feedback,
                    'sections': sections_feedback,
                    'ats_compatibility': ats_feedback
                },
                'detailed_analysis': {
                    'content_quality': content_quality,
                    'skills_breakdown': skills,
                    'sections_content': list(sections.keys()),
                    'structure_metrics': structure_info
                },
                'suggestions': suggestions,
                'grade': self.get_grade(overall_score)
            }
            
            return results
            
        except Exception as e:
            return {"error": f"An error occurred during analysis: {str(e)}"}
    
    def get_grade(self, score):
        """Get grade based on score"""
        if score >= 85:
            return {"grade": "Excellent", "message": "CV demonstrates exceptional professional presentation"}
        elif score >= 75:
            return {"grade": "Very Good", "message": "Strong professional CV with solid fundamentals"}
        elif score >= 65:
            return {"grade": "Good", "message": "Competent CV structure with improvement potential"}
        elif score >= 50:
            return {"grade": "Satisfactory", "message": "Basic CV framework with development opportunities"}
        else:
            return {"grade": "Requires Development", "message": "CV requires substantial improvements"}

# Initialize the analyzer
analyzer = CVAnalyzer()

@app.route('/')
def index():
    return jsonify({
        'service': 'CV Analysis API',
        'status': 'running',
        'version': '1.0.0',
        'endpoints': {
            'analyze': {
                'method': 'POST',
                'url': '/analyze',
                'description': 'Upload CV file for comprehensive analysis',
                'parameters': 'file (form-data)',
                'supported_formats': ['PDF', 'DOCX', 'TXT']
            },
            'health': {
                'method': 'GET', 
                'url': '/health',
                'description': 'API health check'
            }
        },
        'usage_example': {
            'method': 'POST',
            'url': 'https://your-domain.onrender.com/analyze',
            'body': 'form-data with key "file" containing CV file',
            'response': 'JSON with comprehensive CV analysis'
        }
    })

@app.route('/analyze', methods=['POST'])
def analyze_cv():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        try:
            # Analyze the CV
            results = analyzer.analyze_cv(file_path)
            
            # Clean up the uploaded file
            os.remove(file_path)
            
            return jsonify(results)
            
        except Exception as e:
            # Clean up the uploaded file in case of error
            if os.path.exists(file_path):
                os.remove(file_path)
            return jsonify({'error': f'Analysis failed: {str(e)}'}), 500
    
    return jsonify({'error': 'Invalid file type. Please upload PDF, DOCX, or TXT files.'}), 400

@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy', 'message': 'CV Analysis API is running'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
