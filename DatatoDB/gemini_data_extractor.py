"""
Gemini-based data extractor for mutual fund factsheets.
Uses Google's Gemini API for cost-effective and accurate data extraction.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
import google.generativeai as genai
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GeminiDataExtractor:
    def __init__(self):
        """Initialize Gemini API client"""
        load_dotenv()
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not set in environment variables or .env file")
        
        # Configure Gemini
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')  # Use available model
        
    def extract_data_with_gemini(self, scheme_text: str, scheme_name: str, amc_name: str) -> Dict[str, Any]:
        """
        Extract structured data for a single scheme using Gemini.
        """
        try:
            # Create a comprehensive prompt for data extraction
            prompt = self._create_extraction_prompt(scheme_text, scheme_name, amc_name)
            
            # Call Gemini API
            response = self.model.generate_content(prompt)
            
            # Parse the response
            extracted_data = self._parse_gemini_response(response.text)
            
            # Add metadata
            extracted_data['metadata'] = {
                'llm_model': "gemini-2.5-flash",
                'timestamp': datetime.now().isoformat()
            }
            
            return extracted_data
            
        except Exception as e:
            logger.error(f"Error extracting data with Gemini: {e}")
            return {"error": str(e)}
    
    def _create_extraction_prompt(self, scheme_text: str, scheme_name: str, amc_name: str) -> str:
        """Create a comprehensive prompt for Gemini"""
        return f"""
You are an expert financial data analyst specializing in mutual fund factsheet analysis. 
Extract accurate, structured data from the following factsheet text with 100% precision.

FACTSHEET TEXT:
{scheme_text}

SCHEME NAME: {scheme_name}
AMC NAME: {amc_name}

Please extract the following data points and return ONLY a valid JSON object in the EXACT format specified:

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
1. Extract ONLY the data that is clearly visible in the text
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
    
    def _parse_gemini_response(self, response_text: str) -> Dict[str, Any]:
        """Parse Gemini response and extract JSON"""
        try:
            # Clean the response text
            response_text = response_text.strip()
            
            # Find JSON object in response
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                logger.warning("No JSON object found in Gemini response")
                return {"error": "No JSON object found in response"}
            
            json_str = response_text[start_idx:end_idx]
            
            # Parse JSON
            extracted_data = json.loads(json_str)
            
            # Validate required fields
            if not isinstance(extracted_data, dict):
                logger.warning("Invalid JSON structure in Gemini response")
                return {"error": "Invalid JSON structure"}
            
            return extracted_data
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            logger.error(f"Response text: {response_text[:500]}...")
            return {"error": f"JSON parsing error: {str(e)}"}
        except Exception as e:
            logger.error(f"Error parsing Gemini response: {e}")
            return {"error": str(e)}
    
    def batch_extract(self, schemes_data: List[Dict[str, str]], batch_size: int = 5) -> List[Dict[str, Any]]:
        """
        Extract data for multiple schemes in batches to manage API limits
        """
        results = []
        
        for i in range(0, len(schemes_data), batch_size):
            batch = schemes_data[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}/{(len(schemes_data) + batch_size - 1)//batch_size}")
            
            for scheme_data in batch:
                try:
                    result = self.extract_data_with_gemini(
                        scheme_data['text'],
                        scheme_data['name'],
                        scheme_data['amc']
                    )
                    results.append(result)
                    
                    # Small delay to avoid rate limits
                    import time
                    time.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"Error processing scheme {scheme_data['name']}: {e}")
                    results.append({"error": str(e)})
        
        return results

def main():
    """Test the Gemini extractor"""
    try:
        extractor = GeminiDataExtractor()
        
        # Sample test data
        sample_text = """
        SBI Large Cap Fund
        An open-ended Equity Scheme predominantly investing in large cap stocks.
        Date of Allotment: 14/02/2006
        Report as on: 31/08/2025
        AUM (Crores): 52,765.64
        NAV (Growth): 90.7215
        NAV (IDCW): 51.6100
        Benchmark: BSE 100 (TRI)
        Fund Manager: Mr. Saurabh Pant (Managing since Apr-2024, Experience: 18 years)
        Exit Load: 0.50% for exit within 30 days, 0.10% for 30-90 days, Nil after 90 days
        Minimum SIP: ₹1,000
        Expense Ratio: 1.49% (Regular), 0.81% (Direct)
        Standard Deviation: 11.69%
        Beta: 0.64
        Sharpe Ratio: 1.49
        """
        
        result = extractor.extract_data_with_gemini(sample_text, "SBI Large Cap Fund", "SBI Mutual Fund")
        
        print("Gemini extraction result:")
        print(json.dumps(result, indent=2))
        
    except Exception as e:
        logger.error(f"Error in main: {e}")

if __name__ == "__main__":
    main()
