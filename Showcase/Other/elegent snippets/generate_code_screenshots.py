#!/usr/bin/env python3
"""
Professional Code Screenshot Generator
مولد لقطات الشاشة الاحترافية للأكواد

This script generates elegant, professional screenshots of Python code files
with proper syntax highlighting, service ID identification, and beautiful styling.
"""

import os
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime
import time
import traceback

# Progress bar
try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    print("tqdm not available. Install with: pip install tqdm")
    TQDM_AVAILABLE = False

# Screenshot and image processing libraries
try:
    from PIL import Image, ImageDraw, ImageFont
    from pygments import highlight
    from pygments.lexers import PythonLexer
    from pygments.formatters import ImageFormatter
    from pygments.styles import get_style_by_name
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    from matplotlib import font_manager
    IMAGING_AVAILABLE = True
except ImportError as e:
    print(f"Required libraries not installed: {e}")
    print("Install with: pip install Pillow pygments matplotlib tqdm")
    IMAGING_AVAILABLE = False

# Web-based screenshot alternative
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    import base64
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProfessionalCodeScreenshotGenerator:
    """
    Professional code screenshot generator with elegant styling
    مولد لقطات الشاشة الاحترافية للأكواد مع التصميم الأنيق
    """
    
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.screenshots_path = workspace_path / "code_screenshots"
        self.screenshots_path.mkdir(exist_ok=True)
        
        # Load service mappings
        self.service_mappings = self._load_service_mappings()
        
        # Screenshot configuration
        self.config = {
            'style_theme': 'monokai',
            'font_size': 12,
            'image_width': 1200,
            'margin': 0,  # No margins - full width
            'header_height': 0,  # No header - full height for code
            'background_color': '#272822',  # Monokai background
            'text_color': '#f8f8f2',
            'line_number_bg': '#3e3d32',
            'line_number_fg': '#90908a'
        }
        
        # Initialize components
        if IMAGING_AVAILABLE:
            self.lexer = PythonLexer()
            self.style = get_style_by_name(self.config['style_theme'])
        
        logger.info("Professional Code Screenshot Generator initialized")
    
    def _load_service_mappings(self) -> Dict[str, str]:
        """Load service ID mappings from snippets.json"""
        try:
            snippets_file = self.workspace_path / "snippets.json"
            if snippets_file.exists():
                with open(snippets_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                mappings = {}
                for category, services in data.items():
                    for service in services:
                        service_id = service.get('id', '')
                        description = service.get('description', '')
                        mappings[service_id] = {
                            'category': category,
                            'description': description
                        }
                
                return mappings
        except Exception as e:
            logger.warning(f"Could not load service mappings: {e}")
        
        return {}
    
    def _discover_python_files(self) -> List[Path]:
        """
        Discover all Python files in the workspace, excluding common ignore directories
        اكتشاف جميع ملفات Python في مساحة العمل، مع استبعاد المجلدات المتجاهلة
        """
        python_files = []
        
        # Directories to ignore (case-insensitive)
        ignore_dirs = {
            '.venv', 'venv', '.env', 'env',
            '__pycache__', '.pytest_cache',
            '.git', '.svn', '.hg',
            'node_modules', '.node_modules',
            'build', 'dist', '.build', '.dist',
            '.tox', '.coverage', '.mypy_cache',
            '.idea', '.vscode', '.vs',
            'site-packages', 'lib', 'include',
            'scripts', 'bin', 'obj',
            '.github', '.gitlab',
            'temp', 'tmp', '.temp', '.tmp'
        }
        
        # Get all Python files recursively
        for py_file in self.workspace_path.rglob("*.py"):
            # Skip the generator script itself
            if py_file.name == "generate_code_screenshots.py":
                continue
            
            # Check if file is in any ignored directory
            should_ignore = False
            for part in py_file.parts:
                if part.lower() in ignore_dirs:
                    should_ignore = True
                    break
                # Also ignore directories starting with . or __
                if part.startswith('.') or part.startswith('__'):
                    should_ignore = True
                    break
            
            if should_ignore:
                logger.debug(f"Ignoring file in excluded directory: {py_file}")
                continue
            
            # Skip very small files (likely not meaningful code)
            try:
                if py_file.stat().st_size < 50:  # Less than 50 bytes
                    logger.debug(f"Skipping small file: {py_file}")
                    continue
            except OSError:
                logger.warning(f"Could not check file size: {py_file}")
                continue
            
            python_files.append(py_file)
        
        logger.info(f"Discovered {len(python_files)} Python files (excluded common ignore directories)")
        return python_files
    
    def generate_all_screenshots(self) -> Dict[str, List[str]]:
        """
        Generate screenshots for all Python files with progress tracking
        إنشاء لقطات شاشة لجميع ملفات Python مع تتبع التقدم
        """
        results = {
            'successful': [],
            'failed': [],
            'total_files': 0,
            'total_screenshots': 0,
            'processing_time': 0,
            'errors': []
        }
        
        start_time = time.time()
        
        try:
            # Find all Python files
            logger.info("🔍 Scanning for Python files...")
            python_files = self._discover_python_files()
            
            results['total_files'] = len(python_files)
            
            if not python_files:
                logger.warning("No Python files found!")
                return results
            
            logger.info(f"Found {len(python_files)} Python files to process")
            
            # Process files with progress bar
            if TQDM_AVAILABLE:
                file_iterator = tqdm(python_files, desc="📸 Generating Screenshots", 
                                   unit="file", colour="green")
            else:
                file_iterator = python_files
                print(f"Processing {len(python_files)} files...")
            
            for i, py_file in enumerate(file_iterator):
                try:
                    if not TQDM_AVAILABLE:
                        print(f"[{i+1}/{len(python_files)}] Processing {py_file.name}...")
                    
                    screenshots = self.generate_file_screenshots(py_file)
                    
                    if screenshots:
                        results['successful'].extend(screenshots)
                        results['total_screenshots'] += len(screenshots)
                        
                        if TQDM_AVAILABLE:
                            file_iterator.set_postfix({
                                'Screenshots': results['total_screenshots'],
                                'Current': len(screenshots)
                            })
                        else:
                            print(f"  ✅ Generated {len(screenshots)} screenshots")
                    else:
                        results['failed'].append(str(py_file))
                        error_msg = f"No screenshots generated for {py_file.name}"
                        results['errors'].append(error_msg)
                        logger.warning(error_msg)
                        
                        if not TQDM_AVAILABLE:
                            print(f"  ⚠️  No screenshots generated")
                        
                except Exception as e:
                    results['failed'].append(str(py_file))
                    error_msg = f"Failed to process {py_file.name}: {str(e)}"
                    results['errors'].append(error_msg)
                    logger.error(error_msg)
                    logger.debug(traceback.format_exc())
                    
                    if not TQDM_AVAILABLE:
                        print(f"  ❌ Error: {str(e)}")
            
            # Generate summary report
            logger.info("📋 Generating summary report...")
            self._generate_summary_report(results)
            
            results['processing_time'] = time.time() - start_time
            
            logger.info(f"✅ Screenshot generation completed: {results['total_screenshots']} screenshots from {results['total_files']} files in {results['processing_time']:.2f}s")
            
        except Exception as e:
            error_msg = f"Critical error in screenshot generation: {str(e)}"
            results['errors'].append(error_msg)
            logger.error(error_msg)
            logger.debug(traceback.format_exc())
        
        return results
    
    def generate_file_screenshots(self, file_path: Path) -> List[str]:
        """
        Generate screenshots for a single Python file with robust error handling
        إنشاء لقطات شاشة لملف Python واحد مع معالجة قوية للأخطاء
        """
        screenshots = []
        
        try:
            # Validate file exists and is readable
            if not file_path.exists():
                logger.error(f"File does not exist: {file_path}")
                return []
            
            if not file_path.is_file():
                logger.error(f"Path is not a file: {file_path}")
                return []
            
            # Read file content with multiple encoding attempts
            content = None
            encodings = ['utf-8', 'utf-8-sig', 'latin1', 'cp1252']
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        content = f.read()
                    break
                except UnicodeDecodeError:
                    continue
            
            if content is None:
                logger.error(f"Could not read file with any encoding: {file_path}")
                return []
            
            # Skip empty files
            if not content.strip():
                logger.warning(f"File is empty: {file_path}")
                return []
            
            # Extract service ID from content
            service_id = self._extract_service_id(content)
            
            # Split content into logical sections
            sections = self._split_into_sections(content, file_path.name)
            
            if not sections:
                logger.warning(f"No sections found in file: {file_path}")
                return []
            
            # Generate screenshots for each section with progress tracking
            section_iterator = sections
            if TQDM_AVAILABLE and len(sections) > 3:
                section_iterator = tqdm(sections, desc=f"Sections in {file_path.name}", 
                                     leave=False, colour="blue")
            
            for i, section in enumerate(section_iterator):
                try:
                    if section['code'].strip() and len(section['code'].strip()) > 50:  # Skip very small sections
                        screenshot_path = self._generate_section_screenshot(
                            section, file_path, service_id, i
                        )
                        if screenshot_path:
                            screenshots.append(screenshot_path)
                        else:
                            logger.warning(f"Failed to generate screenshot for section {i} in {file_path.name}")
                    
                except Exception as e:
                        logger.error(f"Error generating screenshot for section {i} in {file_path.name}: {e}")
                        continue
            
            if not screenshots:
                logger.warning(f"No screenshots generated for {file_path.name}")
            
            return screenshots
            
        except Exception as e:
            logger.error(f"Critical error processing file {file_path}: {e}")
            logger.debug(traceback.format_exc())
            return screenshots  # Return any screenshots generated before the error
    
    def _extract_service_id(self, content: str) -> Optional[str]:
        """Extract service ID from file content"""
        # Look for service ID in comments
        patterns = [
            r'Service ID:\s*([A-Z]{3}\d{2})',
            r'# Service ID:\s*([A-Z]{3}\d{2})',
            r'ID:\s*([A-Z]{3}\d{2})',
            r'service_id.*["\']([A-Z]{3}\d{2})["\']'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1).upper()
        
        return None
    
    def _split_into_sections(self, content: str, filename: str) -> List[Dict[str, str]]:
        """
        Split code into logical sections based on separators
        تقسيم الكود إلى أقسام منطقية بناءً على الفواصل
        """
        sections = []
        lines = content.split('\n')
        current_section = []
        current_title = f"Main Code - {filename}"
        
        # Define section separators
        separators = [
            '# ' + '='*50,
            '# ' + '-'*50,
            '"""',
            "'''",
            'class ',
            'def ',
            '# Service ID:',
            '# محرك',  # Arabic engine indicators
            '# Advanced',
            '# Professional'
        ]
        
        for line_num, line in enumerate(lines):
            # Check if this line starts a new section
            is_separator = False
            new_title = None
            
            # Check for class definitions
            if line.strip().startswith('class ') and ':' in line:
                class_name = re.search(r'class\s+(\w+)', line)
                if class_name:
                    new_title = f"Class: {class_name.group(1)}"
                    is_separator = True
            
            # Check for function definitions (only major functions)
            elif line.strip().startswith('def ') and not line.strip().startswith('def _'):
                func_name = re.search(r'def\s+(\w+)', line)
                if func_name:
                    new_title = f"Function: {func_name.group(1)}"
                    is_separator = True
            
            # Check for service ID headers
            elif 'Service ID:' in line:
                service_match = re.search(r'Service ID:\s*([A-Z]{3}\d{2})', line)
                if service_match:
                    service_id = service_match.group(1)
                    service_info = self.service_mappings.get(service_id, {})
                    new_title = f"Service {service_id}: {service_info.get('description', 'Unknown Service')}"
                    is_separator = True
            
            # Check for major comment blocks
            elif any(sep in line for sep in ['# Advanced', '# Professional', '# محرك']):
                comment_text = line.strip('# ').strip()
                new_title = f"Module: {comment_text[:50]}..."
                is_separator = True
            
            # If we found a separator and have accumulated content
            if is_separator and current_section and len(current_section) > 5:
                sections.append({
                    'title': current_title,
                    'code': '\n'.join(current_section),
                    'start_line': line_num - len(current_section) + 1,
                    'end_line': line_num
                })
                current_section = []
                current_title = new_title or current_title
            
            current_section.append(line)
            
            # Limit section size to prevent huge screenshots
            if len(current_section) > 100:  # Max 100 lines per section
                sections.append({
                    'title': current_title,
                    'code': '\n'.join(current_section),
                    'start_line': line_num - len(current_section) + 1,
                    'end_line': line_num
                })
                current_section = []
                current_title = f"Continuation - {filename}"
        
        # Add remaining content
        if current_section:
            sections.append({
                'title': current_title,
                'code': '\n'.join(current_section),
                'start_line': len(lines) - len(current_section) + 1,
                'end_line': len(lines)
            })
        
        # Filter out very small sections
        sections = [s for s in sections if len(s['code'].strip()) > 100]
        
        return sections
    
    def _generate_section_screenshot(self, section: Dict[str, str], file_path: Path, 
                                   service_id: Optional[str], section_index: int) -> Optional[str]:
        """
        Generate screenshot for a code section with robust error handling
        إنشاء لقطة شاشة لقسم من الكود مع معالجة قوية للأخطاء
        """
        try:
            if not IMAGING_AVAILABLE:
                logger.warning("Imaging libraries not available, skipping screenshot generation")
                return None
            
            # Validate section content
            if not section.get('code') or not section['code'].strip():
                logger.warning("Section has no code content")
                return None
            
            # Create safe filename
            base_name = file_path.stem
            service_prefix = f"{service_id}_" if service_id else ""
            
            # Clean title for filename
            safe_title = re.sub(r'[^\w\s-]', '', section['title'][:30])
            safe_title = re.sub(r'[-\s]+', '_', safe_title).strip('_')
            
            screenshot_name = f"{service_prefix}{base_name}_section_{section_index:02d}_{safe_title}.png"
            screenshot_path = self.screenshots_path / screenshot_name
            
            # Ensure unique filename
            counter = 1
            original_path = screenshot_path
            while screenshot_path.exists():
                screenshot_path = original_path.with_stem(f"{original_path.stem}_{counter}")
                counter += 1
            
            # Limit code length to prevent memory issues
            code_content = section['code']
            max_lines = 150  # Limit to prevent huge images
            lines = code_content.split('\n')
            if len(lines) > max_lines:
                code_content = '\n'.join(lines[:max_lines]) + f"\n\n# ... ({len(lines) - max_lines} more lines truncated)"
            
            # Generate syntax-highlighted image with full width/height
            try:
                formatter = ImageFormatter(
                    style=self.config['style_theme'],
                    font_size=self.config['font_size'],
                    line_numbers=True,
                    line_number_bg=self.config['line_number_bg'],
                    line_number_fg=self.config['line_number_fg']
                )
                
                # Highlight the code
                highlighted_bytes = highlight(code_content, self.lexer, formatter)
                
                # Create PIL image from highlighted code - this IS the final image
                from io import BytesIO
                final_img = Image.open(BytesIO(highlighted_bytes))
                
            except Exception as e:
                logger.error(f"Failed to generate syntax highlighting: {e}")
                # Fallback: create simple text image that fills full dimensions
                final_img = self._create_fallback_code_image(code_content)
                if not final_img:
                    return None
            
            # Save image with error handling
            try:
                final_img.save(screenshot_path, 'PNG', quality=95, optimize=True)
                logger.debug(f"Generated screenshot: {screenshot_name}")
                return str(screenshot_path)
                
            except Exception as e:
                logger.error(f"Failed to save screenshot: {e}")
                return None
            
        except Exception as e:
            logger.error(f"Critical error generating screenshot for section: {e}")
            logger.debug(traceback.format_exc())
            return None
    
    def _get_font(self, size: int):
        """Get font with fallbacks"""
        font_paths = [
            "arial.ttf", "Arial.ttf", "calibri.ttf", "Calibri.ttf",
            "C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/calibri.ttf",
            "/System/Library/Fonts/Arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        ]
        
        for font_path in font_paths:
            try:
                return ImageFont.truetype(font_path, size)
            except:
                continue
        
        return ImageFont.load_default()
    
    def _create_fallback_code_image(self, code_content: str) -> Optional[Image.Image]:
        """Create simple text image as fallback with line numbers"""
        try:
            lines = code_content.split('\n')
            
            font = self._get_font(12)
            line_height = 16
            line_number_width = 60  # Space for line numbers
            
            # Calculate image size
            max_width = 0
            for line in lines:
                try:
                    bbox = font.getbbox(line)
                    width = bbox[2] - bbox[0]
                    max_width = max(max_width, width)
                except:
                    max_width = max(max_width, len(line) * 8)  # Fallback calculation
            
            img_width = max_width + line_number_width + 20
            img_height = len(lines) * line_height + 20
            
            # Use monokai colors
            img = Image.new('RGB', (img_width, img_height), '#272822')
            draw = ImageDraw.Draw(img)
            
            # Draw line numbers and code
            y = 10
            for i, line in enumerate(lines, 1):
                # Draw line number
                line_num_text = f"{i:3d}"
                draw.text((10, y), line_num_text, fill='#90908a', font=font)
                
                # Draw separator
                draw.text((line_number_width - 10, y), "│", fill='#90908a', font=font)
                
                # Draw code line
                draw.text((line_number_width + 10, y), line, fill='#f8f8f2', font=font)
                y += line_height
            
            return img
            
        except Exception as e:
            logger.error(f"Failed to create fallback image: {e}")
            return None
    
    def _generate_summary_report(self, results: Dict[str, any]):
        """Generate HTML summary report of all screenshots"""
        try:
            html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Code Screenshots Summary - Professional Services</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0;
            padding: 20px;
            color: #333;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #2d3748 0%, #4a5568 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 2.5em;
            font-weight: 300;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 30px;
            background: #f8f9fa;
        }}
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 5px 15px rgba(0,0,0,0.08);
        }}
        .stat-number {{
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }}
        .stat-label {{
            color: #666;
            margin-top: 5px;
        }}
        .screenshots-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            padding: 30px;
        }}
        .screenshot-card {{
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            transition: transform 0.3s ease;
        }}
        .screenshot-card:hover {{
            transform: translateY(-5px);
        }}
        .screenshot-card img {{
            width: 100%;
            height: 200px;
            object-fit: cover;
        }}
        .screenshot-info {{
            padding: 15px;
        }}
        .service-id {{
            background: #667eea;
            color: white;
            padding: 5px 10px;
            border-radius: 15px;
            font-size: 0.8em;
            display: inline-block;
            margin-bottom: 10px;
        }}
        .footer {{
            background: #2d3748;
            color: white;
            text-align: center;
            padding: 20px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎨 Professional Code Screenshots</h1>
            <p>Elegant & Styled Code Documentation</p>
            <p>Generated on {datetime.now().strftime("%B %d, %Y at %H:%M")}</p>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-number">{results['total_files']}</div>
                <div class="stat-label">Python Files</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{results['total_screenshots']}</div>
                <div class="stat-label">Screenshots Generated</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{len(results['successful'])}</div>
                <div class="stat-label">Successful</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{len(results['failed'])}</div>
                <div class="stat-label">Failed</div>
            </div>
        </div>
        
        <div class="screenshots-grid">
"""
            
            # Add screenshot cards
            for screenshot_path in results['successful']:
                screenshot_file = Path(screenshot_path)
                filename = screenshot_file.name
                
                # Extract service ID from filename
                service_id_match = re.match(r'([A-Z]{3}\d{2})_', filename)
                service_id = service_id_match.group(1) if service_id_match else "Unknown"
                
                service_info = self.service_mappings.get(service_id, {})
                
                html_content += f"""
            <div class="screenshot-card">
                <img src="code_screenshots/{filename}" alt="{filename}">
                <div class="screenshot-info">
                    <div class="service-id">{service_id}</div>
                    <h3>{filename.replace('_', ' ').replace('.png', '')}</h3>
                    <p>{service_info.get('description', 'Professional code implementation')}</p>
                </div>
            </div>
"""
            
            html_content += f"""
        </div>
        
        <div class="footer">
            <p>🚀 Professional Automation, AI & Data Engineering Services</p>
            <p>Generated by Advanced Code Screenshot Generator</p>
        </div>
    </div>
</body>
</html>
"""
            
            # Save HTML report
            report_path = self.screenshots_path / "screenshots_summary.html"
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"Summary report generated: {report_path}")
            
        except Exception as e:
            logger.error(f"Failed to generate summary report: {e}")

def main():
    """Main execution function with comprehensive error handling and validation"""
    print("🎨 Professional Code Screenshot Generator")
    print("=" * 60)
    
    # Check dependencies
    missing_deps = []
    if not IMAGING_AVAILABLE:
        missing_deps.append("Pillow pygments matplotlib")
    if not TQDM_AVAILABLE:
        missing_deps.append("tqdm")
    
    if missing_deps:
        print("❌ Required libraries not installed!")
        print(f"Please install: pip install {' '.join(missing_deps)}")
        print("\nFull installation command:")
        print("pip install Pillow pygments matplotlib tqdm")
        return False
    
    try:
        # Initialize generator
        workspace = Path(__file__).parent
        
        # Validate workspace
        if not workspace.exists():
            print(f"❌ Workspace directory not found: {workspace}")
            return False
        
        print(f"📁 Workspace: {workspace}")
        
        generator = ProfessionalCodeScreenshotGenerator(workspace)
        
        # Check if Python files exist
        python_files = list(workspace.rglob("*.py"))
        python_files = [f for f in python_files if not f.name.startswith('generate_')]
        
        if not python_files:
            print("❌ No Python files found in workspace!")
            return False
        
        print(f"🔍 Found {len(python_files)} Python files")
        print("🚀 Starting screenshot generation...")
        print("=" * 60)
        
        # Generate screenshots
        results = generator.generate_all_screenshots()
        
        # Display results
        print("\n" + "=" * 60)
        print("📊 GENERATION SUMMARY:")
        print(f"   📁 Total Files Processed: {results['total_files']}")
        print(f"   📸 Screenshots Generated: {results['total_screenshots']}")
        print(f"   ✅ Successful: {len(results['successful'])}")
        print(f"   ❌ Failed: {len(results['failed'])}")
        print(f"   ⏱️  Processing Time: {results.get('processing_time', 0):.2f}s")
        
        # Show success rate
        if results['total_files'] > 0:
            success_rate = (len(results['successful']) / results['total_screenshots'] * 100) if results['total_screenshots'] > 0 else 0
            print(f"   📈 Success Rate: {success_rate:.1f}%")
        
        # Show failed files if any
        if results['failed']:
            print(f"\n⚠️  Failed files ({len(results['failed'])}):")
            for failed_file in results['failed'][:10]:  # Show max 10
                print(f"   - {Path(failed_file).name}")
            if len(results['failed']) > 10:
                print(f"   ... and {len(results['failed']) - 10} more")
        
        # Show errors if any
        if results.get('errors'):
            print(f"\n🔍 Recent errors ({len(results['errors'])}):")
            for error in results['errors'][-5:]:  # Show last 5 errors
                print(f"   - {error}")
        
        # Show output locations
        print(f"\n📂 Output locations:")
        print(f"   🎨 Screenshots: {generator.screenshots_path}")
        print(f"   📋 Summary report: {generator.screenshots_path / 'screenshots_summary.html'}")
        
        # Final status
        if results['total_screenshots'] > 0:
            print(f"\n🎉 Success! Generated {results['total_screenshots']} professional screenshots")
            print("✨ Professional code documentation complete!")
            return True
        else:
            print("\n❌ No screenshots were generated")
            return False
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Generation cancelled by user")
        return False
    except Exception as e:
        print(f"\n❌ Critical error: {e}")
        logger.error(f"Critical error in main: {e}")
        logger.debug(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
