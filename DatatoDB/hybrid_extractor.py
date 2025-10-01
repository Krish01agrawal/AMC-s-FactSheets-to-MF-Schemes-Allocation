#!/usr/bin/env python3
"""
Hybrid Rule-Based + LLM Data Extractor
Combines regex patterns with LLM for maximum accuracy
"""

import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
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

class HybridDataExtractor:
    """
    Hybrid approach combining rule-based extraction with LLM for maximum accuracy
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
        
        # Rule-based patterns for common data points
        self.patterns = {
            'aum': [
                r'AUM.*?₹[\d,]+\.?\d*\s*[Cc]r',
                r'Assets Under Management.*?₹[\d,]+\.?\d*\s*[Cc]r',
                r'Fund Size.*?₹[\d,]+\.?\d*\s*[Cc]r',
                r'₹[\d,]+\.?\d*\s*[Cc]r.*?AUM',
                r'₹[\d,]+\.?\d*\s*[Cc]r.*?Assets'
            ],
            'nav': [
                r'NAV.*?₹[\d,]+\.?\d*',
                r'Net Asset Value.*?₹[\d,]+\.?\d*',
                r'₹[\d,]+\.?\d*.*?NAV'
            ],
            'expense_ratio': [
                r'Expense Ratio.*?(\d+\.\d+)%',
                r'Total Expense Ratio.*?(\d+\.\d+)%',
                r'(\d+\.\d+)%.*?Expense'
            ],
            'fund_manager': [
                r'Fund Manager.*?Mr\.\s+[A-Za-z\s]+',
                r'Manager.*?Mr\.\s+[A-Za-z\s]+',
                r'Mr\.\s+[A-Za-z\s]+.*?Manager'
            ],
            'benchmark': [
                r'Benchmark.*?[A-Za-z\s]+\(TRI\)',
                r'Index.*?[A-Za-z\s]+\(TRI\)',
                r'[A-Za-z\s]+\(TRI\).*?Benchmark'
            ],
            'cagr': [
                r'CAGR.*?(\d+\.\d+)%',
                r'(\d+\.\d+)%.*?CAGR',
                r'Compound Annual Growth Rate.*?(\d+\.\d+)%'
            ],
            'standard_deviation': [
                r'Standard Deviation.*?(\d+\.\d+)%',
                r'(\d+\.\d+)%.*?Standard Deviation'
            ],
            'beta': [
                r'Beta.*?(\d+\.\d+)',
                r'(\d+\.\d+).*?Beta'
            ],
            'sharpe_ratio': [
                r'Sharpe Ratio.*?(\d+\.\d+)',
                r'(\d+\.\d+).*?Sharpe Ratio'
            ],
            'exit_load': [
                r'Exit Load.*?(\d+\.\d+)%',
                r'(\d+\.\d+)%.*?Exit Load',
                r'Exit Load.*?NIL'
            ],
            'sip_amount': [
                r'SIP.*?₹(\d+)',
                r'₹(\d+).*?SIP',
                r'Minimum.*?₹(\d+)'
            ],
            'date_of_allotment': [
                r'Date of Allotment.*?(\d{2}/\d{2}/\d{4})',
                r'Inception Date.*?(\d{2}/\d{2}/\d{4})',
                r'(\d{2}/\d{2}/\d{4}).*?Allotment'
            ]
        }
    
    def extract_with_rules(self, text: str) -> Dict[str, Any]:
        """
        Extract data using rule-based patterns
        """
        extracted = {}
        
        for field, patterns in self.patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
                if matches:
                    if isinstance(matches[0], tuple):
                        extracted[field] = matches[0][0] if matches[0][0] else matches[0]
                    else:
                        extracted[field] = matches[0]
                    break
        
        return extracted
    
    def extract_with_llm(self, text: str, scheme_name: str, amc_name: str) -> Dict[str, Any]:
        """
        Extract data using LLM with focused prompt
        """
        if not self.model:
            return {}
        
        # Create focused prompt for specific fields
        prompt = f"""Extract ONLY these specific fields from the mutual fund factsheet text:

SCHEME: {scheme_name}
AMC: {amc_name}

Extract these fields and return as JSON:
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

Rules:
- Use "N/A" only if field is absolutely not found
- Extract real values from the text
- Return ONLY valid JSON

TEXT:
{text[:15000]}
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
                
                return json.loads(json_text)
        except Exception as e:
            logger.error(f"LLM extraction error: {e}")
        
        return {}
    
    def merge_extractions(self, rule_data: Dict[str, Any], llm_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge rule-based and LLM extractions, preferring non-N/A values
        """
        merged = {}
        
        # Combine all keys
        all_keys = set(rule_data.keys()) | set(llm_data.keys())
        
        for key in all_keys:
            rule_value = rule_data.get(key, "N/A")
            llm_value = llm_data.get(key, "N/A")
            
            # Prefer non-N/A values
            if rule_value != "N/A" and llm_value != "N/A":
                # Both have values, prefer LLM (more context-aware)
                merged[key] = llm_value
            elif rule_value != "N/A":
                merged[key] = rule_value
            elif llm_value != "N/A":
                merged[key] = llm_value
            else:
                merged[key] = "N/A"
        
        return merged
    
    def extract_scheme_data(self, text: str, scheme_name: str, amc_name: str) -> Dict[str, Any]:
        """
        Extract scheme data using hybrid approach
        """
        logger.info(f"🔍 Extracting data for {scheme_name}")
        
        # Step 1: Rule-based extraction
        rule_data = self.extract_with_rules(text)
        logger.info(f"📊 Rule-based found {len([v for v in rule_data.values() if v != 'N/A'])} fields")
        
        # Step 2: LLM extraction
        llm_data = self.extract_with_llm(text, scheme_name, amc_name)
        logger.info(f"🤖 LLM found {len([v for v in llm_data.values() if v != 'N/A'])} fields")
        
        # Step 3: Merge results
        merged_data = self.merge_extractions(rule_data, llm_data)
        
        # Step 4: Format according to expected schema
        formatted_data = self.format_to_schema(merged_data, scheme_name, amc_name)
        
        return formatted_data
    
    def format_to_schema(self, data: Dict[str, Any], scheme_name: str, amc_name: str) -> Dict[str, Any]:
        """
        Format extracted data to match expected schema
        """
        return {
            "Scheme_Name": scheme_name,
            "Asset_Class": self.determine_asset_class(scheme_name, data),
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
    
    def determine_asset_class(self, scheme_name: str, data: Dict[str, Any]) -> str:
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
        asset_class = self.determine_asset_class(scheme_name, {})
        if asset_class == "Equity":
            return "Open-Ended Equity Scheme"
        elif asset_class == "Debt":
            return "Open-Ended Debt Scheme"
        elif asset_class == "Hybrid":
            return "Open-Ended Hybrid Scheme"
        else:
            return "Open-Ended Scheme"

def main():
    """Test the hybrid extractor"""
    extractor = HybridDataExtractor()
    
    # Test with SBI factsheet
    pdf_path = "factsheets/AL Scheme factsheet August_SBI.pdf"
    
    # Extract text
    extraction_result = extractor.pdf_extractor.extract_text_from_pdf(pdf_path)
    full_text = extraction_result.get('full_text', '')
    
    # Test extraction for a specific scheme
    scheme_name = "SBI Large Cap Fund"
    amc_name = "SBI"
    
    # Find scheme text
    scheme_pattern = re.escape(scheme_name)
    match = re.search(scheme_pattern, full_text, re.IGNORECASE)
    
    if match:
        start_pos = max(0, match.start() - 2000)
        end_pos = min(len(full_text), match.end() + 20000)
        scheme_text = full_text[start_pos:end_pos]
        
        # Extract data
        result = extractor.extract_scheme_data(scheme_text, scheme_name, amc_name)
        
        # Save result
        output_file = extractor.output_dir / "hybrid_test_result.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ Hybrid extraction completed. Saved to {output_file}")
        
        # Count non-N/A values
        non_na_count = sum(1 for v in str(result).split('"') if v.strip() and v.strip() != 'N/A')
        logger.info(f"📊 Found {non_na_count} non-N/A values")
    else:
        logger.error(f"❌ Scheme {scheme_name} not found in text")

if __name__ == "__main__":
    main()
