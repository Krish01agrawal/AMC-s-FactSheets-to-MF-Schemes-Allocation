"""
Smart Hybrid Data Extractor combining regex for simple fields and Gemini for complex extraction.
This approach minimizes API costs while maximizing accuracy.
"""

import os
import json
import re
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import time

from advanced_pdf_extractor import AdvancedPDFExtractor
from gemini_data_extractor import GeminiDataExtractor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SmartHybridExtractor:
    def __init__(self):
        """Initialize the smart hybrid extractor"""
        self.pdf_extractor = AdvancedPDFExtractor()
        self.gemini_extractor = GeminiDataExtractor()
        
        # Regex patterns for simple fields that can be extracted reliably
        self.simple_patterns = {
            'nav_growth': r'NAV\s*\(?Growth\)?\s*:?\s*([\d,]+\.?\d*)',
            'nav_idcw': r'NAV\s*\(?IDCW\)?\s*:?\s*([\d,]+\.?\d*)',
            'aum': r'AUM\s*\(?Crores?\)?\s*:?\s*([\d,]+\.?\d*)',
            'expense_ratio': r'Expense\s*Ratio\s*:?\s*([\d.]+)%?',
            'standard_deviation': r'Standard\s*Deviation\s*:?\s*([\d.]+)%?',
            'beta': r'Beta\s*:?\s*([\d.]+)',
            'sharpe_ratio': r'Sharpe\s*Ratio\s*:?\s*([\d.]+)',
            'min_sip': r'Minimum\s*SIP\s*:?\s*₹?([\d,]+)',
            'inception_date': r'Date\s*of\s*Allotment\s*:?\s*(\d{2}/\d{2}/\d{4})',
            'benchmark': r'Benchmark\s*:?\s*([A-Za-z0-9\s&()]+)',
        }
        
    def extract_simple_fields(self, text: str) -> Dict[str, Any]:
        """Extract simple fields using regex patterns"""
        simple_data = {}
        
        for field, pattern in self.simple_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                # Convert to appropriate type
                if field in ['nav_growth', 'nav_idcw', 'aum', 'expense_ratio', 
                           'standard_deviation', 'beta', 'sharpe_ratio', 'min_sip']:
                    try:
                        simple_data[field] = float(value.replace(',', ''))
                    except ValueError:
                        simple_data[field] = value
                else:
                    simple_data[field] = value
            else:
                simple_data[field] = None
                
        return simple_data
    
    def should_use_gemini(self, text: str, simple_data: Dict[str, Any]) -> bool:
        """
        Determine if we should use Gemini for complex extraction.
        Use Gemini if:
        1. Simple extraction found less than 3 fields
        2. Text contains complex portfolio data
        3. Text contains multiple fund managers
        4. Text contains industry allocation data
        """
        # Count non-null simple fields
        non_null_count = sum(1 for v in simple_data.values() if v is not None)
        
        # Check for complex data indicators
        complex_indicators = [
            'portfolio', 'holdings', 'industry', 'allocation',
            'fund manager', 'managing since', 'experience',
            'exit load', 'cagr', 'turnover', 'riskometer'
        ]
        
        has_complex_data = any(indicator in text.lower() for indicator in complex_indicators)
        
        # Use Gemini if we have complex data or insufficient simple extraction
        return has_complex_data or non_null_count < 3
    
    def split_into_schemes(self, text: str) -> List[Dict[str, str]]:
        """Split factsheet text into individual scheme blocks using intelligent detection"""
        schemes = []
        
        # First, try to find actual mutual fund scheme names
        # Look for patterns that indicate real scheme names
        scheme_indicators = [
            # Pattern 1: Fund names with specific keywords
            r'(HDFC\s+[A-Za-z\s&]+(?:Fund|Scheme))\s*\n',
            # Pattern 2: Fund names with category
            r'([A-Z][A-Za-z\s&]+(?:Large Cap|Mid Cap|Small Cap|Flexi Cap|Multi Cap|Balanced|Debt|Liquid|Money Market|Gilt|Corporate Bond|Credit Risk|Banking|Technology|Healthcare|FMCG|Infrastructure|Thematic|Value|Growth|Dividend|IDCW|ITC)\s+(?:Fund|Scheme))\s*\n',
            # Pattern 3: Fund names with specific AMC patterns
            r'(HDFC\s+[A-Za-z\s&]+(?:Equity|Debt|Hybrid|Balanced|Liquid|Money Market|Gilt|Corporate Bond|Credit Risk|Banking|Technology|Healthcare|FMCG|Infrastructure|Thematic|Value|Growth|Dividend|IDCW|ITC))\s*\n',
            # Pattern 4: Generic fund patterns but more specific
            r'([A-Z][A-Za-z\s&]+(?:Fund|Scheme))\s*[-–]\s*([^\n\r]+)',
        ]
        
        # Try each pattern
        for pattern in scheme_indicators:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                scheme_name = match.group(1).strip()
                
                # Clean scheme name
                scheme_name = re.sub(r'\s+', ' ', scheme_name)
                scheme_name = re.sub(r'[^\w\s&\.\-]', '', scheme_name)
                
                # Skip if too short or contains common non-scheme words
                if len(scheme_name) < 5 or any(word in scheme_name.lower() for word in ['page', 'contd', 'continued', 'glossary', 'disclaimer', 'risk', 'warning']):
                    continue
                
                # Find the text block for this scheme
                start_pos = match.end()
                next_match = None
                
                # Look for the next scheme or end of text
                for next_pattern in scheme_indicators:
                    next_matches = list(re.finditer(next_pattern, text[start_pos:], re.IGNORECASE | re.MULTILINE))
                    if next_matches:
                        if next_match is None or next_matches[0].start() < next_match.start():
                            next_match = next_matches[0]
                
                if next_match:
                    end_pos = start_pos + next_match.start()
                else:
                    end_pos = min(start_pos + 5000, len(text))  # Limit to 5000 chars
                
                scheme_text = text[start_pos:end_pos].strip()
                
                if len(scheme_text) > 200:  # Minimum length for meaningful data
                    schemes.append({
                        'name': scheme_name,
                        'text': scheme_text,
                        'amc': 'HDFC'  # Extract from text if needed
                    })
        
        # Remove duplicates and sort by position
        unique_schemes = []
        seen_names = set()
        for scheme in schemes:
            if scheme['name'] not in seen_names:
                unique_schemes.append(scheme)
                seen_names.add(scheme['name'])
        
        # If still no schemes found, try page-based splitting with better filtering
        if not unique_schemes:
            page_parts = re.split(r'--- Page \d+ ---', text)
            for i, part in enumerate(page_parts):
                if part.strip() and len(part.strip()) > 500:
                    # Look for fund names in the first few lines
                    lines = part.strip().split('\n')[:10]
                    scheme_name = None
                    
                    for line in lines:
                        if re.search(r'(HDFC\s+[A-Za-z\s&]+(?:Fund|Scheme))', line, re.IGNORECASE):
                            scheme_name = line.strip()
                            break
                    
                    if scheme_name:
                        unique_schemes.append({
                            'name': scheme_name,
                            'text': part.strip(),
                            'amc': 'HDFC'
                        })
        
        return unique_schemes
    
    def process_factsheet(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Process a single factsheet PDF with real-time progress tracking"""
        logger.info(f"Processing factsheet: {pdf_path}")
        
        # Extract text from PDF
        extracted_data = self.pdf_extractor.extract_text_from_pdf(pdf_path)
        if not extracted_data or not extracted_data.get('full_text'):
            logger.warning(f"No text extracted from {pdf_path}")
            return []
        
        full_text = extracted_data['full_text']
        
        # Split into schemes
        schemes = self.split_into_schemes(full_text)
        logger.info(f"Found {len(schemes)} schemes in {pdf_path}")
        
        # Initialize real-time progress tracking
        amc_name = Path(pdf_path).stem
        progress_file = self._initialize_progress_file(amc_name, len(schemes))
        
        results = []
        
        for i, scheme in enumerate(schemes):
            logger.info(f"Processing scheme {i+1}/{len(schemes)}: {scheme['name']}")
            
            # Extract simple fields first
            simple_data = self.extract_simple_fields(scheme['text'])
            
            # Determine if we need Gemini for complex extraction
            if self.should_use_gemini(scheme['text'], simple_data):
                logger.info(f"Using Gemini for complex extraction: {scheme['name']}")
                
                try:
                    # Use Gemini for complex extraction
                    gemini_result = self.gemini_extractor.extract_data_with_gemini(
                        scheme['text'], 
                        scheme['name'], 
                        Path(pdf_path).stem
                    )
                    
                    # Merge simple and complex data
                    if 'error' not in gemini_result:
                        # Update simple fields with regex results if they're better
                        for field, value in simple_data.items():
                            if value is not None and gemini_result.get(field) is None:
                                gemini_result[field] = value
                        
                        results.append(gemini_result)
                    else:
                        logger.warning(f"Gemini extraction failed for {scheme['name']}: {gemini_result['error']}")
                        # Fallback to simple extraction
                        results.append(self._create_simple_result(scheme, simple_data))
                    
                    # Rate limiting
                    time.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error with Gemini extraction for {scheme['name']}: {e}")
                    results.append(self._create_simple_result(scheme, simple_data))
            else:
                logger.info(f"Using regex-only extraction: {scheme['name']}")
                results.append(self._create_simple_result(scheme, simple_data))
            
            # Update real-time progress
            self._update_progress_file(progress_file, i + 1, len(schemes), results[-1])
        
        # Mark as completed
        self._mark_progress_complete(progress_file, results)
        
        return results
    
    def _create_simple_result(self, scheme: Dict[str, str], simple_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a result from simple regex extraction in target format"""
        return {
            "Scheme_Name": scheme['name'],
            "Asset_Class": "N/A",
            "Sub_Class": "N/A",
            "Type_of_Scheme": "N/A",
            "Date_of_Allotment_(Inception_Date)": simple_data.get('inception_date', "N/A"),
            "AUM_(as_of_Aug_2025)": f"₹{simple_data.get('aum', 'N/A')} Crs" if simple_data.get('aum') else "N/A",
            "Fund_Manager_Name": "N/A",
            "Fund_Manager_Tenure": "N/A",
            "Fund_Manager_Experience": "N/A",
            "Benchmark": simple_data.get('benchmark', "N/A"),
            "Options": "Regular (IDCW, Growth)",
            "Expense_Ratio": {
                "Direct": f"{simple_data.get('expense_ratio', 'N/A')}%" if simple_data.get('expense_ratio') else "N/A",
                "Regular": f"{simple_data.get('expense_ratio', 'N/A')}%" if simple_data.get('expense_ratio') else "N/A"
            },
            "Risk_Metrics": {
                "Standard_Deviation": f"{simple_data.get('standard_deviation', 'N/A')}%" if simple_data.get('standard_deviation') else "N/A",
                "Beta": str(simple_data.get('beta', 'N/A')) if simple_data.get('beta') else "N/A",
                "Sharpe_Ratio": str(simple_data.get('sharpe_ratio', 'N/A')) if simple_data.get('sharpe_ratio') else "N/A"
            },
            "Turnover": {
                "Equity_Portfolio_Turnover": "N/A",
                "Total_Turnover": "N/A"
            },
            "Portfolio_Allocation_by_Market_Cap": {
                "Large_Cap_(%)": "N/A",
                "Mid_Cap_(%)": "N/A",
                "Small_Cap_(%)": "N/A",
                "Other_Assets_(%)": "N/A"
            },
            "NAV_Value_as_of_Aug_31_2025": {
                "Regular_Growth": f"₹{simple_data.get('nav_growth', 'N/A')}" if simple_data.get('nav_growth') else "N/A",
                "Regular_IDCW": f"₹{simple_data.get('nav_idcw', 'N/A')}" if simple_data.get('nav_idcw') else "N/A",
                "Regular_ITC": "N/A"
            },
            "Exit_Load": {
                "Under_30_days": "N/A",
                "30_-_90_days": "N/A",
                "After_90_days": "N/A"
            },
            "Minimum_Monthly_SIP_investment_amount": f"₹{simple_data.get('min_sip', 'N/A')}" if simple_data.get('min_sip') else "N/A",
            "RisKometer_(Risk_Profile)": "N/A",
            "CAGR": {
                "1Y": "N/A",
                "3Y": "N/A",
                "5Y": "N/A",
                "All": "N/A"
            },
            "Debt_Metrics": "N/A"
        }
    
    def _initialize_progress_file(self, amc_name: str, total_schemes: int) -> str:
        """Initialize progress tracking file"""
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        progress_file = output_dir / f"{amc_name}_progress_{timestamp}.json"
        
        initial_data = {
            "amc_name": amc_name,
            "status": "processing",
            "progress": {
                "current": 0,
                "total": total_schemes,
                "percentage": 0.0
            },
            "start_time": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "schemes": [],
            "errors": []
        }
        
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump(initial_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"📊 Progress tracking initialized: {progress_file}")
        return str(progress_file)
    
    def _update_progress_file(self, progress_file: str, current: int, total: int, scheme_data: Dict[str, Any]):
        """Update progress file with current scheme data"""
        try:
            # Read current progress
            with open(progress_file, 'r', encoding='utf-8') as f:
                progress_data = json.load(f)
            
            # Update progress
            progress_data["progress"]["current"] = current
            progress_data["progress"]["total"] = total
            progress_data["progress"]["percentage"] = round((current / total) * 100, 2)
            progress_data["last_updated"] = datetime.now().isoformat()
            progress_data["schemes"].append(scheme_data)
            
            # Write updated progress
            with open(progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"📊 Progress updated: {current}/{total} ({progress_data['progress']['percentage']}%)")
            
        except Exception as e:
            logger.error(f"Error updating progress file: {e}")
    
    def _mark_progress_complete(self, progress_file: str, all_results: List[Dict[str, Any]]):
        """Mark progress as completed"""
        try:
            # Read current progress
            with open(progress_file, 'r', encoding='utf-8') as f:
                progress_data = json.load(f)
            
            # Mark as completed
            progress_data["status"] = "completed"
            progress_data["progress"]["percentage"] = 100.0
            progress_data["end_time"] = datetime.now().isoformat()
            progress_data["total_schemes_extracted"] = len(all_results)
            progress_data["schemes"] = all_results
            
            # Write final progress
            with open(progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ Progress completed: {progress_file}")
            
        except Exception as e:
            logger.error(f"Error marking progress complete: {e}")
    
    def process_multiple_factsheets(self, factsheet_dir: str) -> Dict[str, Any]:
        """Process multiple factsheets"""
        factsheet_path = Path(factsheet_dir)
        if not factsheet_path.exists():
            logger.error(f"Factsheet directory not found: {factsheet_dir}")
            return {}
        
        pdf_files = list(factsheet_path.glob("*.pdf"))
        if not pdf_files:
            logger.error("No PDF files found in factsheet directory")
            return {}
        
        all_results = []
        total_schemes = 0
        total_time = 0
        
        for pdf_file in pdf_files:
            start_time = time.time()
            
            try:
                schemes = self.process_factsheet(str(pdf_file))
                all_results.extend(schemes)
                total_schemes += len(schemes)
                
                processing_time = time.time() - start_time
                total_time += processing_time
                
                logger.info(f"Extracted {len(schemes)} schemes from {pdf_file.name} in {processing_time:.2f}s")
                
            except Exception as e:
                logger.error(f"Error processing {pdf_file.name}: {e}")
        
        return {
            "metadata": {
                "extraction_method": "smart_hybrid",
                "description": "Smart hybrid extraction (regex + Gemini for complex data)",
                "total_schemes": total_schemes,
                "total_pdfs": len(pdf_files),
                "total_processing_time": total_time,
                "average_processing_time": total_time / len(pdf_files) if pdf_files else 0,
                "extraction_date": datetime.now().isoformat()
            },
            "schemes": all_results
        }

def main():
    """Test the smart hybrid extractor"""
    try:
        extractor = SmartHybridExtractor()
        
        # Process factsheets
        results = extractor.process_multiple_factsheets("factsheets")
        
        # Save results
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"smart_hybrid_results_{timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Results saved to: {output_file}")
        logger.info(f"Total schemes extracted: {results['metadata']['total_schemes']}")
        logger.info(f"Total processing time: {results['metadata']['total_processing_time']:.2f}s")
        
    except Exception as e:
        logger.error(f"Error in main: {e}")

if __name__ == "__main__":
    main()
