"""
Advanced PDF Text Extraction Module
Uses PyPDF2 and pdfplumber for maximum accuracy in financial data extraction
Handles multi-scheme factsheets with intelligent scheme detection
"""
import PyPDF2
import pdfplumber
import re
import logging
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from bson import ObjectId
import hashlib

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AdvancedPDFExtractor:
    """Advanced PDF extractor using multiple libraries for maximum accuracy"""
    
    def __init__(self):
        self.extracted_texts = {}
        self.scheme_boundaries = {}
    
    def extract_text_from_pdf(self, pdf_path: str) -> Dict[str, any]:
        """
        Extract text from PDF using both PyPDF2 and pdfplumber for maximum accuracy
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dictionary with comprehensive extracted data
        """
        try:
            extracted_data = {
                'file_name': Path(pdf_path).name,
                'file_path': pdf_path,
                'extraction_method': 'advanced',
                'pages': {},
                'full_text': '',
                'tables': [],
                'metadata': {}
            }
            
            # Extract using PyPDF2
            pypdf2_text = self._extract_with_pypdf2(pdf_path)
            
            # Extract using pdfplumber
            pdfplumber_data = self._extract_with_pdfplumber(pdf_path)
            
            # Combine and validate data
            extracted_data.update(pdfplumber_data)
            extracted_data['pypdf2_text'] = pypdf2_text
            
            # Store in cache
            self.extracted_texts[pdf_path] = extracted_data
            
            logger.info(f"Successfully extracted text from {pdf_path} ({len(extracted_data['pages'])} pages)")
            return extracted_data
            
        except Exception as e:
            logger.error(f"Error processing PDF {pdf_path}: {str(e)}")
            return {
                'file_name': Path(pdf_path).name,
                'error': str(e),
                'pages': {},
                'full_text': ''
            }
    
    def _extract_with_pypdf2(self, pdf_path: str) -> str:
        """Extract text using PyPDF2"""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                
                for page_num, page in enumerate(pdf_reader.pages):
                    page_text = page.extract_text()
                    if page_text.strip():
                        text += f"\n--- Page {page_num + 1} ---\n{page_text}"
                
                return text
        except Exception as e:
            logger.warning(f"PyPDF2 extraction failed: {str(e)}")
            return ""
    
    def _extract_with_pdfplumber(self, pdf_path: str) -> Dict[str, any]:
        """Extract text and tables using pdfplumber"""
        try:
            data = {
                'pages': {},
                'full_text': '',
                'tables': [],
                'metadata': {}
            }
            
            with pdfplumber.open(pdf_path) as pdf:
                data['metadata'] = {
                    'total_pages': len(pdf.pages),
                    'pdf_info': pdf.metadata or {}
                }
                
                for page_num, page in enumerate(pdf.pages):
                    page_data = {
                        'page_number': page_num + 1,
                        'text': '',
                        'tables': [],
                        'words': [],
                        'chars': []
                    }
                    
                    # Extract text
                    page_text = page.extract_text()
                    if page_text:
                        page_data['text'] = page_text
                        data['full_text'] += f"\n--- Page {page_num + 1} ---\n{page_text}"
                    
                    # Extract tables
                    tables = page.extract_tables()
                    if tables:
                        page_data['tables'] = tables
                        data['tables'].extend(tables)
                    
                    # Extract words and characters for better parsing
                    words = page.extract_words()
                    if words:
                        page_data['words'] = words
                    
                    chars = page.chars
                    if chars:
                        page_data['chars'] = chars
                    
                    data['pages'][f'page_{page_num + 1}'] = page_data
            
            return data
            
        except Exception as e:
            logger.warning(f"pdfplumber extraction failed: {str(e)}")
            return {'pages': {}, 'full_text': '', 'tables': [], 'metadata': {}}
    
    def _detect_scheme_boundaries(self, extracted_data: Dict) -> List[Dict]:
        """Detect scheme boundaries within the factsheet"""
        schemes = []
        full_text = extracted_data.get('full_text', '')
        
        if not full_text:
            return schemes
        
        # Scheme detection patterns
        scheme_patterns = [
            # Pattern 1: Fund name followed by description
            r'([A-Z][A-Z\s&\.]+(?:FUND|SCHEME|PLAN))\s*[-–]\s*([^\n\r]+)',
            # Pattern 2: Scheme name with category
            r'([A-Z][A-Z\s&\.]+(?:FUND|SCHEME))\s*\(([^)]+)\)',
            # Pattern 3: Fund name with type
            r'([A-Z][A-Z\s&\.]+(?:FUND|SCHEME))\s*[-–]\s*([A-Z][^a-z\n\r]+)',
            # Pattern 4: Simple fund name
            r'^([A-Z][A-Z\s&\.]+(?:FUND|SCHEME|PLAN))',
        ]
        
        # Find all potential scheme names
        potential_schemes = []
        for pattern in scheme_patterns:
            matches = re.finditer(pattern, full_text, re.MULTILINE | re.IGNORECASE)
            for match in matches:
                scheme_name = match.group(1).strip()
                description = match.group(2).strip() if len(match.groups()) > 1 else ""
                
                # Clean scheme name
                scheme_name = re.sub(r'\s+', ' ', scheme_name)
                scheme_name = re.sub(r'[^\w\s&\.\-]', '', scheme_name)
                
                if len(scheme_name) > 5 and scheme_name not in [s['name'] for s in potential_schemes]:
                    potential_schemes.append({
                        'name': scheme_name,
                        'description': description,
                        'position': match.start(),
                        'context': self._get_context_around_match(full_text, match.start(), match.end())
                    })
        
        # Sort by position and create scheme objects
        potential_schemes.sort(key=lambda x: x['position'])
        
        for i, scheme in enumerate(potential_schemes):
            scheme_data = {
                'scheme_id': str(ObjectId()),
                'name': scheme['name'],
                'description': scheme['description'],
                'position': scheme['position'],
                'context': scheme['context'],
                'extracted_data': self._extract_scheme_specific_data(
                    extracted_data, scheme['position'], i
                )
            }
            schemes.append(scheme_data)
        
        return schemes
    
    def _get_context_around_match(self, text: str, start: int, end: int, context_size: int = 500) -> str:
        """Get context around a match for better understanding"""
        context_start = max(0, start - context_size)
        context_end = min(len(text), end + context_size)
        return text[context_start:context_end]
    
    def _extract_scheme_specific_data(self, extracted_data: Dict, position: int, scheme_index: int) -> Dict:
        """Extract data specific to a scheme"""
        scheme_data = {
            'nav_data': {},
            'fund_details': {},
            'performance_metrics': {},
            'risk_metrics': {},
            'portfolio_data': {},
            'raw_text': ''
        }
        
        # Get text around the scheme
        full_text = extracted_data.get('full_text', '')
        if not full_text:
            return scheme_data
        
        # Extract a larger chunk of text for this scheme
        chunk_size = 2000
        start_pos = max(0, position - chunk_size)
        end_pos = min(len(full_text), position + chunk_size)
        scheme_text = full_text[start_pos:end_pos]
        
        scheme_data['raw_text'] = scheme_text
        
        # Extract basic scheme information
        scheme_data['fund_details'] = self._extract_basic_scheme_info(scheme_text)
        scheme_data['nav_data'] = self._extract_nav_data(scheme_text)
        scheme_data['performance_metrics'] = self._extract_performance_data(scheme_text)
        scheme_data['risk_metrics'] = self._extract_risk_data(scheme_text)
        scheme_data['portfolio_data'] = self._extract_portfolio_data(scheme_text)
        
        return scheme_data
    
    def _extract_basic_scheme_info(self, text: str) -> Dict:
        """Extract basic scheme information"""
        info = {}
        
        # AMC name patterns
        amc_patterns = [
            r'([A-Z][A-Z\s&\.]+(?:MUTUAL FUND|ASSET MANAGEMENT|INVESTMENT))',
            r'([A-Z][A-Z\s&\.]+(?:FUND|SCHEME|PLAN))\s*[-–]\s*([A-Z][A-Z\s&\.]+)',
        ]
        
        for pattern in amc_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                info['amc_name'] = match.group(1).strip()
                break
        
        # Inception date patterns
        inception_patterns = [
            r'Date of Allotment[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
            r'Inception Date[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
            r'Launch Date[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
        ]
        
        for pattern in inception_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                info['inception_date'] = match.group(1).strip()
                break
        
        # Fund manager patterns
        manager_patterns = [
            r'Fund Manager[:\s]*([^\n\r]+)',
            r'Manager[:\s]*([^\n\r]+)',
            r'Portfolio Manager[:\s]*([^\n\r]+)',
        ]
        
        for pattern in manager_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                info['fund_manager'] = match.group(1).strip()
                break
        
        # Benchmark patterns
        benchmark_patterns = [
            r'Benchmark[:\s]*([^\n\r]+)',
            r'Index[:\s]*([^\n\r]+)',
            r'Reference Index[:\s]*([^\n\r]+)',
        ]
        
        for pattern in benchmark_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                info['benchmark'] = match.group(1).strip()
                break
        
        return info
    
    def _extract_nav_data(self, text: str) -> Dict:
        """Extract NAV data"""
        nav_data = {}
        
        # NAV patterns
        nav_patterns = [
            r'NAV.*?Regular.*?Growth.*?(\d+\.?\d*)',
            r'Regular.*?Growth.*?(\d+\.?\d*)',
            r'Growth.*?(\d+\.?\d*)',
            r'IDCW.*?(\d+\.?\d*)',
            r'Dividend.*?(\d+\.?\d*)',
        ]
        
        for pattern in nav_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = float(match.group(1))
                if 'growth' in pattern.lower():
                    nav_data['regular_growth'] = value
                elif 'idcw' in pattern.lower() or 'dividend' in pattern.lower():
                    nav_data['idcw'] = value
                else:
                    nav_data['regular_itc'] = value
        
        return nav_data
    
    def _extract_performance_data(self, text: str) -> Dict:
        """Extract performance data"""
        performance = {}
        
        # CAGR patterns
        cagr_patterns = [
            r'1.*?Year.*?CAGR[:\s]*(\d+\.?\d*%?)',
            r'3.*?Year.*?CAGR[:\s]*(\d+\.?\d*%?)',
            r'5.*?Year.*?CAGR[:\s]*(\d+\.?\d*%?)',
            r'Since Inception.*?CAGR[:\s]*(\d+\.?\d*%?)',
        ]
        
        for pattern in cagr_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = float(re.sub(r'[^\d.]', '', match.group(1)))
                if '1.*?Year' in pattern:
                    performance['cagr_1y'] = value
                elif '3.*?Year' in pattern:
                    performance['cagr_3y'] = value
                elif '5.*?Year' in pattern:
                    performance['cagr_5y'] = value
                elif 'Since Inception' in pattern:
                    performance['cagr_all'] = value
        
        return performance
    
    def _extract_risk_data(self, text: str) -> Dict:
        """Extract risk data"""
        risk_data = {}
        
        # Risk metric patterns
        risk_patterns = [
            r'Standard Deviation[:\s]*(\d+\.?\d*%?)',
            r'Beta[:\s]*(\d+\.?\d*)',
            r'Sharpe Ratio[:\s]*(\d+\.?\d*)',
        ]
        
        for pattern in risk_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = float(re.sub(r'[^\d.]', '', match.group(1)))
                if 'Standard Deviation' in pattern:
                    risk_data['standard_deviation'] = value
                elif 'Beta' in pattern:
                    risk_data['beta'] = value
                elif 'Sharpe Ratio' in pattern:
                    risk_data['sharpe_ratio'] = value
        
        return risk_data
    
    def _extract_portfolio_data(self, text: str) -> Dict:
        """Extract portfolio data"""
        portfolio_data = {
            'industry_allocation': {},
            'top_holdings': [],
            'asset_allocation': {}
        }
        
        # Industry allocation patterns
        industry_patterns = [
            r'([A-Za-z\s]+)[:\s]*(\d+\.?\d*%?)',
        ]
        
        # Look for industry allocation sections
        allocation_section = self._find_section(text, ['industry', 'sector', 'allocation'])
        
        if allocation_section:
            for pattern in industry_patterns:
                matches = re.findall(pattern, allocation_section)
                for match in matches:
                    industry = match[0].strip()
                    percentage = match[1].strip()
                    if industry and percentage:
                        try:
                            percentage_value = float(re.sub(r'[^\d.]', '', percentage))
                            if 0 <= percentage_value <= 100:
                                portfolio_data['industry_allocation'][industry] = percentage_value
                        except ValueError:
                            continue
        
        return portfolio_data
    
    def _find_section(self, text: str, keywords: List[str]) -> str:
        """Find relevant section based on keywords"""
        lines = text.split('\n')
        section_lines = []
        in_section = False
        
        for line in lines:
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in keywords):
                in_section = True
                section_lines.append(line)
            elif in_section and line.strip() and not line.startswith(' '):
                if any(keyword in line_lower for keyword in ['performance', 'risk', 'portfolio', 'fund details']):
                    break
                section_lines.append(line)
        
        return '\n'.join(section_lines)
    
    def get_all_pdf_files(self, directory: str) -> List[str]:
        """Get all PDF files from directory"""
        pdf_files = []
        directory_path = Path(directory)
        
        if directory_path.exists():
            pdf_files = list(directory_path.glob('*.pdf'))
            pdf_files = [str(f) for f in pdf_files]
        
        logger.info(f"Found {len(pdf_files)} PDF files in {directory}")
        return pdf_files
    
    def extract_all_factsheets(self, factsheets_dir: str) -> Dict[str, Dict]:
        """Extract text from all PDF files in the factsheets directory"""
        pdf_files = self.get_all_pdf_files(factsheets_dir)
        all_extracted_data = {}
        
        for pdf_file in pdf_files:
            logger.info(f"Processing: {pdf_file}")
            extracted_data = self.extract_text_from_pdf(pdf_file)
            all_extracted_data[pdf_file] = extracted_data
        
        return all_extracted_data
    
    def generate_scheme_hash(self, scheme_data: Dict) -> str:
        """Generate a unique hash for a scheme to avoid duplicates"""
        # Create a hash based on scheme name, AMC, and key characteristics
        hash_string = f"{scheme_data.get('name', '')}_{scheme_data.get('amc_name', '')}_{scheme_data.get('inception_date', '')}"
        return hashlib.md5(hash_string.encode()).hexdigest()
