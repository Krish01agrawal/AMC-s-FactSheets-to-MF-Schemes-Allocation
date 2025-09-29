"""
Multi-Scheme Data Parser for Factsheet Information
Extracts all required data points for each scheme within a factsheet
Handles multiple schemes per PDF with high accuracy
"""
import re
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from bson import ObjectId
import config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MultiSchemeDataParser:
    """Advanced parser for extracting structured data from multi-scheme factsheets"""
    
    def __init__(self):
        self.extracted_data = {}
        self.patterns = self._initialize_advanced_patterns()
    
    def _initialize_advanced_patterns(self) -> Dict[str, List[str]]:
        """Initialize comprehensive regex patterns for data extraction"""
        return {
            # NAV patterns - more specific
            'nav_regular_growth': [
                r'Regular.*?Plan.*?Growth.*?Option[:\s]*(\d+\.?\d*)',
                r'Regular.*?Growth[:\s]*(\d+\.?\d*)',
                r'Growth.*?Option[:\s]*(\d+\.?\d*)',
                r'NAV.*?Growth[:\s]*(\d+\.?\d*)',
                r'Growth[:\s]*(\d+\.?\d*)',
            ],
            'nav_regular_idcw': [
                r'Regular.*?Plan.*?IDCW.*?Option[:\s]*(\d+\.?\d*)',
                r'Regular.*?IDCW[:\s]*(\d+\.?\d*)',
                r'IDCW.*?Option[:\s]*(\d+\.?\d*)',
                r'NAV.*?IDCW[:\s]*(\d+\.?\d*)',
                r'IDCW[:\s]*(\d+\.?\d*)',
                r'Dividend[:\s]*(\d+\.?\d*)',
            ],
            'nav_direct_growth': [
                r'Direct.*?Plan.*?Growth.*?Option[:\s]*(\d+\.?\d*)',
                r'Direct.*?Growth[:\s]*(\d+\.?\d*)',
                r'Direct.*?Growth.*?Option[:\s]*(\d+\.?\d*)',
            ],
            'nav_direct_idcw': [
                r'Direct.*?Plan.*?IDCW.*?Option[:\s]*(\d+\.?\d*)',
                r'Direct.*?IDCW[:\s]*(\d+\.?\d*)',
                r'Direct.*?IDCW.*?Option[:\s]*(\d+\.?\d*)',
            ],
            
            # AUM patterns
            'aum': [
                r'AUM.*?as on.*?(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})[:\s]*₹?(\d+\.?\d*)\s*(?:Cr|Crore|Lakh|Million|Billion)',
                r'Assets Under Management.*?₹?(\d+\.?\d*)\s*(?:Cr|Crore|Lakh|Million|Billion)',
                r'Total AUM.*?₹?(\d+\.?\d*)\s*(?:Cr|Crore|Lakh|Million|Billion)',
                r'Fund Size.*?₹?(\d+\.?\d*)\s*(?:Cr|Crore|Lakh|Million|Billion)',
                r'AUM.*?₹?(\d+\.?\d*)\s*(?:Cr|Crore|Lakh|Million|Billion)',
            ],
            
            # Fund manager patterns
            'fund_manager_name': [
                r'Fund Manager[:\s]*([^\n\r]+?)(?:\s*Since|\s*Total|\s*Experience|\n)',
                r'Manager[:\s]*([^\n\r]+?)(?:\s*Since|\s*Total|\s*Experience|\n)',
                r'Portfolio Manager[:\s]*([^\n\r]+?)(?:\s*Since|\s*Total|\s*Experience|\n)',
                r'Mr\.\s*([A-Za-z\s]+?)(?:\s*Since|\s*Total|\s*Experience|\n)',
            ],
            'fund_manager_tenure': [
                r'Since[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
                r'Managing since[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
                r'w\.e\.f\.\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
            ],
            'fund_manager_experience': [
                r'Total Experience[:\s]*([^\n\r]+)',
                r'Experience[:\s]*([^\n\r]+)',
                r'Over\s*(\d+)\s*years',
                r'(\d+)\s*years',
            ],
            
            # Exit load patterns
            'exit_load_30_days': [
                r'Exit Load.*?30.*?days?[:\s]*(\d+\.?\d*%?)',
                r'30.*?days?.*?Exit Load[:\s]*(\d+\.?\d*%?)',
                r'Within 30 days[:\s]*(\d+\.?\d*%?)',
                r'For exit.*?30 days[:\s]*(\d+\.?\d*%?)',
            ],
            'exit_load_30_90_days': [
                r'Exit Load.*?30.*?90.*?days?[:\s]*(\d+\.?\d*%?)',
                r'30.*?90.*?days?.*?Exit Load[:\s]*(\d+\.?\d*%?)',
                r'Between 30.*?90 days[:\s]*(\d+\.?\d*%?)',
                r'For exit.*?30.*?90 days[:\s]*(\d+\.?\d*%?)',
            ],
            'exit_load_after_90_days': [
                r'Exit Load.*?90.*?days?[:\s]*(\d+\.?\d*%?)',
                r'After 90 days[:\s]*(\d+\.?\d*%?)',
                r'90.*?days?.*?Exit Load[:\s]*(\d+\.?\d*%?)',
                r'For exit.*?90 days[:\s]*(\d+\.?\d*%?)',
            ],
            
            # SIP patterns
            'min_sip_monthly': [
                r'Minimum.*?SIP.*?Monthly[:\s]*₹?(\d+)',
                r'Monthly.*?SIP.*?Minimum[:\s]*₹?(\d+)',
                r'SIP.*?Monthly[:\s]*₹?(\d+)',
                r'Minimum.*?Monthly.*?SIP[:\s]*₹?(\d+)',
            ],
            
            # Performance metrics
            'cagr_1y': [
                r'1.*?Year.*?CAGR[:\s]*(\d+\.?\d*%?)',
                r'CAGR.*?1.*?Year[:\s]*(\d+\.?\d*%?)',
                r'1Y.*?CAGR[:\s]*(\d+\.?\d*%?)',
                r'Last 1 Year[:\s]*(\d+\.?\d*%?)',
            ],
            'cagr_3y': [
                r'3.*?Year.*?CAGR[:\s]*(\d+\.?\d*%?)',
                r'CAGR.*?3.*?Year[:\s]*(\d+\.?\d*%?)',
                r'3Y.*?CAGR[:\s]*(\d+\.?\d*%?)',
                r'Last 3 Years[:\s]*(\d+\.?\d*%?)',
            ],
            'cagr_5y': [
                r'5.*?Year.*?CAGR[:\s]*(\d+\.?\d*%?)',
                r'CAGR.*?5.*?Year[:\s]*(\d+\.?\d*%?)',
                r'5Y.*?CAGR[:\s]*(\d+\.?\d*%?)',
                r'Last 5 Years[:\s]*(\d+\.?\d*%?)',
            ],
            'cagr_all': [
                r'Since Inception.*?CAGR[:\s]*(\d+\.?\d*%?)',
                r'CAGR.*?Since Inception[:\s]*(\d+\.?\d*%?)',
                r'All.*?CAGR[:\s]*(\d+\.?\d*%?)',
                r'Since Inception[:\s]*(\d+\.?\d*%?)',
            ],
            
            # Risk metrics
            'standard_deviation': [
                r'Standard Deviation[:\s]*(\d+\.?\d*%?)',
                r'Std Dev[:\s]*(\d+\.?\d*%?)',
                r'Volatility[:\s]*(\d+\.?\d*%?)',
            ],
            'beta': [
                r'Beta[:\s]*(\d+\.?\d*)',
                r'β[:\s]*(\d+\.?\d*)',
            ],
            'sharpe_ratio': [
                r'Sharpe Ratio[:\s]*(\d+\.?\d*)',
                r'Sharpe[:\s]*(\d+\.?\d*)',
            ],
            
            # Turnover patterns
            'equity_turnover': [
                r'Equity.*?Turnover[:\s]*(\d+\.?\d*%?)',
                r'Portfolio.*?Turnover[:\s]*(\d+\.?\d*%?)',
                r'Equity.*?Portfolio.*?Turnover[:\s]*(\d+\.?\d*%?)',
            ],
            'total_turnover': [
                r'Total.*?Turnover[:\s]*(\d+\.?\d*%?)',
                r'Turnover[:\s]*(\d+\.?\d*%?)',
            ],
            
            # Expense ratio
            'expense_ratio': [
                r'Total Expense Ratio[:\s]*(\d+\.?\d*%?)',
                r'Expense Ratio[:\s]*(\d+\.?\d*%?)',
                r'TER[:\s]*(\d+\.?\d*%?)',
                r'Regular[:\s]*(\d+\.?\d*%?)',
            ],
            
            # Debt fund specific patterns
            'yield_to_maturity': [
                r'Yield to Maturity[:\s]*(\d+\.?\d*%?)',
                r'YTM[:\s]*(\d+\.?\d*%?)',
                r'Yield[:\s]*(\d+\.?\d*%?)',
            ],
            'modified_duration': [
                r'Modified Duration[:\s]*(\d+\.?\d*)',
                r'Mod Duration[:\s]*(\d+\.?\d*)',
            ],
            'average_maturity': [
                r'Average Maturity[:\s]*(\d+\.?\d*)',
                r'Avg Maturity[:\s]*(\d+\.?\d*)',
                r'Maturity[:\s]*(\d+\.?\d*)',
            ],
            'macaulay_duration': [
                r'Macaulay Duration[:\s]*(\d+\.?\d*)',
                r'Mac Duration[:\s]*(\d+\.?\d*)',
            ],
            
            # Riskometer patterns
            'riskometer': [
                r'Riskometer[:\s]*([^\n\r]+)',
                r'Risk Level[:\s]*([^\n\r]+)',
                r'Risk Profile[:\s]*([^\n\r]+)',
                r'Very High|High|Moderate|Low',
            ],
        }
    
    def parse_multi_scheme_factsheet(self, extracted_data: Dict) -> List[Dict[str, Any]]:
        """
        Parse factsheet data and extract all schemes with their information
        
        Args:
            extracted_data: Raw extracted data from PDF
            
        Returns:
            List of structured scheme data dictionaries
        """
        if 'schemes' not in extracted_data:
            logger.error("No schemes detected in extracted data")
            return []
        
        parsed_schemes = []
        
        for scheme in extracted_data['schemes']:
            try:
                parsed_scheme = self._parse_individual_scheme(scheme, extracted_data)
                if parsed_scheme:
                    parsed_schemes.append(parsed_scheme)
            except Exception as e:
                logger.error(f"Error parsing scheme {scheme.get('name', 'Unknown')}: {str(e)}")
                continue
        
        logger.info(f"Successfully parsed {len(parsed_schemes)} schemes")
        return parsed_schemes
    
    def _parse_individual_scheme(self, scheme: Dict, extracted_data: Dict) -> Optional[Dict[str, Any]]:
        """Parse individual scheme data"""
        try:
            scheme_text = scheme.get('extracted_data', {}).get('raw_text', '')
            if not scheme_text:
                return None
            
            # Initialize result structure
            result = {
                '_id': ObjectId(),
                'scheme_id': scheme.get('scheme_id'),
                'basic_info': {
                    'scheme_name': scheme.get('name', ''),
                    'amc_name': self._extract_amc_name(scheme_text, extracted_data),
                    'file_name': extracted_data.get('file_name', ''),
                    'extraction_date': datetime.now().isoformat(),
                    'asset_class': self._determine_asset_class(scheme_text),
                    'sub_class': self._determine_sub_class(scheme_text),
                    'scheme_type': self._determine_scheme_type(scheme_text),
                },
                'nav_data': self._extract_nav_data(scheme_text),
                'fund_details': self._extract_fund_details(scheme_text),
                'performance_metrics': self._extract_performance_metrics(scheme_text),
                'risk_metrics': self._extract_risk_metrics(scheme_text),
                'debt_metrics': self._extract_debt_metrics(scheme_text),
                'portfolio_data': self._extract_portfolio_data(scheme_text),
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error parsing individual scheme: {str(e)}")
            return None
    
    def _extract_amc_name(self, scheme_text: str, extracted_data: Dict) -> str:
        """Extract AMC name from scheme text or file name"""
        # Try to extract from scheme text first
        amc_patterns = [
            r'([A-Z][A-Z\s&\.]+(?:MUTUAL FUND|ASSET MANAGEMENT|INVESTMENT))',
            r'([A-Z][A-Z\s&\.]+(?:FUND|SCHEME|PLAN))\s*[-–]\s*([A-Z][A-Z\s&\.]+)',
        ]
        
        for pattern in amc_patterns:
            match = re.search(pattern, scheme_text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        # Fallback to file name
        file_name = extracted_data.get('file_name', '')
        if 'HDFC' in file_name:
            return 'HDFC Mutual Fund'
        elif 'SBI' in file_name:
            return 'SBI Mutual Fund'
        elif 'ICICI' in file_name:
            return 'ICICI Prudential Mutual Fund'
        elif 'Axis' in file_name:
            return 'Axis Mutual Fund'
        elif 'Nippon' in file_name:
            return 'Nippon India Mutual Fund'
        
        return 'Unknown AMC'
    
    def _determine_asset_class(self, text: str) -> str:
        """Determine asset class based on scheme text"""
        text_lower = text.lower()
        
        if any(keyword in text_lower for keyword in ['equity', 'growth', 'value', 'large cap', 'mid cap', 'small cap']):
            return 'equity'
        elif any(keyword in text_lower for keyword in ['debt', 'bond', 'gilt', 'liquid', 'money market']):
            return 'debt'
        elif any(keyword in text_lower for keyword in ['hybrid', 'balanced', 'arbitrage']):
            return 'hybrid'
        elif any(keyword in text_lower for keyword in ['solution', 'retirement', 'children', 'tax saving']):
            return 'solution'
        else:
            return 'other'
    
    def _determine_sub_class(self, text: str) -> str:
        """Determine sub-class based on scheme text"""
        text_lower = text.lower()
        
        if 'large cap' in text_lower:
            return 'large cap'
        elif 'mid cap' in text_lower:
            return 'mid cap'
        elif 'small cap' in text_lower:
            return 'small cap'
        elif 'flexi cap' in text_lower:
            return 'flexi cap'
        elif 'multi cap' in text_lower:
            return 'multi cap'
        elif 'sectoral' in text_lower or 'sector' in text_lower:
            return 'sectoral'
        elif 'thematic' in text_lower:
            return 'thematic'
        elif 'value' in text_lower:
            return 'value'
        elif 'growth' in text_lower:
            return 'growth'
        elif 'dividend yield' in text_lower:
            return 'dividend yield'
        elif 'liquid' in text_lower:
            return 'liquid'
        elif 'money market' in text_lower:
            return 'money market'
        elif 'corporate bond' in text_lower:
            return 'corporate bond'
        elif 'government' in text_lower or 'gilt' in text_lower:
            return 'government securities'
        else:
            return 'other'
    
    def _determine_scheme_type(self, text: str) -> str:
        """Determine scheme type"""
        text_lower = text.lower()
        
        if 'growth' in text_lower:
            return 'Growth'
        elif 'dividend' in text_lower or 'idcw' in text_lower:
            return 'IDCW'
        elif 'regular' in text_lower:
            return 'Regular'
        else:
            return 'Growth'  # Default
    
    def _extract_nav_data(self, text: str) -> Dict:
        """Extract NAV data with high accuracy"""
        nav_data = {}
        
        # Extract Regular Growth NAV
        nav_data['regular_growth'] = self._extract_value(text, self.patterns['nav_regular_growth'])
        
        # Extract Regular IDCW NAV
        nav_data['regular_idcw'] = self._extract_value(text, self.patterns['nav_regular_idcw'])
        
        # Extract Direct Growth NAV
        nav_data['direct_growth'] = self._extract_value(text, self.patterns['nav_direct_growth'])
        
        # Extract Direct IDCW NAV
        nav_data['direct_idcw'] = self._extract_value(text, self.patterns['nav_direct_idcw'])
        
        return nav_data
    
    def _extract_fund_details(self, text: str) -> Dict:
        """Extract fund details with high accuracy"""
        fund_details = {}
        
        # Extract AUM
        fund_details['aum'] = self._extract_value(text, self.patterns['aum'])
        
        # Extract inception date
        fund_details['inception_date'] = self._extract_date(text, [
            r'Date of Allotment[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
            r'Inception Date[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
            r'Launch Date[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
        ])
        
        # Extract fund manager information
        fund_details['fund_manager_name'] = self._extract_text(text, self.patterns['fund_manager_name'])
        fund_details['fund_manager_tenure'] = self._extract_date(text, self.patterns['fund_manager_tenure'])
        fund_details['fund_manager_experience'] = self._extract_text(text, self.patterns['fund_manager_experience'])
        
        # Extract benchmark
        fund_details['benchmark'] = self._extract_text(text, [
            r'Benchmark[:\s]*([^\n\r]+)',
            r'Index[:\s]*([^\n\r]+)',
            r'Reference Index[:\s]*([^\n\r]+)',
        ])
        
        # Extract exit loads
        fund_details['exit_load_30_days'] = self._extract_value(text, self.patterns['exit_load_30_days'])
        fund_details['exit_load_30_90_days'] = self._extract_value(text, self.patterns['exit_load_30_90_days'])
        fund_details['exit_load_after_90_days'] = self._extract_value(text, self.patterns['exit_load_after_90_days'])
        
        # Extract minimum SIP
        fund_details['min_sip_monthly'] = self._extract_value(text, self.patterns['min_sip_monthly'])
        
        # Extract expense ratio
        fund_details['expense_ratio'] = self._extract_value(text, self.patterns['expense_ratio'])
        
        return fund_details
    
    def _extract_performance_metrics(self, text: str) -> Dict:
        """Extract performance metrics"""
        performance = {}
        
        # Extract CAGR values
        performance['cagr_1y'] = self._extract_value(text, self.patterns['cagr_1y'])
        performance['cagr_3y'] = self._extract_value(text, self.patterns['cagr_3y'])
        performance['cagr_5y'] = self._extract_value(text, self.patterns['cagr_5y'])
        performance['cagr_all'] = self._extract_value(text, self.patterns['cagr_all'])
        
        # Extract turnover
        performance['equity_turnover'] = self._extract_value(text, self.patterns['equity_turnover'])
        performance['total_turnover'] = self._extract_value(text, self.patterns['total_turnover'])
        
        return performance
    
    def _extract_risk_metrics(self, text: str) -> Dict:
        """Extract risk metrics"""
        risk_metrics = {}
        
        risk_metrics['standard_deviation'] = self._extract_value(text, self.patterns['standard_deviation'])
        risk_metrics['beta'] = self._extract_value(text, self.patterns['beta'])
        risk_metrics['sharpe_ratio'] = self._extract_value(text, self.patterns['sharpe_ratio'])
        
        # Extract riskometer
        risk_metrics['riskometer'] = self._extract_text(text, self.patterns['riskometer'])
        
        return risk_metrics
    
    def _extract_debt_metrics(self, text: str) -> Dict:
        """Extract debt-specific metrics"""
        debt_metrics = {}
        
        debt_metrics['yield_to_maturity'] = self._extract_value(text, self.patterns['yield_to_maturity'])
        debt_metrics['modified_duration'] = self._extract_value(text, self.patterns['modified_duration'])
        debt_metrics['average_maturity_years'] = self._extract_value(text, self.patterns['average_maturity'])
        debt_metrics['macaulay_duration'] = self._extract_value(text, self.patterns['macaulay_duration'])
        
        return debt_metrics
    
    def _extract_portfolio_data(self, text: str) -> Dict:
        """Extract portfolio-related data"""
        portfolio_data = {}
        
        # Extract industry allocation
        industry_allocation = self._extract_industry_allocation(text)
        portfolio_data['industry_allocation'] = industry_allocation
        
        # Extract portfolio composition
        portfolio_composition = self._extract_portfolio_composition(text)
        portfolio_data['portfolio_composition'] = portfolio_composition
        
        return portfolio_data
    
    def _extract_industry_allocation(self, text: str) -> Dict[str, float]:
        """Extract industry allocation percentages"""
        industry_allocation = {}
        
        # Look for industry allocation sections
        allocation_section = self._find_section(text, ['industry', 'sector', 'allocation'])
        
        if allocation_section:
            # Common industry patterns
            industry_patterns = [
                r'([A-Za-z\s&\.]+)[:\s]*(\d+\.?\d*%?)',
                r'([A-Za-z\s&\.]+)\s+(\d+\.?\d*%?)',
            ]
            
            for pattern in industry_patterns:
                matches = re.findall(pattern, allocation_section)
                for match in matches:
                    industry = match[0].strip()
                    percentage = match[1].strip()
                    if industry and percentage and len(industry) > 2:
                        try:
                            percentage_value = float(re.sub(r'[^\d.]', '', percentage))
                            if 0 <= percentage_value <= 100:
                                industry_allocation[industry] = percentage_value
                        except ValueError:
                            continue
        
        return industry_allocation
    
    def _extract_portfolio_composition(self, text: str) -> Dict[str, Any]:
        """Extract portfolio composition details"""
        composition = {}
        
        # Extract top holdings
        top_holdings = self._extract_top_holdings(text)
        composition['top_holdings'] = top_holdings
        
        # Extract asset allocation
        asset_allocation = self._extract_asset_allocation(text)
        composition['asset_allocation'] = asset_allocation
        
        return composition
    
    def _extract_top_holdings(self, text: str) -> List[Dict[str, str]]:
        """Extract top holdings information"""
        holdings = []
        
        # Look for holdings section
        holdings_section = self._find_section(text, ['holdings', 'portfolio', 'investments'])
        
        if holdings_section:
            # Pattern for company name and percentage
            holding_pattern = r'([A-Za-z\s&\.]+)\s+(\d+\.?\d*%?)'
            matches = re.findall(holding_pattern, holdings_section)
            
            for match in matches:
                company = match[0].strip()
                percentage = match[1].strip()
                if company and percentage and len(company) > 2:
                    holdings.append({
                        'company': company,
                        'percentage': percentage
                    })
        
        return holdings[:10]  # Return top 10 holdings
    
    def _extract_asset_allocation(self, text: str) -> Dict[str, float]:
        """Extract asset allocation percentages"""
        allocation = {}
        
        # Common asset types
        asset_types = ['equity', 'debt', 'cash', 'others', 'derivatives']
        
        for asset_type in asset_types:
            pattern = rf'{asset_type}[:\s]*(\d+\.?\d*%?)'
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    percentage = float(re.sub(r'[^\d.]', '', match.group(1)))
                    if 0 <= percentage <= 100:
                        allocation[asset_type] = percentage
                except ValueError:
                    continue
        
        return allocation
    
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
    
    def _extract_value(self, text: str, patterns: List[str]) -> Optional[float]:
        """Extract numeric value using patterns"""
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                try:
                    value_str = match.group(1)
                    # Clean the value string
                    value_str = re.sub(r'[^\d.]', '', value_str)
                    if value_str:
                        return float(value_str)
                except ValueError:
                    continue
        return None
    
    def _extract_text(self, text: str, patterns: List[str]) -> Optional[str]:
        """Extract text using patterns"""
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                return match.group(1).strip()
        return None
    
    def _extract_date(self, text: str, patterns: List[str]) -> Optional[str]:
        """Extract date using patterns"""
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                return match.group(1).strip()
        return None
