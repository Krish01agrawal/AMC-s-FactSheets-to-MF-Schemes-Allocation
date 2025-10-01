#!/usr/bin/env python3
"""
Precise Scheme Data Extractor
Uses intelligent scheme boundary detection for accurate data extraction
"""

import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from advanced_pdf_extractor import AdvancedPDFExtractor
import google.generativeai as genai
from dotenv import load_dotenv
import os
import time

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PreciseSchemeExtractor:
    """
    Precise scheme data extractor with intelligent boundary detection
    """
    
    def __init__(self):
        self.pdf_extractor = AdvancedPDFExtractor()
        self.output_dir = Path("output")
        self.output_dir.mkdir(exist_ok=True)
        
        # Configure Gemini
        api_key = os.getenv('GEMINI_API_KEY')
        if api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-2.5-flash')
        else:
            logger.error("GEMINI_API_KEY not found in environment")
            self.model = None
    
    def find_scheme_boundaries(self, full_text: str, scheme_name: str, page_number: str = "N/A") -> Tuple[int, int]:
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
            return -1, -1
        
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
        
        return scheme_start, scheme_end
    
    def extract_scheme_text(self, full_text: str, scheme_name: str, page_number: str = "N/A") -> str:
        """
        Extract precise text section for a scheme
        """
        start, end = self.find_scheme_boundaries(full_text, scheme_name, page_number)
        
        if start == -1 or end == -1:
            logger.error(f"❌ Could not extract text for {scheme_name}")
            return ""
        
        scheme_text = full_text[start:end]
        logger.info(f"📊 Extracted {len(scheme_text)} chars for {scheme_name}")
        
        return scheme_text
    
    def validate_scheme_text(self, text: str, scheme_name: str) -> bool:
        """
        Validate that extracted text is relevant to the scheme
        """
        # Check for key financial indicators
        financial_indicators = [
            'NAV', 'AUM', 'Expense Ratio', 'Fund Manager', 'Benchmark',
            'CAGR', 'Standard Deviation', 'Beta', 'Sharpe Ratio'
        ]
        
        found_indicators = sum(1 for indicator in financial_indicators if indicator.lower() in text.lower())
        
        # Check for scheme name in text
        scheme_found = scheme_name.lower() in text.lower()
        
        # Check for portfolio holdings (should be minimal in scheme factsheet)
        portfolio_indicators = ['portfolio', 'holdings', 'allocation', 'company']
        portfolio_found = sum(1 for indicator in portfolio_indicators if indicator.lower() in text.lower())
        
        # Valid if: has scheme name, has financial indicators, minimal portfolio content
        is_valid = (
            scheme_found and 
            found_indicators >= 3 and 
            portfolio_found <= 2 and
            len(text) > 1000
        )
        
        logger.info(f"🔍 Validation: scheme_found={scheme_found}, indicators={found_indicators}, portfolio={portfolio_found}, valid={is_valid}")
        
        return is_valid
    
    def extract_with_enhanced_llm(self, text: str, scheme_name: str, amc_name: str) -> Dict[str, Any]:
        """
        Extract data using enhanced LLM prompt with validation
        """
        if not self.model:
            return {}
        
        # Validate text first
        if not self.validate_scheme_text(text, scheme_name):
            logger.warning(f"⚠️ Text validation failed for {scheme_name}")
            return {}
        
        # Enhanced prompt with specific instructions
        prompt = f"""You are an expert financial data analyst. Extract mutual fund scheme data with 100% accuracy.

SCHEME: {scheme_name}
AMC: {amc_name}

CRITICAL INSTRUCTIONS:
1. Read the ENTIRE text carefully - data may be scattered across multiple sections
2. Look for patterns like "NAV", "AUM", "Expense Ratio", "Fund Manager", "Benchmark"
3. Extract REAL data values - DO NOT use "N/A" unless absolutely not found
4. For dates, use DD/MM/YYYY format
5. For amounts, include currency symbol (₹) and "Crs" for crores
6. For percentages, include "%" symbol
7. Return ONLY valid JSON - no explanations or additional text

EXTRACT THESE SPECIFIC FIELDS:
{{
    "AUM": "₹XX,XXX.XX Crs",
    "NAV_Growth": "₹XXX.XXXX",
    "NAV_IDCW": "₹XXX.XXXX", 
    "Expense_Ratio_Direct": "X.XX%",
    "Expense_Ratio_Regular": "X.XX%",
    "Fund_Manager": "Mr. Full Name",
    "Benchmark": "Index Name (TRI)",
    "CAGR_1Y": "XX.XX%",
    "CAGR_3Y": "XX.XX%",
    "CAGR_5Y": "XX.XX%",
    "Standard_Deviation": "XX.XX%",
    "Beta": "X.XX",
    "Sharpe_Ratio": "X.XX",
    "Exit_Load": "X.XX% or NIL",
    "SIP_Minimum": "₹XXX",
    "Date_Allotment": "DD/MM/YYYY"
}}

SEARCH PATTERNS:
- Look for "NAV" followed by numbers
- Look for "AUM" or "Assets Under Management" followed by ₹ amounts
- Look for "Expense Ratio" followed by percentages
- Look for "Fund Manager" or "Manager" followed by names
- Look for "Benchmark" followed by index names
- Look for "CAGR" or "Compound Annual Growth Rate" followed by percentages
- Look for "Standard Deviation", "Beta", "Sharpe Ratio" followed by values

TEXT TO ANALYZE:
{text}
"""
        
        try:
            response = self.model.generate_content(prompt)
            if response.text:
                # Clean response and extract JSON
                json_text = response.text.strip()
                if json_text.startswith('```json'):
                    json_text = json_text[7:]
                if json_text.endswith('```'):
                    json_text = json_text[:-3]
                
                result = json.loads(json_text)
                logger.info(f"✅ LLM extracted {len([v for v in result.values() if v != 'N/A'])} fields")
                return result
        except Exception as e:
            logger.error(f"❌ LLM extraction error: {e}")
        
        return {}
    
    def format_to_schema(self, data: Dict[str, Any], scheme_name: str, amc_name: str) -> Dict[str, Any]:
        """
        Format extracted data to match expected schema
        """
        return {
            "Scheme_Name": scheme_name,
            "Asset_Class": self.determine_asset_class(scheme_name),
            "Sub_Class": self.determine_sub_class(scheme_name),
            "Type_of_Scheme": self.determine_scheme_type(scheme_name),
            "Date_of_Allotment_(Inception_Date)": data.get("Date_Allotment", "N/A"),
            "AUM_(as_of_Aug_2025)": data.get("AUM", "N/A"),
            "Fund_Manager_Name": data.get("Fund_Manager", "N/A"),
            "Fund_Manager_Tenure": "N/A",
            "Fund_Manager_Experience": "N/A",
            "Benchmark": data.get("Benchmark", "N/A"),
            "Options": "Regular (IDCW, Growth)",
            "Expense_Ratio": {
                "Direct": data.get("Expense_Ratio_Direct", "N/A"),
                "Regular": data.get("Expense_Ratio_Regular", "N/A")
            },
            "Risk_Metrics": {
                "Standard_Deviation": data.get("Standard_Deviation", "N/A"),
                "Beta": data.get("Beta", "N/A"),
                "Sharpe_Ratio": data.get("Sharpe_Ratio", "N/A")
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
                "Regular_Growth": data.get("NAV_Growth", "N/A"),
                "Regular_IDCW": data.get("NAV_IDCW", "N/A"),
                "Regular_ITC": "N/A"
            },
            "Exit_Load": {
                "Under_30_days": data.get("Exit_Load", "N/A"),
                "30_-_90_days": "NIL",
                "After_90_days": "NIL"
            },
            "Minimum_Monthly_SIP_investment_amount": data.get("SIP_Minimum", "N/A"),
            "RisKometer_(Risk_Profile)": "N/A",
            "CAGR": {
                "1Y": data.get("CAGR_1Y", "N/A"),
                "3Y": data.get("CAGR_3Y", "N/A"),
                "5Y": data.get("CAGR_5Y", "N/A"),
                "All": "N/A"
            },
            "Debt_Metrics": "N/A (Equity Fund)"
        }
    
    def determine_asset_class(self, scheme_name: str) -> str:
        """Determine asset class from scheme name"""
        name_lower = scheme_name.lower()
        if 'debt' in name_lower or 'bond' in name_lower or 'gilt' in name_lower:
            return "Debt"
        elif 'hybrid' in name_lower or 'balanced' in name_lower:
            return "Hybrid"
        else:
            return "Equity"
    
    def determine_sub_class(self, scheme_name: str) -> str:
        """Determine sub-class from scheme name"""
        name_lower = scheme_name.lower()
        if 'large cap' in name_lower:
            return "Large Cap Fund"
        elif 'mid cap' in name_lower:
            return "Mid Cap Fund"
        elif 'small cap' in name_lower:
            return "Small Cap Fund"
        elif 'flexi' in name_lower:
            return "Flexi Cap Fund"
        elif 'multi cap' in name_lower:
            return "Multi Cap Fund"
        elif 'hybrid' in name_lower:
            return "Hybrid Fund"
        elif 'debt' in name_lower:
            return "Debt Fund"
        else:
            return "Equity Fund"
    
    def determine_scheme_type(self, scheme_name: str) -> str:
        """Determine scheme type"""
        asset_class = self.determine_asset_class(scheme_name)
        if asset_class == "Equity":
            return "Open-Ended Equity Scheme"
        elif asset_class == "Debt":
            return "Open-Ended Debt Scheme"
        elif asset_class == "Hybrid":
            return "Open-Ended Hybrid Scheme"
        else:
            return "Open-Ended Scheme"

def main():
    """Test the precise extractor"""
    extractor = PreciseSchemeExtractor()
    
    # Test with SBI factsheet
    pdf_path = "factsheets/AL Scheme factsheet August_SBI.pdf"
    
    # Extract text
    extraction_result = extractor.pdf_extractor.extract_text_from_pdf(pdf_path)
    full_text = extraction_result.get('full_text', '')
    
    # Test extraction for a specific scheme
    scheme_name = "SBI Large Cap Fund"
    amc_name = "SBI"
    page_number = "04"
    
    # Extract precise scheme text
    scheme_text = extractor.extract_scheme_text(full_text, scheme_name, page_number)
    
    if scheme_text:
        # Extract data using LLM
        result = extractor.extract_with_enhanced_llm(scheme_text, scheme_name, amc_name)
        
        if result:
            # Format to schema
            formatted_result = extractor.format_to_schema(result, scheme_name, amc_name)
            
            # Save result
            output_file = extractor.output_dir / "precise_test_result.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(formatted_result, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ Precise extraction completed. Saved to {output_file}")
            
            # Count non-N/A values
            non_na_count = sum(1 for v in str(formatted_result).split('"') if v.strip() and v.strip() != 'N/A')
            logger.info(f"📊 Found {non_na_count} non-N/A values")
        else:
            logger.error("❌ LLM extraction failed")
    else:
        logger.error("❌ Could not extract scheme text")

if __name__ == "__main__":
    main()
