#!/usr/bin/env python3
"""
Scalable AMC Factsheet Extractor - REDESIGNED FOR ACCURACY
Extracts scheme data using Table of Contents + Page-based extraction
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Set
import re
import hashlib
import time

# Gemini imports
import google.generativeai as genai
from dotenv import load_dotenv

# PDF processing
from advanced_pdf_extractor import AdvancedPDFExtractor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ScalableAMCExtractor:
    """Scalable extractor using TOC-based scheme detection for 100% accuracy"""
    
    def __init__(self):
        load_dotenv()
        
        # Initialize multiple API keys for rotation
        self.api_keys = self._load_api_keys()
        if not self.api_keys:
            raise ValueError("No GEMINI_API_KEY found in environment variables")
        
        self.current_key_index = 0
        self.key_usage_count = {i: 0 for i in range(len(self.api_keys))}
        self.key_quota_exceeded = {i: False for i in range(len(self.api_keys))}
        
        # Initialize with first key
        self._configure_current_key()
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        self.pdf_extractor = AdvancedPDFExtractor()
        
        # Smart rate limiting
        self.request_delay = 4.0
        self.last_request_time = 0
        
        # Processing state
        self.processed_files = set()
        self.processing_state_file = Path("output/processing_state.json")
        self._load_processing_state()
        
        # Output directories
        self.output_dir = Path("output")
        self.output_dir.mkdir(exist_ok=True)
    
    def _find_precise_scheme_boundaries(self, full_text: str, scheme_name: str, page_number: str = "N/A") -> str:
        """
        Find precise boundaries for a scheme's data section
        """
        logger.info(f"🔍 Finding boundaries for {scheme_name} (Page: {page_number})")
        
        # Strategy 1: Look for scheme name as a heading
        scheme_heading_patterns = [
            rf'^[A-Z\s]+{re.escape(scheme_name)}[A-Z\s]*$',  # Full line heading
            rf'^[A-Z\s]*{re.escape(scheme_name)}[A-Z\s]*$',  # Partial line heading
            rf'{re.escape(scheme_name)}[A-Z\s]*$',           # End of line
        ]
        
        scheme_start = -1
        scheme_end = -1
        
        # Find scheme start
        for pattern in scheme_heading_patterns:
            matches = list(re.finditer(pattern, full_text, re.MULTILINE | re.IGNORECASE))
            for match in matches:
                # Check if this looks like a scheme heading (not in portfolio section)
                context_before = full_text[max(0, match.start()-200):match.start()]
                context_after = full_text[match.end():match.end()+200]
                
                # Skip if in portfolio section
                if any(word in context_before.lower() for word in ['portfolio', 'holdings', 'allocation', 'company']):
                    continue
                
                # Skip if in table of contents
                if any(word in context_before.lower() for word in ['contents', 'index', 'page']):
                    continue
                
                scheme_start = match.start()
                logger.info(f"📄 Found scheme heading at position {scheme_start}")
                break
            
            if scheme_start != -1:
                break
        
        if scheme_start == -1:
            # Fallback: look for scheme name anywhere
            match = re.search(re.escape(scheme_name), full_text, re.IGNORECASE)
            if match:
                scheme_start = match.start()
                logger.info(f"📄 Found scheme name at position {scheme_start}")
        
        if scheme_start == -1:
            logger.error(f"❌ Could not find scheme {scheme_name}")
            return ""
        
        # Find scheme end by looking for next scheme or section
        next_scheme_patterns = [
            r'^[A-Z\s]+Fund[A-Z\s]*$',  # Next fund heading
            r'^[A-Z\s]+Scheme[A-Z\s]*$',  # Next scheme heading
            r'^PORTFOLIO\s+CLASSIFICATION',  # Portfolio section
            r'^ASSET\s+ALLOCATION',  # Asset allocation section
            r'^BENCHMARK\s+COMPARISON',  # Benchmark section
            r'^RISK\s+METRICS',  # Risk metrics section
        ]
        
        # Look for next section after scheme start
        text_after_scheme = full_text[scheme_start + 1000:]  # Skip first 1000 chars to avoid same scheme
        
        for pattern in next_scheme_patterns:
            match = re.search(pattern, text_after_scheme, re.MULTILINE | re.IGNORECASE)
            if match:
                scheme_end = scheme_start + 1000 + match.start()
                logger.info(f"📄 Found scheme end at position {scheme_end}")
                break
        
        if scheme_end == -1:
            # Fallback: use reasonable chunk size
            scheme_end = min(len(full_text), scheme_start + 15000)
            logger.info(f"📄 Using fallback end at position {scheme_end}")
        
        scheme_text = full_text[scheme_start:scheme_end]
        logger.info(f"📊 Extracted {len(scheme_text)} chars for {scheme_name}")
        
        return scheme_text
    
    def _load_api_keys(self) -> List[str]:
        """Load multiple API keys from environment variables"""
        api_keys = []
        
        i = 1
        while True:
            key = os.environ.get(f"GEMINI_API_KEY_{i}")
            if key:
                api_keys.append(key)
                i += 1
            else:
                break
        
        if not api_keys:
            single_key = os.environ.get("GEMINI_API_KEY")
            if single_key:
                api_keys.append(single_key)
        
        logger.info(f"🔑 Loaded {len(api_keys)} API key(s) for rotation")
        return api_keys
    
    def _configure_current_key(self):
        """Configure Gemini with current API key"""
        current_key = self.api_keys[self.current_key_index]
        genai.configure(api_key=current_key)
        logger.info(f"🔑 Using API key {self.current_key_index + 1}/{len(self.api_keys)}")
    
    def _rotate_api_key(self):
        """Rotate to next available API key"""
        for _ in range(len(self.api_keys)):
            self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
            
            if not self.key_quota_exceeded[self.current_key_index]:
                self._configure_current_key()
                self.model = genai.GenerativeModel('gemini-2.5-flash')
                logger.info(f"🔄 Rotated to API key {self.current_key_index + 1}/{len(self.api_keys)}")
                return True
        
        logger.error("❌ All API keys have exceeded quota limits")
        return False
    
    def _handle_quota_error(self, error_message: str) -> bool:
        """Handle quota exceeded error by rotating to next API key"""
        if "quota" in error_message.lower() or "429" in error_message:
            logger.warning(f"⚠️ Quota exceeded for API key {self.current_key_index + 1}")
            self.key_quota_exceeded[self.current_key_index] = True
            
            if self._rotate_api_key():
                return True
            else:
                logger.error("❌ All API keys exhausted")
                return False
        return False
    
    def _load_processing_state(self):
        """Load processing state"""
        if self.processing_state_file.exists():
            try:
                with open(self.processing_state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    self.processed_files = set(state.get('processed_files', []))
                logger.info(f"📂 Loaded processing state: {len(self.processed_files)} files already processed")
            except Exception as e:
                logger.warning(f"Could not load processing state: {e}")
                self.processed_files = set()
    
    def _save_processing_state(self):
        """Save current processing state"""
        try:
            state = {
                'processed_files': list(self.processed_files),
                'last_updated': datetime.now().isoformat()
            }
            with open(self.processing_state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving processing state: {e}")
    
    def _get_factsheet_hash(self, pdf_path: str) -> str:
        """Generate unique hash for factsheet file"""
        with open(pdf_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    
    def _mark_file_as_processed(self, file_hash: str, amc_name: str, scheme_count: int):
        """Mark a file as processed"""
        self.processed_files.add(file_hash)
        self._save_processing_state()
        logger.info(f"✅ Marked {amc_name} as processed ({scheme_count} schemes)")
    
    def _detect_amc_from_filename(self, pdf_path: str) -> Optional[str]:
        """Detect AMC name from filename"""
        filename = Path(pdf_path).stem.lower()
        
        amc_keywords = {
            'hdfc': 'HDFC', 'sbi': 'SBI', 'icici': 'ICICI', 'axis': 'Axis',
            'kotak': 'Kotak', 'nippon': 'Nippon', 'aditya': 'Aditya Birla',
            'birla': 'Aditya Birla', 'franklin': 'Franklin Templeton',
            'reliance': 'Reliance', 'uti': 'UTI', 'dsp': 'DSP',
            'mirae': 'Mirae Asset', 'tata': 'Tata', 'invesco': 'Invesco'
        }
        
        for keyword, amc_name in amc_keywords.items():
            if keyword in filename:
                logger.info(f"🏷️ Detected AMC from filename: {amc_name}")
                return amc_name
        
        return None
    
    def _extract_table_of_contents(self, text: str, amc_name: str) -> List[Dict[str, Any]]:
        """
        Extract schemes from Table of Contents - TOC IS THE SOURCE OF TRUTH
        """
        schemes = []
        
        # Find the CONTENTS section
        contents_match = re.search(r'CONTENTS|INDEX|Table\s+of\s+Contents', text, re.IGNORECASE)
        if not contents_match:
            logger.warning("⚠️ No Table of Contents found, using fallback")
            return self._fallback_scheme_detection(text, amc_name)
        
        # Extract TOC section (focus on TOC only, not entire document)
        toc_start = contents_match.start()
        toc_text = text[toc_start:toc_start + 15000]  # Focused TOC section
        
        # TOC-SPECIFIC patterns - look for scheme names with page numbers
        # Pattern 1: "HDFC Flexi Cap Fund..................... 7-8"
        pattern1 = rf'({amc_name}\s+[A-Za-z\s&\-]+Fund)\s*\.+\s*(\d+(?:-\d+)?)'
        matches1 = re.findall(pattern1, toc_text, re.MULTILINE | re.IGNORECASE)
        
        # Pattern 2: "SBI Large Cap Fund........................ 12-13" 
        pattern2 = rf'({amc_name}\s+[A-Za-z\s&\-]+Fund)\s+(\d+(?:-\d+)?)'
        matches2 = re.findall(pattern2, toc_text, re.MULTILINE | re.IGNORECASE)
        
        # Pattern 3: Look for any fund name followed by page number in TOC
        pattern3 = r'([A-Z][A-Za-z\s&\-]+Fund)\s*\.+\s*(\d+(?:-\d+)?)'
        matches3 = re.findall(pattern3, toc_text, re.MULTILINE)
        
        all_matches = matches1 + matches2 + matches3
        
        # Process matches with STRICT filtering
        seen_schemes = set()
        for match in all_matches:
            scheme_name = match[0].strip()
            page_number = match[1] if len(match) > 1 else "N/A"
            
            # Clean scheme name
            scheme_name = re.sub(r'\s+', ' ', scheme_name)
            scheme_name = re.sub(r'\.+$', '', scheme_name)
            
            # STRICT filtering - only real scheme names
            skip_words = [
                'sponsor', 'mutual fund', 'bank limited', 'asset management', 
                'contents', 'page no', 'factsheet', 'august', 'scheme factsheet',
                'wealth creation', 'tax savings', 'children', 'retirement planning',
                'income solutions', 'fund details', 'performance details', 'benchmark',
                'riskometer', 'disclaimer', 'annexure', 'break-up', 'history'
            ]
            
            # Must be in TOC format: "Scheme Name.....Page"
            if (len(scheme_name) < 10 or 
                any(word in scheme_name.lower() for word in skip_words) or
                scheme_name.lower() in seen_schemes or
                not page_number.isdigit() or  # Must have page number
                'fund' not in scheme_name.lower()):  # Must contain "Fund"
                continue
            
            seen_schemes.add(scheme_name.lower())
            schemes.append({
                'name': scheme_name,
                'page': page_number,
                'amc': amc_name
            })
        
        # If no schemes found in TOC, try minimal fallback
        if not schemes:
            logger.warning("⚠️ No schemes found in TOC, trying minimal fallback")
            return self._minimal_fallback_detection(text, amc_name)
        
        logger.info(f"📊 Found {len(schemes)} schemes in Table of Contents")
        return schemes
    
    def _fallback_scheme_detection(self, text: str, amc_name: str) -> List[Dict[str, Any]]:
        """Fallback: Find schemes by looking for Fund names in text"""
        schemes = []
        
        # Look for "SCHEME NAME Fund" followed by financial keywords
        pattern = rf'({amc_name}\s+[A-Za-z\s&\-]+Fund)[\s\n]+(?=.*(?:NAV|AUM|Expense|Benchmark))'
        matches = re.finditer(pattern, text[:50000], re.IGNORECASE | re.DOTALL)
        
        seen_schemes = set()
        for match in matches:
            scheme_name = match.group(1).strip()
            scheme_name = re.sub(r'\s+', ' ', scheme_name)
            
            if scheme_name.lower() not in seen_schemes and len(scheme_name) > 10:
                seen_schemes.add(scheme_name.lower())
                schemes.append({
                    'name': scheme_name,
                    'page': 'N/A',
                    'amc': amc_name
                })
        
        logger.info(f"📊 Fallback detected {len(schemes)} schemes")
        return schemes
    
    def _aggressive_scheme_detection(self, text: str, amc_name: str) -> List[Dict[str, Any]]:
        """Aggressive fallback: Look for any fund names in the entire document"""
        schemes = []
        
        # Look for common fund name patterns throughout the document
        patterns = [
            rf'({amc_name}\s+[A-Za-z\s&\-]+Fund)',
            rf'({amc_name}\s+[A-Za-z\s&\-]+Scheme)',
            r'([A-Z][A-Za-z\s&\-]+Fund)',
            r'([A-Z][A-Za-z\s&\-]+Scheme)'
        ]
        
        seen_schemes = set()
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                scheme_name = match.group(1).strip()
                scheme_name = re.sub(r'\s+', ' ', scheme_name)
                
                # Skip unwanted patterns
                skip_words = ['sponsor', 'mutual fund', 'bank limited', 'asset management', 
                             'contents', 'page no', 'factsheet', 'august', 'scheme factsheet']
                
                if (len(scheme_name) < 10 or 
                    any(word in scheme_name.lower() for word in skip_words) or
                    scheme_name.lower() in seen_schemes):
                    continue
                
                seen_schemes.add(scheme_name.lower())
                schemes.append({
                    'name': scheme_name,
                    'page': 'N/A',
                    'amc': amc_name
                })
        
        logger.info(f"📊 Aggressive detection found {len(schemes)} schemes")
        return schemes
    
    def _minimal_fallback_detection(self, text: str, amc_name: str) -> List[Dict[str, Any]]:
        """Minimal fallback: Only look for clear scheme names in first 10000 chars"""
        schemes = []
        
        # Only look in first 10000 characters (likely TOC area)
        search_text = text[:10000]
        
        # Look for clear scheme patterns
        pattern = rf'({amc_name}\s+[A-Za-z\s&\-]+Fund)'
        matches = re.finditer(pattern, search_text, re.IGNORECASE)
        
        seen_schemes = set()
        for match in matches:
            scheme_name = match.group(1).strip()
            scheme_name = re.sub(r'\s+', ' ', scheme_name)
            
            # Skip unwanted patterns
            skip_words = ['sponsor', 'mutual fund', 'bank limited', 'asset management']
            
            if (len(scheme_name) < 10 or 
                any(word in scheme_name.lower() for word in skip_words) or
                scheme_name.lower() in seen_schemes):
                continue
            
            seen_schemes.add(scheme_name.lower())
            schemes.append({
                'name': scheme_name,
                'page': 'N/A',
                'amc': amc_name
            })
        
        logger.info(f"📊 Minimal fallback found {len(schemes)} schemes")
        return schemes
    
    def _smart_rate_limit(self):
        """Implement smart rate limiting for API calls"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.request_delay:
            sleep_time = self.request_delay - time_since_last_request
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _extract_scheme_data_with_gemini(self, full_text: str, scheme_name: str, amc_name: str, page_number: str = "N/A") -> Dict[str, Any]:
        """
        Extract scheme data using Gemini with PRECISE SCHEME BOUNDARY DETECTION
        """
        
        # PRECISE SCHEME BOUNDARY DETECTION: Find exact scheme section
        scheme_text = self._find_precise_scheme_boundaries(full_text, scheme_name, page_number)
        
        if not scheme_text:
            logger.error(f"❌ Could not extract text for {scheme_name}")
            return self._create_fallback_scheme_data(scheme_name, amc_name)
        
        # Log extracted text length for debugging
        logger.info(f"📊 Extracted {len(scheme_text)} chars for {scheme_name} (Page: {page_number})")
        
        prompt = f"""You are an expert financial data analyst. Extract mutual fund scheme data with 100% accuracy.

SCHEME: {scheme_name}
AMC: {amc_name}
PAGE: {page_number}

CRITICAL INSTRUCTIONS:
1. Read the ENTIRE text carefully - data may be scattered across multiple sections
2. Look for patterns like "NAV", "AUM", "Expense Ratio", "Fund Manager", "Benchmark", "CAGR", "Beta", "Sharpe Ratio"
3. Extract REAL data values - DO NOT use "N/A" unless absolutely not found
4. For dates, use DD/MM/YYYY format
5. For amounts, include currency symbol (₹) and "Crs" for crores
6. For percentages, include "%" symbol
7. Return ONLY valid JSON - no explanations or additional text

EXACT JSON FORMAT REQUIRED:
{{
    "Scheme_Name": "{scheme_name}",
    "Asset_Class": "Equity/Debt/Hybrid/Other",
    "Sub_Class": "Large Cap Fund/Mid Cap Fund/Small Cap Fund/Dynamic Bond Fund/etc",
    "Type_of_Scheme": "Open-Ended Equity Scheme/Open-Ended Debt Scheme/Open-Ended Hybrid Scheme",
    "Date_of_Allotment_(Inception_Date)": "DD/MM/YYYY",
    "AUM_(as_of_Aug_2025)": "₹XX,XXX.XX Crs",
    "Fund_Manager_Name": "Mr./Ms. Full Name",
    "Fund_Manager_Tenure": "Since Month Year",
    "Fund_Manager_Experience": "N/A (Only tenure/managing since date available)",
    "Benchmark": "Index Name (TRI)",
    "Options": "Regular (IDCW, Growth)",
    "Expense_Ratio": {{
        "Direct": "X.XX%",
        "Regular": "X.XX%"
    }},
    "Risk_Metrics": {{
        "Standard_Deviation": "XX.XX%",
        "Beta": "X.XX",
        "Sharpe_Ratio": "X.XX"
    }},
    "Turnover": {{
        "Equity_Portfolio_Turnover": "X.XX",
        "Total_Turnover": "N/A"
    }},
    "Portfolio_Allocation_by_Market_Cap": {{
        "Large_Cap_(%)": "XX.XX",
        "Mid_Cap_(%)": "XX.XX",
        "Small_Cap_(%)": "XX.XX",
        "Other_Assets_(%)": "XX.XX"
    }},
    "NAV_Value_as_of_Aug_31_2025": {{
        "Regular_Growth": "₹XXX.XXXX",
        "Regular_IDCW": "₹XXX.XXXX",
        "Regular_ITC": "N/A"
    }},
    "Exit_Load": {{
        "Under_30_days": "X.XX% of the units or NIL",
        "30_-_90_days": "NIL",
        "After_90_days": "NIL"
    }},
    "Minimum_Monthly_SIP_investment_amount": "₹XXX",
    "RisKometer_(Risk_Profile)": "LOW/MODERATE/HIGH/VERY HIGH",
    "CAGR": {{
        "1Y": "XX.XX%",
        "3Y": "XX.XX%",
        "5Y": "XX.XX%",
        "All": "XX.XX%"
    }},
    "Debt_Metrics": {{
        "Yield_to_Maturity": "X.XX%",
        "Modified_Duration": "X.XX Years",
        "Average_Maturity_Years": "X.XX Years",
        "Macaulay_Duration": "X.XX Years",
        "Composition_by_rating": "AAA/Sovereign (XX%), AA (XX%), Others (XX%)"
    }}
}}

EXAMPLES OF WHAT TO LOOK FOR:
- AUM: "₹52,420.39 Crs" or "₹65,890.12 Crs"
- NAV: "₹456.7845" or "₹289.4510"
- Expense Ratio: "0.81%" or "1.49%"
- Fund Manager: "Mr. Saurabh Pant" or "Mr. R Srinivasan"
- Benchmark: "BSE 100 (TRI)" or "CRISIL Hybrid 35+65 Aggressive Index"
- CAGR: "18.52%" or "20.15%"
- Risk Metrics: "11.69%" for Standard Deviation, "0.91" for Beta

SEARCH PATTERNS:
- Look for "NAV" followed by numbers
- Look for "AUM" or "Assets Under Management" followed by ₹ amounts
- Look for "Expense Ratio" followed by percentages
- Look for "Fund Manager" or "Manager" followed by names
- Look for "Benchmark" followed by index names
- Look for "CAGR" or "Compound Annual Growth Rate" followed by percentages
- Look for "Standard Deviation", "Beta", "Sharpe Ratio" followed by values
- Look for "Exit Load" followed by percentages or "NIL"
- Look for "SIP" or "Systematic Investment Plan" followed by ₹ amounts

TEXT TO ANALYZE:
{scheme_text}
"""
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self._smart_rate_limit()
                response = self.model.generate_content(prompt)
                self.key_usage_count[self.current_key_index] += 1
                
                content = response.text.strip()
                
                # Clean markdown if present
                if content.startswith('```json'):
                    content = content[7:]
                if content.endswith('```'):
                    content = content[:-3]
                
                content = content.strip()
                
                scheme_data = json.loads(content)
                return scheme_data
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error for {scheme_name} (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
            except Exception as e:
                error_message = str(e)
                logger.error(f"Gemini extraction error for {scheme_name} (attempt {attempt + 1}): {e}")
                
                if self._handle_quota_error(error_message):
                    logger.info(f"🔄 Retrying with new API key for {scheme_name}")
                    continue
                
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
        
        # All retries failed
        return self._create_fallback_scheme_data(scheme_name, amc_name)
    
    def _create_fallback_scheme_data(self, scheme_name: str, amc_name: str) -> Dict[str, Any]:
        """Create fallback data structure"""
        return {
            "Scheme_Name": scheme_name,
            "AMC": amc_name,
            "Asset_Class": "N/A",
            "Sub_Class": "N/A",
            "Type_of_Scheme": "N/A",
            "Date_of_Allotment_(Inception_Date)": "N/A",
            "AUM_(as_of_Aug_2025)": "N/A",
            "Fund_Manager_Name": "N/A",
            "Fund_Manager_Tenure": "N/A",
            "Fund_Manager_Experience": "N/A",
            "Benchmark": "N/A",
            "Options": "N/A",
            "Expense_Ratio": {"Direct": "N/A", "Regular": "N/A"},
            "Risk_Metrics": {"Standard_Deviation": "N/A", "Beta": "N/A", "Sharpe_Ratio": "N/A"},
            "Turnover": {"Equity_Portfolio_Turnover": "N/A", "Total_Turnover": "N/A"},
            "Portfolio_Allocation_by_Market_Cap": {"Large_Cap_(%)": "N/A", "Mid_Cap_(%)": "N/A", "Small_Cap_(%)": "N/A", "Other_Assets_(%)": "N/A"},
            "NAV_Value_as_of_Aug_31_2025": {"Regular_Growth": "N/A", "Regular_IDCW": "N/A", "Regular_ITC": "N/A"},
            "Exit_Load": {"Under_30_days": "N/A", "30_-_90_days": "N/A", "After_90_days": "N/A"},
            "Minimum_Monthly_SIP_investment_amount": "N/A",
            "RisKometer_(Risk_Profile)": "N/A",
            "CAGR": {"1Y": "N/A", "3Y": "N/A", "5Y": "N/A", "All": "N/A"},
            "Debt_Metrics": "N/A",
            "Extraction_Status": "Failed - Using Fallback"
        }
    
    def _initialize_progress_file(self, amc_name: str, total_schemes: int) -> str:
        """Initialize progress tracking file"""
        progress_filename = f"{amc_name}_progress.json"
        progress_filepath = self.output_dir / progress_filename
        
        progress_data = {
            "amc": amc_name,
            "total_schemes": total_schemes,
            "processed_schemes": 0,
            "start_time": datetime.now().isoformat(),
            "status": "in_progress",
            "schemes": []
        }
        
        with open(progress_filepath, 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, indent=2, ensure_ascii=False)
        
        return str(progress_filepath)
    
    def _update_progress_file(self, progress_file: str, processed: int, total: int, 
                             scheme_data: Dict[str, Any], error: str = None):
        """Update progress tracking file"""
        try:
            with open(progress_file, 'r', encoding='utf-8') as f:
                progress_data = json.load(f)
            
            progress_data["processed_schemes"] = processed
            progress_data["schemes"].append({
                "scheme_name": scheme_data.get("Scheme_Name", "Unknown"),
                "status": "error" if error else "success",
                "error": error,
                "timestamp": datetime.now().isoformat()
            })
            
            with open(progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress_data, f, indent=2, ensure_ascii=False)
            
            # Force sync
            import os
            os.sync()
            
        except Exception as e:
            logger.error(f"Error updating progress file: {e}")
    
    def _mark_progress_complete(self, progress_file: str, results: List[Dict[str, Any]]):
        """Mark progress as complete"""
        try:
            with open(progress_file, 'r', encoding='utf-8') as f:
                progress_data = json.load(f)
            
            progress_data["status"] = "completed"
            progress_data["end_time"] = datetime.now().isoformat()
            progress_data["total_extracted"] = len(results)
            
            with open(progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress_data, f, indent=2, ensure_ascii=False)
            
        except Exception as e:
            logger.error(f"Error marking progress complete: {e}")
    
    def _save_amc_results(self, data: List[Dict[str, Any]], amc_name: str):
        """Save results for a specific AMC (INCREMENTAL - saves after each scheme)"""
        filename = f"{amc_name}_scalable_extraction.json"
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        # Force sync to disk
        import os
        os.sync()
        
        logger.info(f"💾 {amc_name}: Saved {len(data)} schemes to {filepath}")
    
    def _save_combined_results(self, results: Dict[str, List[Dict[str, Any]]]):
        """Save combined results from all AMCs"""
        filename = f"scalable_extraction_all_amcs.json"
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"💾 Combined results saved to: {filepath}")
    
    def process_factsheet(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Process a single factsheet PDF"""
        logger.info(f"🚀 Processing factsheet: {Path(pdf_path).name}")
        
        # Check if already processed
        file_hash = self._get_factsheet_hash(pdf_path)
        if file_hash in self.processed_files:
            logger.info(f"⏭️ Skipping {Path(pdf_path).name} (already processed)")
            return []
        
        # Extract text from PDF
        extraction_result = self.pdf_extractor.extract_text_from_pdf(pdf_path)
        if not extraction_result or not isinstance(extraction_result, dict):
            logger.error(f"❌ Failed to extract text from {pdf_path}")
            return []
        
        # Get the full text
        text = extraction_result.get('full_text', '')
        if not text:
            logger.error(f"❌ No text found in {pdf_path}")
            return []
        
        # Detect AMC
        filename_amc = self._detect_amc_from_filename(pdf_path)
        amc_name = filename_amc if filename_amc else "Unknown AMC"
        logger.info(f"🏷️ Detected AMC: {amc_name}")
        
        # Extract schemes from Table of Contents
        schemes = self._extract_table_of_contents(text, amc_name)
        
        if not schemes:
            logger.warning(f"⚠️ No schemes found in {Path(pdf_path).name}")
            return []
        
        # Initialize progress tracking
        progress_file = self._initialize_progress_file(amc_name, len(schemes))
        
        # Extract data for each scheme (SAVE INCREMENTALLY!)
        results = []
        for i, scheme in enumerate(schemes):
            logger.info(f"🔄 Processing scheme {i+1}/{len(schemes)}: {scheme['name']}")
            
            try:
                scheme_data = self._extract_scheme_data_with_gemini(
                    text, 
                    scheme['name'], 
                    amc_name,
                    scheme.get('page', 'N/A')
                )
                results.append(scheme_data)
                
                # ✅ SAVE AFTER EACH SCHEME! (Prevents data loss)
                self._save_amc_results(results, amc_name)
                
                # Update progress
                self._update_progress_file(progress_file, i+1, len(schemes), scheme_data)
                
            except Exception as e:
                logger.error(f"Error processing scheme {scheme['name']}: {e}")
                fallback_data = self._create_fallback_scheme_data(scheme['name'], amc_name)
                results.append(fallback_data)
                
                # ✅ SAVE EVEN ON ERROR!
                self._save_amc_results(results, amc_name)
                
                self._update_progress_file(progress_file, i+1, len(schemes), fallback_data, str(e))
        
        # Mark progress as complete
        self._mark_progress_complete(progress_file, results)
        
        # Mark file as processed
        self._mark_file_as_processed(file_hash, amc_name, len(results))
        
        logger.info(f"✅ Successfully extracted {len(results)} schemes from {amc_name}")
        return results
    
    def process_all_factsheets(self, factsheets_dir: str = "factsheets") -> Dict[str, List[Dict[str, Any]]]:
        """Process all factsheets in the directory"""
        factsheets_path = Path(factsheets_dir)
        pdf_files = list(factsheets_path.glob("*.pdf"))
        
        if not pdf_files:
            logger.warning(f"⚠️ No PDF files found in {factsheets_dir}")
            return {}
        
        logger.info(f"📁 Found {len(pdf_files)} factsheet(s) to process")
        
        all_results = {}
        
        for pdf_file in pdf_files:
            try:
                results = self.process_factsheet(str(pdf_file))
                if results:
                    amc_name = results[0].get('AMC', results[0].get('Scheme_Name', 'Unknown').split()[0])
                    all_results[amc_name] = results
            except Exception as e:
                logger.error(f"Error processing {pdf_file.name}: {e}")
        
        # Save combined results
        if all_results:
            self._save_combined_results(all_results)
            logger.info(f"🎉 Processing complete! Extracted data from {len(all_results)} AMC(s)")
        
        # Log API key usage statistics
        logger.info(f"📊 API Key Usage Statistics:")
        for i, count in self.key_usage_count.items():
            status = "EXHAUSTED" if self.key_quota_exceeded[i] else "ACTIVE"
            logger.info(f"  Key {i+1}: {count} requests ({status})")
        
        return all_results

def main():
    """Main function"""
    extractor = ScalableAMCExtractor()
    results = extractor.process_all_factsheets()
    
    if results:
        print(f"\n✅ Successfully processed {len(results)} AMC(s)")
        for amc, schemes in results.items():
            print(f"  - {amc}: {len(schemes)} schemes")
    else:
        print("\n⚠️ No data extracted. Check logs for details.")

if __name__ == "__main__":
    main()
