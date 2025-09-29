"""
PDF Text Extraction Module
Handles robust extraction of text from factsheet PDFs with multi-page support
"""
import PyPDF2
import re
import logging
from typing import List, Dict, Optional
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PDFExtractor:
    """Robust PDF text extractor for factsheets"""
    
    def __init__(self):
        self.extracted_texts = {}
    
    def extract_text_from_pdf(self, pdf_path: str) -> Dict[str, str]:
        """
        Extract text from PDF with comprehensive error handling
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dictionary with page-wise extracted text
        """
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                total_pages = len(pdf_reader.pages)
                
                logger.info(f"Processing {pdf_path} with {total_pages} pages")
                
                extracted_data = {
                    'file_name': Path(pdf_path).name,
                    'total_pages': total_pages,
                    'pages': {},
                    'full_text': '',
                    'scheme_info': {}
                }
                
                # Extract text from each page
                for page_num in range(total_pages):
                    try:
                        page = pdf_reader.pages[page_num]
                        page_text = page.extract_text()
                        
                        if page_text.strip():
                            extracted_data['pages'][f'page_{page_num + 1}'] = page_text
                            extracted_data['full_text'] += f"\n--- Page {page_num + 1} ---\n{page_text}"
                            
                            # Extract basic scheme information from first few pages
                            if page_num < 3:  # Focus on first 3 pages for scheme info
                                self._extract_scheme_info(page_text, extracted_data['scheme_info'])
                        
                    except Exception as e:
                        logger.warning(f"Error extracting page {page_num + 1}: {str(e)}")
                        continue
                
                # Store in cache
                self.extracted_texts[pdf_path] = extracted_data
                
                logger.info(f"Successfully extracted text from {pdf_path}")
                return extracted_data
                
        except Exception as e:
            logger.error(f"Error processing PDF {pdf_path}: {str(e)}")
            return {
                'file_name': Path(pdf_path).name,
                'error': str(e),
                'pages': {},
                'full_text': '',
                'scheme_info': {}
            }
    
    def _extract_scheme_info(self, text: str, scheme_info: Dict) -> None:
        """Extract basic scheme information from text"""
        
        # Scheme name patterns
        scheme_name_patterns = [
            r'Scheme Name[:\s]*([^\n\r]+)',
            r'Fund Name[:\s]*([^\n\r]+)',
            r'Name of the Scheme[:\s]*([^\n\r]+)',
            r'^([A-Z][^a-z]*?(?:Fund|Scheme|Plan)[^a-z]*?)(?:\s|$)',  # Capitalized scheme names
        ]
        
        # AMC name patterns
        amc_patterns = [
            r'Asset Management Company[:\s]*([^\n\r]+)',
            r'AMC[:\s]*([^\n\r]+)',
            r'Fund House[:\s]*([^\n\r]+)',
            r'([A-Z][^a-z]*?(?:Asset Management|Mutual Fund|Investment)[^a-z]*?)(?:\s|$)',
        ]
        
        # Extract scheme name
        if 'scheme_name' not in scheme_info:
            for pattern in scheme_name_patterns:
                match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
                if match:
                    scheme_info['scheme_name'] = match.group(1).strip()
                    break
        
        # Extract AMC name
        if 'amc_name' not in scheme_info:
            for pattern in amc_patterns:
                match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
                if match:
                    scheme_info['amc_name'] = match.group(1).strip()
                    break
    
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
        """
        Extract text from all PDF files in the factsheets directory
        
        Args:
            factsheets_dir: Directory containing factsheet PDFs
            
        Returns:
            Dictionary with all extracted data
        """
        pdf_files = self.get_all_pdf_files(factsheets_dir)
        all_extracted_data = {}
        
        for pdf_file in pdf_files:
            logger.info(f"Processing: {pdf_file}")
            extracted_data = self.extract_text_from_pdf(pdf_file)
            all_extracted_data[pdf_file] = extracted_data
        
        return all_extracted_data
    
    def search_text_across_pages(self, extracted_data: Dict, search_terms: List[str]) -> Dict[str, List[str]]:
        """
        Search for specific terms across all pages of extracted text
        
        Args:
            extracted_data: Extracted data from PDF
            search_terms: List of terms to search for
            
        Returns:
            Dictionary with search results
        """
        results = {}
        
        for term in search_terms:
            results[term] = []
            
            # Search in full text
            if 'full_text' in extracted_data:
                full_text = extracted_data['full_text']
                lines = full_text.split('\n')
                
                for i, line in enumerate(lines):
                    if re.search(term, line, re.IGNORECASE):
                        # Get context (previous and next lines)
                        start = max(0, i - 2)
                        end = min(len(lines), i + 3)
                        context = '\n'.join(lines[start:end])
                        results[term].append({
                            'line_number': i + 1,
                            'context': context,
                            'matched_line': line.strip()
                        })
        
        return results
    
    def get_text_by_keywords(self, extracted_data: Dict, keywords: List[str]) -> str:
        """
        Extract relevant text sections based on keywords
        
        Args:
            extracted_data: Extracted data from PDF
            keywords: Keywords to search for
            
        Returns:
            Relevant text sections
        """
        relevant_text = ""
        
        if 'full_text' in extracted_data:
            full_text = extracted_data['full_text']
            lines = full_text.split('\n')
            
            for i, line in enumerate(lines):
                for keyword in keywords:
                    if re.search(keyword, line, re.IGNORECASE):
                        # Get context around the keyword
                        start = max(0, i - 5)
                        end = min(len(lines), i + 10)
                        context = '\n'.join(lines[start:end])
                        relevant_text += f"\n--- Context for '{keyword}' ---\n{context}\n"
                        break
        
        return relevant_text
