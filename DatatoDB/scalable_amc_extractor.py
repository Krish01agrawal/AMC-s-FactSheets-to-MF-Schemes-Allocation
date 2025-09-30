#!/usr/bin/env python3
"""
Scalable AMC Factsheet Extractor
Handles 44+ AMCs with automatic detection, resume capability, and deduplication
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
    """Scalable extractor for 44+ AMCs with automatic detection and resume capability"""
    
    def __init__(self):
        load_dotenv()
        
        # Initialize Gemini
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not set in environment variables")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        self.pdf_extractor = AdvancedPDFExtractor()
        
        # Smart rate limiting for Gemini 2.5 Flash (15 requests/min)
        self.request_delay = 4.0  # 4 seconds between requests = 15 requests/min
        self.last_request_time = 0
        
        # AMC detection patterns
        self.amc_patterns = self._initialize_amc_patterns()
        
        # Processing state
        self.processed_files = set()
        self.processing_state_file = Path("output/processing_state.json")
        self._load_processing_state()
        
        # Output directories
        self.output_dir = Path("output")
        self.output_dir.mkdir(exist_ok=True)
        
    def _initialize_amc_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Initialize AMC detection patterns for 44+ AMCs"""
        return {
            # Major AMCs
            'HDFC': {
                'filename_patterns': [r'hdfc', r'housing development'],
                'scheme_patterns': [r'(HDFC\s+[A-Za-z\s&]+(?:Fund|Scheme))\s*\n'],
                'content_indicators': ['HDFC Mutual Fund', 'HDFC Asset Management']
            },
            'SBI': {
                'filename_patterns': [r'sbi', r'state bank'],
                'scheme_patterns': [r'(SBI\s+[A-Za-z\s&]+(?:Fund|Scheme))\s*\n'],
                'content_indicators': ['SBI Mutual Fund', 'SBI Asset Management']
            },
            'ICICI': {
                'filename_patterns': [r'icici'],
                'scheme_patterns': [r'(ICICI\s+[A-Za-z\s&]+(?:Fund|Scheme))\s*\n'],
                'content_indicators': ['ICICI Mutual Fund', 'ICICI Asset Management']
            },
            'Axis': {
                'filename_patterns': [r'axis'],
                'scheme_patterns': [r'(Axis\s+[A-Za-z\s&]+(?:Fund|Scheme))\s*\n'],
                'content_indicators': ['Axis Mutual Fund', 'Axis Asset Management']
            },
            'Kotak': {
                'filename_patterns': [r'kotak'],
                'scheme_patterns': [r'(Kotak\s+[A-Za-z\s&]+(?:Fund|Scheme))\s*\n'],
                'content_indicators': ['Kotak Mutual Fund', 'Kotak Asset Management']
            },
            'Aditya Birla': {
                'filename_patterns': [r'aditya', r'birla', r'absl'],
                'scheme_patterns': [r'(Aditya Birla\s+[A-Za-z\s&]+(?:Fund|Scheme))\s*\n'],
                'content_indicators': ['Aditya Birla Mutual Fund', 'ABSL Mutual Fund']
            },
            'Franklin Templeton': {
                'filename_patterns': [r'franklin', r'templeton'],
                'scheme_patterns': [r'(Franklin\s+[A-Za-z\s&]+(?:Fund|Scheme))\s*\n'],
                'content_indicators': ['Franklin Templeton Mutual Fund']
            },
            'Reliance': {
                'filename_patterns': [r'reliance'],
                'scheme_patterns': [r'(Reliance\s+[A-Za-z\s&]+(?:Fund|Scheme))\s*\n'],
                'content_indicators': ['Reliance Mutual Fund', 'Reliance Asset Management']
            },
            'UTI': {
                'filename_patterns': [r'uti'],
                'scheme_patterns': [r'(UTI\s+[A-Za-z\s&]+(?:Fund|Scheme))\s*\n'],
                'content_indicators': ['UTI Mutual Fund', 'UTI Asset Management']
            },
            'DSP': {
                'filename_patterns': [r'dsp'],
                'scheme_patterns': [r'(DSP\s+[A-Za-z\s&]+(?:Fund|Scheme))\s*\n'],
                'content_indicators': ['DSP Mutual Fund', 'DSP Asset Management']
            },
            'Mirae Asset': {
                'filename_patterns': [r'mirae'],
                'scheme_patterns': [r'(Mirae\s+[A-Za-z\s&]+(?:Fund|Scheme))\s*\n'],
                'content_indicators': ['Mirae Asset Mutual Fund']
            },
            'Nippon': {
                'filename_patterns': [r'nippon'],
                'scheme_patterns': [r'(Nippon\s+[A-Za-z\s&]+(?:Fund|Scheme))\s*\n'],
                'content_indicators': ['Nippon Mutual Fund', 'Nippon Asset Management']
            },
            'Tata': {
                'filename_patterns': [r'tata'],
                'scheme_patterns': [r'(Tata\s+[A-Za-z\s&]+(?:Fund|Scheme))\s*\n'],
                'content_indicators': ['Tata Mutual Fund', 'Tata Asset Management']
            },
            'L&T': {
                'filename_patterns': [r'l&t', r'larsen', r'toubro'],
                'scheme_patterns': [r'(L&T\s+[A-Za-z\s&]+(?:Fund|Scheme))\s*\n'],
                'content_indicators': ['L&T Mutual Fund', 'L&T Asset Management']
            },
            'Invesco': {
                'filename_patterns': [r'invesco'],
                'scheme_patterns': [r'(Invesco\s+[A-Za-z\s&]+(?:Fund|Scheme))\s*\n'],
                'content_indicators': ['Invesco Mutual Fund', 'Invesco Asset Management']
            },
            'HSBC': {
                'filename_patterns': [r'hsbc'],
                'scheme_patterns': [r'(HSBC\s+[A-Za-z\s&]+(?:Fund|Scheme))\s*\n'],
                'content_indicators': ['HSBC Mutual Fund', 'HSBC Asset Management']
            },
            'BNP Paribas': {
                'filename_patterns': [r'bnp', r'paribas'],
                'scheme_patterns': [r'(BNP\s+[A-Za-z\s&]+(?:Fund|Scheme))\s*\n'],
                'content_indicators': ['BNP Paribas Mutual Fund']
            },
            'Baroda': {
                'filename_patterns': [r'baroda'],
                'scheme_patterns': [r'(Baroda\s+[A-Za-z\s&]+(?:Fund|Scheme))\s*\n'],
                'content_indicators': ['Baroda Mutual Fund', 'Baroda Asset Management']
            },
            'Canara Robeco': {
                'filename_patterns': [r'canara', r'robeco'],
                'scheme_patterns': [r'(Canara\s+[A-Za-z\s&]+(?:Fund|Scheme))\s*\n'],
                'content_indicators': ['Canara Robeco Mutual Fund']
            },
            'Edelweiss': {
                'filename_patterns': [r'edelweiss'],
                'scheme_patterns': [r'(Edelweiss\s+[A-Za-z\s&]+(?:Fund|Scheme))\s*\n'],
                'content_indicators': ['Edelweiss Mutual Fund', 'Edelweiss Asset Management']
            },
            'Motilal Oswal': {
                'filename_patterns': [r'motilal', r'oswal'],
                'scheme_patterns': [r'(Motilal\s+[A-Za-z\s&]+(?:Fund|Scheme))\s*\n'],
                'content_indicators': ['Motilal Oswal Mutual Fund']
            },
            'Mahindra': {
                'filename_patterns': [r'mahindra'],
                'scheme_patterns': [r'(Mahindra\s+[A-Za-z\s&]+(?:Fund|Scheme))\s*\n'],
                'content_indicators': ['Mahindra Mutual Fund', 'Mahindra Asset Management']
            },
            'PGIM': {
                'filename_patterns': [r'pgim'],
                'scheme_patterns': [r'(PGIM\s+[A-Za-z\s&]+(?:Fund|Scheme))\s*\n'],
                'content_indicators': ['PGIM Mutual Fund', 'PGIM Asset Management']
            },
            'Quantum': {
                'filename_patterns': [r'quantum'],
                'scheme_patterns': [r'(Quantum\s+[A-Za-z\s&]+(?:Fund|Scheme))\s*\n'],
                'content_indicators': ['Quantum Mutual Fund', 'Quantum Asset Management']
            },
            'Sundaram': {
                'filename_patterns': [r'sundaram'],
                'scheme_patterns': [r'(Sundaram\s+[A-Za-z\s&]+(?:Fund|Scheme))\s*\n'],
                'content_indicators': ['Sundaram Mutual Fund', 'Sundaram Asset Management']
            },
            'Union': {
                'filename_patterns': [r'union'],
                'scheme_patterns': [r'(Union\s+[A-Za-z\s&]+(?:Fund|Scheme))\s*\n'],
                'content_indicators': ['Union Mutual Fund', 'Union Asset Management']
            },
            'WhiteOak': {
                'filename_patterns': [r'whiteoak', r'white oak'],
                'scheme_patterns': [r'(WhiteOak\s+[A-Za-z\s&]+(?:Fund|Scheme))\s*\n'],
                'content_indicators': ['WhiteOak Mutual Fund', 'WhiteOak Asset Management']
            },
            'Bandhan': {
                'filename_patterns': [r'bandhan'],
                'scheme_patterns': [r'(Bandhan\s+[A-Za-z\s&]+(?:Fund|Scheme))\s*\n'],
                'content_indicators': ['Bandhan Mutual Fund', 'Bandhan Asset Management']
            },
            'ITI': {
                'filename_patterns': [r'iti'],
                'scheme_patterns': [r'(ITI\s+[A-Za-z\s&]+(?:Fund|Scheme))\s*\n'],
                'content_indicators': ['ITI Mutual Fund', 'ITI Asset Management']
            },
            'JM Financial': {
                'filename_patterns': [r'jm financial', r'jm'],
                'scheme_patterns': [r'(JM\s+[A-Za-z\s&]+(?:Fund|Scheme))\s*\n'],
                'content_indicators': ['JM Financial Mutual Fund']
            },
            'LIC': {
                'filename_patterns': [r'lic'],
                'scheme_patterns': [r'(LIC\s+[A-Za-z\s&]+(?:Fund|Scheme))\s*\n'],
                'content_indicators': ['LIC Mutual Fund', 'LIC Asset Management']
            },
            'IDFC': {
                'filename_patterns': [r'idfc'],
                'scheme_patterns': [r'(IDFC\s+[A-Za-z\s&]+(?:Fund|Scheme))\s*\n'],
                'content_indicators': ['IDFC Mutual Fund', 'IDFC Asset Management']
            },
            'Indiabulls': {
                'filename_patterns': [r'indiabulls'],
                'scheme_patterns': [r'(Indiabulls\s+[A-Za-z\s&]+(?:Fund|Scheme))\s*\n'],
                'content_indicators': ['Indiabulls Mutual Fund', 'Indiabulls Asset Management']
            },
            'Principal': {
                'filename_patterns': [r'principal'],
                'scheme_patterns': [r'(Principal\s+[A-Za-z\s&]+(?:Fund|Scheme))\s*\n'],
                'content_indicators': ['Principal Mutual Fund', 'Principal Asset Management']
            },
            'PPFAS': {
                'filename_patterns': [r'ppfas'],
                'scheme_patterns': [r'(PPFAS\s+[A-Za-z\s&]+(?:Fund|Scheme))\s*\n'],
                'content_indicators': ['PPFAS Mutual Fund', 'PPFAS Asset Management']
            },
            'Samco': {
                'filename_patterns': [r'samco'],
                'scheme_patterns': [r'(Samco\s+[A-Za-z\s&]+(?:Fund|Scheme))\s*\n'],
                'content_indicators': ['Samco Mutual Fund', 'Samco Asset Management']
            },
            'Taurus': {
                'filename_patterns': [r'taurus'],
                'scheme_patterns': [r'(Taurus\s+[A-Za-z\s&]+(?:Fund|Scheme))\s*\n'],
                'content_indicators': ['Taurus Mutual Fund', 'Taurus Asset Management']
            },
            'Trust': {
                'filename_patterns': [r'trust'],
                'scheme_patterns': [r'(Trust\s+[A-Za-z\s&]+(?:Fund|Scheme))\s*\n'],
                'content_indicators': ['Trust Mutual Fund', 'Trust Asset Management']
            },
            'Truemind': {
                'filename_patterns': [r'truemind'],
                'scheme_patterns': [r'(Truemind\s+[A-Za-z\s&]+(?:Fund|Scheme))\s*\n'],
                'content_indicators': ['Truemind Mutual Fund', 'Truemind Asset Management']
            },
            'Zerodha': {
                'filename_patterns': [r'zerodha'],
                'scheme_patterns': [r'(Zerodha\s+[A-Za-z\s&]+(?:Fund|Scheme))\s*\n'],
                'content_indicators': ['Zerodha Mutual Fund', 'Zerodha Asset Management']
            },
            'Groww': {
                'filename_patterns': [r'groww'],
                'scheme_patterns': [r'(Groww\s+[A-Za-z\s&]+(?:Fund|Scheme))\s*\n'],
                'content_indicators': ['Groww Mutual Fund', 'Groww Asset Management']
            },
            'Upstox': {
                'filename_patterns': [r'upstox'],
                'scheme_patterns': [r'(Upstox\s+[A-Za-z\s&]+(?:Fund|Scheme))\s*\n'],
                'content_indicators': ['Upstox Mutual Fund', 'Upstox Asset Management']
            }
        }
    
    def _load_processing_state(self):
        """Load processing state to resume from where we left off"""
        if self.processing_state_file.exists():
            try:
                with open(self.processing_state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    self.processed_files = set(state.get('processed_files', []))
                    logger.info(f"📊 Loaded processing state: {len(self.processed_files)} files already processed")
            except Exception as e:
                logger.error(f"Error loading processing state: {e}")
                self.processed_files = set()
        else:
            self.processed_files = set()
    
    def _save_processing_state(self):
        """Save processing state for resume capability"""
        try:
            state = {
                'processed_files': list(self.processed_files),
                'last_updated': datetime.now().isoformat()
            }
            with open(self.processing_state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving processing state: {e}")
    
    def _detect_amc_from_filename(self, filename: str) -> Optional[str]:
        """Detect AMC from filename"""
        filename_lower = filename.lower()
        
        for amc_name, patterns in self.amc_patterns.items():
            for pattern in patterns['filename_patterns']:
                if re.search(pattern, filename_lower):
                    return amc_name
        
        return None
    
    def _detect_amc_from_content(self, text: str) -> Optional[str]:
        """Detect AMC from PDF content"""
        text_lower = text.lower()
        
        for amc_name, patterns in self.amc_patterns.items():
            for indicator in patterns['content_indicators']:
                if indicator.lower() in text_lower:
                    return amc_name
        
        return None
    
    def _detect_amc(self, pdf_path: str, text: str) -> str:
        """Detect AMC from filename and content"""
        filename = Path(pdf_path).name
        
        # Try filename first
        amc_from_filename = self._detect_amc_from_filename(filename)
        if amc_from_filename:
            logger.info(f"🏷️ Detected AMC from filename: {amc_from_filename}")
            return amc_from_filename
        
        # Try content
        amc_from_content = self._detect_amc_from_content(text)
        if amc_from_content:
            logger.info(f"🏷️ Detected AMC from content: {amc_from_content}")
            return amc_from_content
        
        # Fallback to filename-based detection
        logger.warning(f"⚠️ Could not detect AMC for {filename}, using filename-based detection")
        return self._extract_amc_name_from_filename(filename)
    
    def _extract_amc_name_from_filename(self, filename: str) -> str:
        """Extract AMC name from filename as fallback"""
        filename_lower = filename.lower()
        
        # Common patterns
        if 'hdfc' in filename_lower:
            return 'HDFC'
        elif 'sbi' in filename_lower:
            return 'SBI'
        elif 'icici' in filename_lower:
            return 'ICICI'
        elif 'axis' in filename_lower:
            return 'Axis'
        elif 'kotak' in filename_lower:
            return 'Kotak'
        else:
            # Extract first word as AMC name
            first_word = filename.split()[0]
            return first_word.upper()
    
    def _get_file_hash(self, file_path: str) -> str:
        """Get file hash for deduplication"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception as e:
            logger.error(f"Error calculating file hash: {e}")
            return str(os.path.getmtime(file_path))
    
    def _is_file_processed(self, file_path: str) -> bool:
        """Check if file has been processed"""
        file_hash = self._get_file_hash(file_path)
        return file_hash in self.processed_files
    
    def _mark_file_processed(self, file_path: str):
        """Mark file as processed"""
        file_hash = self._get_file_hash(file_path)
        self.processed_files.add(file_hash)
        self._save_processing_state()
    
    def _smart_rate_limit(self):
        """Smart rate limiting to stay within Gemini 2.5 Flash limits"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.request_delay:
            sleep_time = self.request_delay - time_since_last
            logger.info(f"⏳ Rate limiting: waiting {sleep_time:.1f}s (15 requests/min limit)")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _split_schemes_by_amc(self, text: str, amc_name: str) -> List[Dict[str, str]]:
        """Split schemes based on AMC-specific patterns"""
        schemes = []
        
        if amc_name in self.amc_patterns:
            patterns = self.amc_patterns[amc_name]['scheme_patterns']
        else:
            # Generic pattern for unknown AMCs
            patterns = [r'([A-Z][A-Za-z\s&]+(?:Fund|Scheme))\s*\n']
        
        # Find all scheme matches
        all_matches = []
        for pattern in patterns:
            matches = list(re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE))
            all_matches.extend(matches)
        
        # Sort matches by position
        all_matches.sort(key=lambda x: x.start())
        
        # Process each match
        for i, match in enumerate(all_matches):
            scheme_name = match.group(1).strip()
            
            # Clean scheme name
            scheme_name = re.sub(r'\s+', ' ', scheme_name)
            scheme_name = re.sub(r'[^\w\s&\.\-]', '', scheme_name)
            
            # Skip if too short or contains unwanted words
            skip_words = [
                'page', 'contd', 'continued', 'glossary', 'disclaimer', 'risk', 'warning',
                'sponsor', 'bank limited', 'mutual fund', 'terms and conditions', 'contact',
                'registrar', 'transfer agent', 'fund manager profile', 'investment objective'
            ]
            
            if (len(scheme_name) < 5 or 
                any(word in scheme_name.lower() for word in skip_words)):
                continue
            
            # Find the text block for this scheme
            start_pos = match.end()
            end_pos = len(text)
            
            if i + 1 < len(all_matches):
                next_match = all_matches[i + 1]
                next_scheme_name = next_match.group(1).strip()
                
                # Skip if same scheme name
                if scheme_name.lower() == next_scheme_name.lower():
                    continue
                
                end_pos = next_match.start()
            
            # Extract scheme text
            scheme_text = text[start_pos:end_pos].strip()
            
            # Enhanced validation for meaningful scheme content
            if self._is_valid_scheme_content(scheme_text, scheme_name):
                schemes.append({
                    'name': scheme_name,
                    'text': scheme_text,
                    'amc': amc_name
                })
        
        return schemes
    
    def _is_valid_scheme_content(self, text: str, scheme_name: str) -> bool:
        """Validate if the extracted text contains meaningful scheme data"""
        if len(text) < 500:  # Minimum content length
            return False
        
        # Check for key financial data indicators
        financial_indicators = [
            r'NAV', r'AUM', r'Expense\s+Ratio', r'Fund\s+Manager',
            r'Benchmark', r'Risk', r'Return', r'Performance',
            r'Asset\s+Allocation', r'Portfolio', r'Investment',
            r'CAGR', r'Beta', r'Sharpe', r'Standard\s+Deviation'
        ]
        
        indicator_count = 0
        for indicator in financial_indicators:
            if re.search(indicator, text, re.IGNORECASE):
                indicator_count += 1
        
        # Must have at least 3 financial indicators
        return indicator_count >= 3
    
    def _extract_scheme_data_with_gemini(self, scheme_text: str, scheme_name: str, amc_name: str) -> Dict[str, Any]:
        """Extract all data points for a scheme using Gemini 2.5 Flash"""
        
        prompt = f"""
        You are an expert financial data analyst specializing in mutual fund factsheet analysis.
        Extract ALL data points from the following scheme information with 100% accuracy.
        
        CRITICAL INSTRUCTIONS:
        1. Read the ENTIRE text carefully - data may be scattered across multiple sections
        2. Look for patterns like "NAV", "AUM", "Expense Ratio", "Fund Manager", "Benchmark"
        3. If data is not found, use "N/A" - DO NOT make up values
        4. For dates, use DD/MM/YYYY format
        5. For amounts, include currency symbol (₹) and "Crs" for crores
        6. For percentages, include "%" symbol
        7. Return ONLY valid JSON - no explanations or additional text
        8. Focus on extracting REAL data, not placeholder values
        
        SCHEME NAME: {scheme_name}
        AMC: {amc_name}
        
        SCHEME TEXT:
        {scheme_text}
        
        Extract the following data points and return ONLY a valid JSON object:
        
        {{
            "Scheme_Name": "exact scheme name from factsheet",
            "Asset_Class": "Equity/Debt/Hybrid/Other",
            "Sub_Class": "Large Cap/Mid Cap/Small Cap/Corporate Bond/etc",
            "Type_of_Scheme": "full scheme description",
            "Date_of_Allotment_(Inception_Date)": "DD/MM/YYYY format",
            "AUM_(as_of_Aug_2025)": "₹X,XXX.XX Crs format",
            "Fund_Manager_Name": "fund manager name(s)",
            "Fund_Manager_Tenure": "Since MMM YYYY format",
            "Fund_Manager_Experience": "N/A (Only tenure/managing since date available) or actual years",
            "Benchmark": "benchmark name",
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
                "Total_Turnover": "X.XX or N/A"
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
                "Regular_ITC": "₹XXX.XXXX or N/A"
            }},
            "Exit_Load": {{
                "Under_30_days": "X.XX% of the units",
                "30_-_90_days": "X.XX% or NIL",
                "After_90_days": "X.XX% or NIL"
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
            }} or "N/A (Equity Fund)"
        }}
        
        CRITICAL INSTRUCTIONS:
        1. Extract ONLY data that is clearly visible in the text
        2. Use "N/A" for missing data, not null or empty strings
        3. Follow the EXACT field names and format shown above
        4. Return ONLY the JSON object, no additional text
        5. Be extremely accurate with financial data
        6. For percentages, include the % symbol (e.g., "1.49%")
        7. For currency, include ₹ symbol (e.g., "₹52,420.39 Crs")
        8. For dates, use DD/MM/YYYY format
        9. For fund managers, extract all managers if multiple
        10. For debt funds, provide debt metrics; for equity funds, use "N/A (Equity Fund)"
        11. For market cap allocation, provide percentages for Large/Mid/Small cap
        12. For exit load, use "NIL" for no charges, "X.XX% of the units" for charges
        13. For riskometer, use: LOW, MODERATE, HIGH, or VERY HIGH
        14. For CAGR, provide percentages with % symbol
        15. For NAV values, include ₹ symbol and 4 decimal places
        """
        
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                self._smart_rate_limit()
                response = self.model.generate_content(prompt)
                
                # Parse the JSON response
                content = response.text.strip()
                
                # Clean the response (remove any markdown formatting)
                if content.startswith('```json'):
                    content = content[7:]
                if content.endswith('```'):
                    content = content[:-3]
                
                scheme_data = json.loads(content)
                
                # Validate extraction quality
                if self._validate_extraction_quality(scheme_data, scheme_name):
                    return scheme_data
                else:
                    logger.warning(f"Low quality extraction for {scheme_name}, attempt {attempt + 1}")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        continue
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error for scheme {scheme_name} (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
            except Exception as e:
                logger.error(f"Gemini extraction error for scheme {scheme_name} (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
        
        # All retries failed, return fallback
        return self._create_fallback_scheme_data(scheme_name, amc_name)
    
    def _validate_extraction_quality(self, result: Dict[str, Any], scheme_name: str) -> bool:
        """Validate the quality of extracted data"""
        if not result:
            return False
        
        # Check for critical fields
        critical_fields = ["Asset_Class", "Sub_Class", "Type_of_Scheme"]
        na_count = sum(1 for field in critical_fields if result.get(field) == "N/A")
        
        # If more than 1 critical field is N/A, consider it low quality
        return na_count <= 1
    
    def _create_fallback_scheme_data(self, scheme_name: str, amc_name: str) -> Dict[str, Any]:
        """Create fallback data structure when Gemini extraction fails"""
        return {
            "Scheme_Name": scheme_name,
            "Asset_Class": "N/A",
            "Sub_Class": "N/A",
            "Type_of_Scheme": "N/A",
            "Date_of_Allotment_(Inception_Date)": "N/A",
            "AUM_(as_of_Aug_2025)": "N/A",
            "Fund_Manager_Name": "N/A",
            "Fund_Manager_Tenure": "N/A",
            "Fund_Manager_Experience": "N/A",
            "Benchmark": "N/A",
            "Options": "Regular (IDCW, Growth)",
            "Expense_Ratio": {
                "Direct": "N/A",
                "Regular": "N/A"
            },
            "Risk_Metrics": {
                "Standard_Deviation": "N/A",
                "Beta": "N/A",
                "Sharpe_Ratio": "N/A"
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
                "Regular_Growth": "N/A",
                "Regular_IDCW": "N/A",
                "Regular_ITC": "N/A"
            },
            "Exit_Load": {
                "Under_30_days": "N/A",
                "30_-_90_days": "N/A",
                "After_90_days": "N/A"
            },
            "Minimum_Monthly_SIP_investment_amount": "N/A",
            "RisKometer_(Risk_Profile)": "N/A",
            "CAGR": {
                "1Y": "N/A",
                "3Y": "N/A",
                "5Y": "N/A",
                "All": "N/A"
            },
            "Debt_Metrics": "N/A"
        }
    
    def process_factsheet(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Process a single factsheet with automatic AMC detection"""
        logger.info(f"🚀 Processing factsheet: {Path(pdf_path).name}")
        
        # Check if already processed
        if self._is_file_processed(pdf_path):
            logger.info(f"⏭️ Skipping already processed file: {Path(pdf_path).name}")
            return []
        
        # Extract text from PDF
        extracted_data = self.pdf_extractor.extract_text_from_pdf(pdf_path)
        full_text = extracted_data.get('full_text', '')
        
        if not full_text:
            logger.error(f"No text extracted from {pdf_path}")
            return []
        
        # Detect AMC
        amc_name = self._detect_amc(pdf_path, full_text)
        logger.info(f"🏷️ Detected AMC: {amc_name}")
        
        # Split into schemes
        schemes = self._split_schemes_by_amc(full_text, amc_name)
        logger.info(f"📊 Found {len(schemes)} schemes in {amc_name}")
        
        if not schemes:
            logger.warning(f"No schemes detected in {pdf_path}")
            return []
        
        # Initialize progress tracking for this AMC
        progress_file = self._initialize_progress_file(amc_name, len(schemes))
        
        # Extract data for each scheme
        results = []
        for i, scheme in enumerate(schemes):
            logger.info(f"🔄 Processing scheme {i+1}/{len(schemes)}: {scheme['name']}")
            
            try:
                scheme_data = self._extract_scheme_data_with_gemini(
                    scheme['text'], 
                    scheme['name'], 
                    amc_name
                )
                results.append(scheme_data)
                
                # Update progress tracking with real-time updates
                self._update_progress_file(progress_file, i+1, len(schemes), scheme_data)
                
                # Force file system sync for real-time updates
                import os
                os.sync()
                
            except Exception as e:
                logger.error(f"Error processing scheme {scheme['name']}: {e}")
                fallback_data = self._create_fallback_scheme_data(scheme['name'], amc_name)
                results.append(fallback_data)
                
                # Update progress tracking with error
                self._update_progress_file(progress_file, i+1, len(schemes), fallback_data, str(e))
                
                # Force file system sync for real-time updates
                import os
                os.sync()
        
        # Mark progress as complete
        self._mark_progress_complete(progress_file, results)
        
        # Mark file as processed
        self._mark_file_processed(pdf_path)
        
        logger.info(f"✅ Successfully extracted {len(results)} schemes from {amc_name}")
        return results
    
    def process_all_factsheets(self, factsheet_dir: str = "factsheets") -> Dict[str, List[Dict[str, Any]]]:
        """Process all factsheets with automatic AMC detection and resume capability"""
        logger.info("🚀 Starting scalable AMC extraction...")
        
        factsheet_path = Path(factsheet_dir)
        if not factsheet_path.exists():
            logger.error(f"Factsheet directory {factsheet_dir} does not exist")
            return {}
        
        # Find all PDF files
        pdf_files = list(factsheet_path.glob("*.pdf"))
        logger.info(f"📁 Found {len(pdf_files)} PDF files")
        
        # Filter out already processed files
        new_pdf_files = [f for f in pdf_files if not self._is_file_processed(str(f))]
        logger.info(f"📊 New files to process: {len(new_pdf_files)}")
        
        if not new_pdf_files:
            logger.info("✅ All files have been processed!")
            return {}
        
        # Process each factsheet
        all_results = {}
        for pdf_file in new_pdf_files:
            try:
                # Process the factsheet (progress tracking is handled inside process_factsheet)
                schemes = self.process_factsheet(str(pdf_file))
                
                # Get AMC name for organizing results
                amc_name = self._detect_amc(str(pdf_file), "")
                
                if amc_name not in all_results:
                    all_results[amc_name] = []
                all_results[amc_name].extend(schemes)
                
                # Save individual AMC results
                self._save_amc_results(schemes, amc_name)
                
            except Exception as e:
                logger.error(f"Error processing {pdf_file.name}: {e}")
        
        # Save combined results
        self._save_combined_results(all_results)
        
        logger.info(f"🎉 Scalable extraction completed!")
        logger.info(f"📊 Total AMCs processed: {len(all_results)}")
        
        for amc, schemes in all_results.items():
            logger.info(f"   {amc}: {len(schemes)} schemes")
        
        return all_results
    
    def _save_amc_results(self, data: List[Dict[str, Any]], amc_name: str):
        """Save results for a specific AMC (single file per AMC)"""
        filename = f"{amc_name}_scalable_extraction.json"
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"💾 {amc_name} results saved to: {filepath}")
    
    def _save_combined_results(self, results: Dict[str, List[Dict[str, Any]]]):
        """Save combined results from all AMCs (single file)"""
        filename = f"scalable_extraction_all_amcs.json"
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"💾 Combined results saved to: {filepath}")
    
    def _initialize_progress_file(self, amc_name: str, total_schemes: int) -> str:
        """Initialize progress tracking file for an AMC (single file per AMC)"""
        progress_filename = f"{amc_name}_progress.json"
        progress_filepath = self.output_dir / progress_filename
        
        progress_data = {
            "amc_name": amc_name,
            "total_schemes": total_schemes,
            "processed_schemes": 0,
            "current_scheme": 0,
            "status": "processing",
            "start_time": datetime.now().isoformat(),
            "schemes": []
        }
        
        with open(progress_filepath, 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"📊 Progress tracking initialized: {progress_filepath}")
        return str(progress_filepath)
    
    def _update_progress_file(self, progress_file: str, current: int, total: int, scheme_data: Dict[str, Any], error: Optional[str] = None):
        """Update progress tracking file"""
        try:
            with open(progress_file, 'r', encoding='utf-8') as f:
                progress_data = json.load(f)
            
            progress_data["processed_schemes"] = current
            progress_data["current_scheme"] = current
            progress_data["last_updated"] = datetime.now().isoformat()
            
            if error:
                progress_data["last_error"] = error
                progress_data["status"] = "error"
            else:
                progress_data["schemes"].append(scheme_data)
                progress_data["status"] = "processing"
            
            with open(progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"📈 Progress: {current}/{total} schemes processed for {progress_data['amc_name']}")
            
        except Exception as e:
            logger.error(f"Error updating progress file: {e}")
    
    def _mark_progress_complete(self, progress_file: str, all_results: List[Dict[str, Any]]):
        """Mark progress as complete"""
        try:
            with open(progress_file, 'r', encoding='utf-8') as f:
                progress_data = json.load(f)
            
            progress_data["status"] = "completed"
            progress_data["end_time"] = datetime.now().isoformat()
            progress_data["total_extracted"] = len(all_results)
            progress_data["schemes"] = all_results
            
            with open(progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ Progress completed: {progress_data['amc_name']} - {len(all_results)} schemes extracted")
            
        except Exception as e:
            logger.error(f"Error marking progress complete: {e}")

def main():
    """Main function to run scalable extraction"""
    try:
        extractor = ScalableAMCExtractor()
        results = extractor.process_all_factsheets()
        
        total_schemes = sum(len(schemes) for schemes in results.values())
        logger.info(f"🎉 Scalable extraction completed!")
        logger.info(f"📊 Total schemes extracted: {total_schemes}")
        logger.info(f"📊 Total AMCs processed: {len(results)}")
        
        for amc, schemes in results.items():
            logger.info(f"   {amc}: {len(schemes)} schemes")
        
    except Exception as e:
        logger.error(f"Error in main: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
