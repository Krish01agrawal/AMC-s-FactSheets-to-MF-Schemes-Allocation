#!/usr/bin/env python3
"""
Optimized Gemini-based Data Extractor with Smart Rate Limiting
Uses Gemini 2.5 Flash for cost-effective extraction with proper rate limiting
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import re
import time

# Gemini imports
import google.generativeai as genai
from dotenv import load_dotenv

# PDF processing
from advanced_pdf_extractor import AdvancedPDFExtractor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OptimizedGeminiExtractor:
    """Optimized Gemini-based extractor with smart rate limiting"""
    
    def __init__(self):
        load_dotenv()
        
        # Initialize Gemini
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not set in environment variables")
        
        genai.configure(api_key=api_key)
        
        # Use Gemini 2.5 Flash for better rate limits (15 requests/min vs 2 for Pro)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        self.pdf_extractor = AdvancedPDFExtractor()
        
        # Smart rate limiting for Gemini 2.5 Flash (15 requests/min)
        self.request_delay = 4.0  # 4 seconds between requests = 15 requests/min
        self.last_request_time = 0
        
        # Progress tracking
        self.progress_file = None
        self.current_amc = None
        self.total_schemes = 0
        self.processed_schemes = 0
        
    def _smart_rate_limit(self):
        """Smart rate limiting to stay within Gemini 2.5 Flash limits"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.request_delay:
            sleep_time = self.request_delay - time_since_last
            logger.info(f"⏳ Rate limiting: waiting {sleep_time:.1f}s (15 requests/min limit)")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _initialize_progress_tracking(self, amc_name: str, total_schemes: int):
        """Initialize real-time progress tracking"""
        self.current_amc = amc_name
        self.total_schemes = total_schemes
        self.processed_schemes = 0
        
        # Create progress file
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.progress_file = output_dir / f"{amc_name}_optimized_progress_{timestamp}.json"
        
        # Initialize progress data
        progress_data = {
            "amc_name": amc_name,
            "status": "processing",
            "model": "gemini-2.5-flash",
            "rate_limit": "15 requests/min",
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
        
        with open(self.progress_file, 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"📊 Progress tracking initialized: {self.progress_file}")
        logger.info(f"🔄 Processing {amc_name}: 0/{total_schemes} schemes (using Gemini 2.5 Flash)")
    
    def _update_progress(self, scheme_data: Dict[str, Any], error: str = None):
        """Update real-time progress"""
        self.processed_schemes += 1
        
        try:
            # Read current progress
            with open(self.progress_file, 'r', encoding='utf-8') as f:
                progress_data = json.load(f)
            
            # Update progress
            progress_data["progress"]["current"] = self.processed_schemes
            progress_data["progress"]["percentage"] = round((self.processed_schemes / self.total_schemes) * 100, 2)
            progress_data["last_updated"] = datetime.now().isoformat()
            
            if error:
                progress_data["errors"].append({
                    "scheme": scheme_data.get("Scheme_Name", "Unknown"),
                    "error": error,
                    "timestamp": datetime.now().isoformat()
                })
            else:
                progress_data["schemes"].append(scheme_data)
            
            # Write updated progress
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress_data, f, indent=2, ensure_ascii=False)
            
            # Log progress
            percentage = progress_data["progress"]["percentage"]
            logger.info(f"📊 Progress: {self.processed_schemes}/{self.total_schemes} ({percentage}%) - {scheme_data.get('Scheme_Name', 'Unknown')}")
            
        except Exception as e:
            logger.error(f"Error updating progress: {e}")
    
    def _complete_progress(self, all_results: List[Dict[str, Any]]):
        """Mark progress as completed"""
        try:
            # Read current progress
            with open(self.progress_file, 'r', encoding='utf-8') as f:
                progress_data = json.load(f)
            
            # Mark as completed
            progress_data["status"] = "completed"
            progress_data["progress"]["percentage"] = 100.0
            progress_data["end_time"] = datetime.now().isoformat()
            progress_data["total_schemes_extracted"] = len(all_results)
            progress_data["schemes"] = all_results
            
            # Write final progress
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ Progress completed: {self.progress_file}")
            
        except Exception as e:
            logger.error(f"Error completing progress: {e}")
    
    def extract_from_factsheet(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Extract all schemes from a factsheet with optimized Gemini extraction"""
        logger.info(f"🚀 Starting optimized extraction from {pdf_path}")
        
        # Extract text from PDF
        extracted_data = self.pdf_extractor.extract_text_from_pdf(pdf_path)
        full_text = extracted_data.get('full_text', '')
        
        if not full_text:
            logger.error(f"No text extracted from {pdf_path}")
            return []
        
        # Determine AMC name from file path
        amc_name = self._extract_amc_name(pdf_path)
        
        # Split into schemes using intelligent detection
        schemes = self._intelligent_scheme_splitter(full_text, amc_name)
        logger.info(f"📊 Found {len(schemes)} schemes in {amc_name}")
        
        # Initialize progress tracking
        self._initialize_progress_tracking(amc_name, len(schemes))
        
        # Extract data for each scheme using Gemini
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
                
                # Update progress
                self._update_progress(scheme_data)
                
                # Smart rate limiting
                self._smart_rate_limit()
                
            except Exception as e:
                logger.error(f"Error processing scheme {scheme['name']}: {e}")
                # Add fallback data
                fallback_data = self._create_fallback_scheme_data(scheme['name'], amc_name)
                results.append(fallback_data)
                
                # Update progress with error
                self._update_progress(fallback_data, str(e))
        
        # Complete progress tracking
        self._complete_progress(results)
        
        logger.info(f"✅ Successfully extracted {len(results)} schemes")
        return results
    
    def _extract_amc_name(self, pdf_path: str) -> str:
        """Extract AMC name from file path"""
        filename = Path(pdf_path).name.lower()
        if 'hdfc' in filename:
            return 'HDFC'
        elif 'sbi' in filename:
            return 'SBI'
        else:
            return 'Unknown'
    
    def _intelligent_scheme_splitter(self, text: str, amc_name: str) -> List[Dict[str, str]]:
        """Intelligently split text into individual scheme blocks using regex (no LLM for splitting)"""
        schemes = []
        
        # Enhanced regex patterns for scheme detection
        if amc_name == 'HDFC':
            patterns = [
                r'(HDFC\s+[A-Za-z\s&]+(?:Fund|Scheme))\s*\n',
                r'(HDFC\s+[A-Za-z\s&]+(?:Equity|Debt|Hybrid|Balanced|Liquid|Money Market|Gilt|Corporate Bond|Credit Risk|Banking|Technology|Healthcare|FMCG|Infrastructure|Thematic|Value|Growth|Dividend|IDCW|ITC))\s*\n',
            ]
        elif amc_name == 'SBI':
            patterns = [
                r'(SBI\s+[A-Za-z\s&]+(?:Fund|Scheme))\s*\n',
                r'(SBI\s+[A-Za-z\s&]+(?:Equity|Debt|Hybrid|Balanced|Liquid|Money Market|Gilt|Corporate Bond|Credit Risk|Banking|Technology|Healthcare|FMCG|Infrastructure|Thematic|Value|Growth|Dividend|IDCW|ITC))\s*\n',
            ]
        else:
            patterns = [
                r'([A-Z][A-Za-z\s&]+(?:Fund|Scheme))\s*\n',
            ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                scheme_name = match.group(1).strip()
                
                # Find the text block for this scheme
                start_pos = match.end()
                next_match = None
                
                # Look for the next scheme
                for next_pattern in patterns:
                    next_matches = list(re.finditer(next_pattern, text[start_pos:], re.IGNORECASE | re.MULTILINE))
                    if next_matches:
                        if next_match is None or next_matches[0].start() < next_match.start():
                            next_match = next_matches[0]
                
                if next_match:
                    end_pos = start_pos + next_match.start()
                else:
                    end_pos = min(start_pos + 8000, len(text))  # Limit to 8000 chars
                
                scheme_text = text[start_pos:end_pos].strip()
                
                if len(scheme_text) > 500:  # Minimum length for meaningful data
                    schemes.append({
                        'name': scheme_name,
                        'text': scheme_text,
                        'amc': amc_name
                    })
        
        # Remove duplicates
        unique_schemes = []
        seen_names = set()
        for scheme in schemes:
            if scheme['name'] not in seen_names:
                unique_schemes.append(scheme)
                seen_names.add(scheme['name'])
        
        return unique_schemes
    
    def _extract_scheme_data_with_gemini(self, scheme_text: str, scheme_name: str, amc_name: str) -> Dict[str, Any]:
        """Extract all data points for a scheme using Gemini 2.5 Flash"""
        
        prompt = f"""
        You are an expert financial data analyst specializing in mutual fund factsheet analysis.
        Extract ALL data points from the following scheme information with 100% accuracy.
        
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
            return scheme_data
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error for scheme {scheme_name}: {e}")
            return self._create_fallback_scheme_data(scheme_name, amc_name)
        except Exception as e:
            logger.error(f"Gemini extraction error for scheme {scheme_name}: {e}")
            return self._create_fallback_scheme_data(scheme_name, amc_name)
    
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
    
    def process_all_factsheets(self, factsheet_dir: str = "factsheets") -> Dict[str, List[Dict[str, Any]]]:
        """Process all factsheets in the directory with optimized extraction"""
        results = {}
        factsheet_path = Path(factsheet_dir)
        
        if not factsheet_path.exists():
            logger.error(f"Factsheet directory {factsheet_dir} does not exist")
            return results
        
        # Find all PDF files
        pdf_files = list(factsheet_path.glob("*.pdf"))
        logger.info(f"📁 Found {len(pdf_files)} PDF files to process")
        
        for pdf_file in pdf_files:
            logger.info(f"🔄 Processing {pdf_file.name}")
            try:
                scheme_data = self.extract_from_factsheet(str(pdf_file))
                amc_name = self._extract_amc_name(str(pdf_file))
                results[amc_name] = scheme_data
                
                # Save individual results
                self._save_results(scheme_data, amc_name)
                
            except Exception as e:
                logger.error(f"Error processing {pdf_file.name}: {e}")
        
        # Save combined results
        self._save_combined_results(results)
        
        return results
    
    def _save_results(self, data: List[Dict[str, Any]], amc_name: str):
        """Save results to JSON file"""
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{amc_name}_optimized_gemini_{timestamp}.json"
        filepath = output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"💾 Results saved to: {filepath}")
    
    def _save_combined_results(self, results: Dict[str, List[Dict[str, Any]]]):
        """Save combined results from all AMCs"""
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"optimized_gemini_all_amcs_{timestamp}.json"
        filepath = output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"💾 Combined results saved to: {filepath}")

def main():
    """Main function to run optimized extraction"""
    try:
        extractor = OptimizedGeminiExtractor()
        results = extractor.process_all_factsheets()
        
        total_schemes = sum(len(schemes) for schemes in results.values())
        logger.info(f"🎉 Optimized extraction completed!")
        logger.info(f"📊 Total schemes extracted: {total_schemes}")
        
        for amc, schemes in results.items():
            logger.info(f"   {amc}: {len(schemes)} schemes")
        
    except Exception as e:
        logger.error(f"Error in main: {e}")

if __name__ == "__main__":
    main()
