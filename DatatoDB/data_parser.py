"""
Intelligent Data Parser for Factsheet Information
Extracts all required data points from factsheet text with advanced pattern matching
"""
import re
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FactsheetDataParser:
    """Advanced parser for extracting structured data from factsheet text"""
    
    def __init__(self):
        self.extracted_data = {}
        self.patterns = self._initialize_patterns()
    
    def _initialize_patterns(self) -> Dict[str, List[str]]:
        """Initialize regex patterns for data extraction"""
        return {
            'nav_regular': [
                r'NAV.*?Regular.*?(\d+\.?\d*)',
                r'Regular.*?NAV.*?(\d+\.?\d*)',
                r'Regular.*?(\d+\.?\d*)',
                r'NAV.*?(\d+\.?\d*).*?Regular'
            ],
            'nav_growth': [
                r'NAV.*?Growth.*?(\d+\.?\d*)',
                r'Growth.*?NAV.*?(\d+\.?\d*)',
                r'Growth.*?(\d+\.?\d*)',
                r'NAV.*?(\d+\.?\d*).*?Growth'
            ],
            'nav_idcw': [
                r'NAV.*?IDCW.*?(\d+\.?\d*)',
                r'IDCW.*?NAV.*?(\d+\.?\d*)',
                r'IDCW.*?(\d+\.?\d*)',
                r'Dividend.*?(\d+\.?\d*)'
            ],
            'aum': [
                r'AUM.*?(\d+\.?\d*)\s*(?:Cr|Crore|Lakh|Million|Billion)',
                r'Assets Under Management.*?(\d+\.?\d*)\s*(?:Cr|Crore|Lakh|Million|Billion)',
                r'Total AUM.*?(\d+\.?\d*)\s*(?:Cr|Crore|Lakh|Million|Billion)',
                r'Fund Size.*?(\d+\.?\d*)\s*(?:Cr|Crore|Lakh|Million|Billion)'
            ],
            'inception_date': [
                r'Date of Allotment[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
                r'Inception Date[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
                r'Launch Date[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
                r'Started[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})'
            ],
            'fund_manager': [
                r'Fund Manager[:\s]*([^\n\r]+)',
                r'Manager[:\s]*([^\n\r]+)',
                r'Portfolio Manager[:\s]*([^\n\r]+)'
            ],
            'benchmark': [
                r'Benchmark[:\s]*([^\n\r]+)',
                r'Index[:\s]*([^\n\r]+)',
                r'Reference Index[:\s]*([^\n\r]+)'
            ],
            'exit_load_30': [
                r'Exit Load.*?30.*?days?[:\s]*(\d+\.?\d*%?)',
                r'30.*?days?.*?Exit Load[:\s]*(\d+\.?\d*%?)',
                r'Within 30 days[:\s]*(\d+\.?\d*%?)'
            ],
            'exit_load_30_90': [
                r'Exit Load.*?30.*?90.*?days?[:\s]*(\d+\.?\d*%?)',
                r'30.*?90.*?days?.*?Exit Load[:\s]*(\d+\.?\d*%?)',
                r'Between 30.*?90 days[:\s]*(\d+\.?\d*%?)'
            ],
            'exit_load_90': [
                r'Exit Load.*?90.*?days?[:\s]*(\d+\.?\d*%?)',
                r'After 90 days[:\s]*(\d+\.?\d*%?)',
                r'90.*?days?.*?Exit Load[:\s]*(\d+\.?\d*%?)'
            ],
            'min_sip': [
                r'Minimum SIP[:\s]*(\d+)',
                r'Min SIP[:\s]*(\d+)',
                r'SIP Minimum[:\s]*(\d+)',
                r'Minimum Investment[:\s]*(\d+)'
            ],
            'standard_deviation': [
                r'Standard Deviation[:\s]*(\d+\.?\d*)',
                r'Std Dev[:\s]*(\d+\.?\d*)',
                r'Volatility[:\s]*(\d+\.?\d*)'
            ],
            'beta': [
                r'Beta[:\s]*(\d+\.?\d*)',
                r'β[:\s]*(\d+\.?\d*)'
            ],
            'sharpe_ratio': [
                r'Sharpe Ratio[:\s]*(\d+\.?\d*)',
                r'Sharpe[:\s]*(\d+\.?\d*)'
            ],
            'expense_ratio': [
                r'Expense Ratio[:\s]*(\d+\.?\d*%?)',
                r'Total Expense Ratio[:\s]*(\d+\.?\d*%?)',
                r'TER[:\s]*(\d+\.?\d*%?)'
            ],
            'cagr_1y': [
                r'1.*?Year.*?CAGR[:\s]*(\d+\.?\d*%?)',
                r'CAGR.*?1.*?Year[:\s]*(\d+\.?\d*%?)',
                r'1Y.*?CAGR[:\s]*(\d+\.?\d*%?)'
            ],
            'cagr_3y': [
                r'3.*?Year.*?CAGR[:\s]*(\d+\.?\d*%?)',
                r'CAGR.*?3.*?Year[:\s]*(\d+\.?\d*%?)',
                r'3Y.*?CAGR[:\s]*(\d+\.?\d*%?)'
            ],
            'cagr_5y': [
                r'5.*?Year.*?CAGR[:\s]*(\d+\.?\d*%?)',
                r'CAGR.*?5.*?Year[:\s]*(\d+\.?\d*%?)',
                r'5Y.*?CAGR[:\s]*(\d+\.?\d*%?)'
            ],
            'cagr_all': [
                r'Since Inception.*?CAGR[:\s]*(\d+\.?\d*%?)',
                r'CAGR.*?Since Inception[:\s]*(\d+\.?\d*%?)',
                r'All.*?CAGR[:\s]*(\d+\.?\d*%?)'
            ],
            'modified_duration': [
                r'Modified Duration[:\s]*(\d+\.?\d*)',
                r'Mod Duration[:\s]*(\d+\.?\d*)'
            ],
            'average_maturity': [
                r'Average Maturity[:\s]*(\d+\.?\d*)',
                r'Avg Maturity[:\s]*(\d+\.?\d*)',
                r'Maturity[:\s]*(\d+\.?\d*)'
            ],
            'macaulay_duration': [
                r'Macaulay Duration[:\s]*(\d+\.?\d*)',
                r'Mac Duration[:\s]*(\d+\.?\d*)'
            ],
            'yield_to_maturity': [
                r'Yield to Maturity[:\s]*(\d+\.?\d*%?)',
                r'YTM[:\s]*(\d+\.?\d*%?)',
                r'Yield[:\s]*(\d+\.?\d*%?)'
            ],
            'turnover': [
                r'Portfolio Turnover[:\s]*(\d+\.?\d*%?)',
                r'Turnover[:\s]*(\d+\.?\d*%?)',
                r'Equity Turnover[:\s]*(\d+\.?\d*%?)'
            ]
        }
    
    def parse_factsheet(self, extracted_data: Dict) -> Dict[str, Any]:
        """
        Parse factsheet data and extract all required information
        
        Args:
            extracted_data: Raw extracted data from PDF
            
        Returns:
            Structured data dictionary
        """
        if 'full_text' not in extracted_data:
            logger.error("No text data available for parsing")
            return {}
        
        full_text = extracted_data['full_text']
        scheme_info = extracted_data.get('scheme_info', {})
        
        # Initialize result structure
        result = {
            'basic_info': {
                'scheme_name': scheme_info.get('scheme_name', ''),
                'amc_name': scheme_info.get('amc_name', ''),
                'file_name': extracted_data.get('file_name', ''),
                'extraction_date': datetime.now().isoformat()
            },
            'nav_data': {},
            'fund_details': {},
            'performance_metrics': {},
            'risk_metrics': {},
            'debt_metrics': {},
            'portfolio_data': {},
            'raw_text_snippets': {}
        }
        
        # Extract all data points
        self._extract_nav_data(full_text, result)
        self._extract_fund_details(full_text, result)
        self._extract_performance_metrics(full_text, result)
        self._extract_risk_metrics(full_text, result)
        self._extract_debt_metrics(full_text, result)
        self._extract_portfolio_data(full_text, result)
        self._extract_asset_classification(full_text, result)
        self._extract_riskometer(full_text, result)
        
        return result
    
    def _extract_nav_data(self, text: str, result: Dict) -> None:
        """Extract NAV related data"""
        nav_data = {}
        
        # Extract NAV values
        nav_data['regular_itc'] = self._extract_value(text, self.patterns['nav_regular'])
        nav_data['regular_growth'] = self._extract_value(text, self.patterns['nav_growth'])
        nav_data['idcw'] = self._extract_value(text, self.patterns['nav_idcw'])
        
        result['nav_data'] = nav_data
    
    def _extract_fund_details(self, text: str, result: Dict) -> None:
        """Extract fund details"""
        fund_details = {}
        
        # Extract basic fund information
        fund_details['aum'] = self._extract_value(text, self.patterns['aum'])
        fund_details['inception_date'] = self._extract_date(text, self.patterns['inception_date'])
        fund_details['fund_manager'] = self._extract_text(text, self.patterns['fund_manager'])
        fund_details['benchmark'] = self._extract_text(text, self.patterns['benchmark'])
        fund_details['min_sip'] = self._extract_value(text, self.patterns['min_sip'])
        fund_details['expense_ratio'] = self._extract_value(text, self.patterns['expense_ratio'])
        
        # Extract exit loads
        fund_details['exit_load_30_days'] = self._extract_value(text, self.patterns['exit_load_30'])
        fund_details['exit_load_30_90_days'] = self._extract_value(text, self.patterns['exit_load_30_90'])
        fund_details['exit_load_after_90_days'] = self._extract_value(text, self.patterns['exit_load_90'])
        
        result['fund_details'] = fund_details
    
    def _extract_performance_metrics(self, text: str, result: Dict) -> None:
        """Extract performance metrics"""
        performance = {}
        
        # Extract CAGR values
        performance['cagr_1y'] = self._extract_value(text, self.patterns['cagr_1y'])
        performance['cagr_3y'] = self._extract_value(text, self.patterns['cagr_3y'])
        performance['cagr_5y'] = self._extract_value(text, self.patterns['cagr_5y'])
        performance['cagr_all'] = self._extract_value(text, self.patterns['cagr_all'])
        
        # Extract turnover
        performance['equity_turnover'] = self._extract_value(text, self.patterns['turnover'])
        performance['total_turnover'] = self._extract_value(text, self.patterns['turnover'])
        
        result['performance_metrics'] = performance
    
    def _extract_risk_metrics(self, text: str, result: Dict) -> None:
        """Extract risk metrics"""
        risk_metrics = {}
        
        risk_metrics['standard_deviation'] = self._extract_value(text, self.patterns['standard_deviation'])
        risk_metrics['beta'] = self._extract_value(text, self.patterns['beta'])
        risk_metrics['sharpe_ratio'] = self._extract_value(text, self.patterns['sharpe_ratio'])
        
        result['risk_metrics'] = risk_metrics
    
    def _extract_debt_metrics(self, text: str, result: Dict) -> None:
        """Extract debt-specific metrics"""
        debt_metrics = {}
        
        debt_metrics['yield_to_maturity'] = self._extract_value(text, self.patterns['yield_to_maturity'])
        debt_metrics['modified_duration'] = self._extract_value(text, self.patterns['modified_duration'])
        debt_metrics['average_maturity_years'] = self._extract_value(text, self.patterns['average_maturity'])
        debt_metrics['macaulay_duration'] = self._extract_value(text, self.patterns['macaulay_duration'])
        
        result['debt_metrics'] = debt_metrics
    
    def _extract_portfolio_data(self, text: str, result: Dict) -> None:
        """Extract portfolio-related data"""
        portfolio_data = {}
        
        # Extract industry allocation (simplified approach)
        industry_allocation = self._extract_industry_allocation(text)
        portfolio_data['industry_allocation'] = industry_allocation
        
        # Extract portfolio composition
        portfolio_composition = self._extract_portfolio_composition(text)
        portfolio_data['portfolio_composition'] = portfolio_composition
        
        result['portfolio_data'] = portfolio_data
    
    def _extract_asset_classification(self, text: str, result: Dict) -> None:
        """Extract asset class and sub-class information"""
        asset_info = {}
        
        # Determine asset class based on scheme name and content
        scheme_name = result['basic_info'].get('scheme_name', '').lower()
        text_lower = text.lower()
        
        # Classify asset class
        if any(keyword in scheme_name or keyword in text_lower for keyword in ['equity', 'growth', 'value']):
            asset_info['asset_class'] = 'equity'
        elif any(keyword in scheme_name or keyword in text_lower for keyword in ['debt', 'bond', 'gilt']):
            asset_info['asset_class'] = 'debt'
        elif any(keyword in scheme_name or keyword in text_lower for keyword in ['hybrid', 'balanced']):
            asset_info['asset_class'] = 'hybrid'
        else:
            asset_info['asset_class'] = 'other'
        
        # Determine sub-class
        asset_info['sub_class'] = self._determine_sub_class(scheme_name, text_lower, asset_info['asset_class'])
        
        # Determine scheme type
        asset_info['scheme_type'] = self._determine_scheme_type(scheme_name, text_lower)
        
        result['asset_classification'] = asset_info
    
    def _extract_riskometer(self, text: str, result: Dict) -> None:
        """Extract riskometer information"""
        riskometer_patterns = [
            r'Riskometer[:\s]*([^\n\r]+)',
            r'Risk Level[:\s]*([^\n\r]+)',
            r'Risk Profile[:\s]*([^\n\r]+)',
            r'Risk[:\s]*(?:Low|Moderate|High)'
        ]
        
        riskometer = self._extract_text(text, riskometer_patterns)
        result['riskometer'] = riskometer
    
    def _extract_industry_allocation(self, text: str) -> Dict[str, float]:
        """Extract industry allocation percentages"""
        industry_allocation = {}
        
        # Common industry patterns
        industry_patterns = [
            r'([A-Za-z\s]+)[:\s]*(\d+\.?\d*%?)',
            r'([A-Za-z\s]+)\s+(\d+\.?\d*%?)'
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
                            # Clean percentage value
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
    
    def _determine_sub_class(self, scheme_name: str, text: str, asset_class: str) -> str:
        """Determine sub-class based on scheme name and content"""
        if asset_class == 'equity':
            if any(keyword in scheme_name for keyword in ['large cap', 'largecap']):
                return 'large cap'
            elif any(keyword in scheme_name for keyword in ['mid cap', 'midcap']):
                return 'mid cap'
            elif any(keyword in scheme_name for keyword in ['small cap', 'smallcap']):
                return 'small cap'
            elif any(keyword in scheme_name for keyword in ['flexi cap', 'flexicap']):
                return 'flexi cap'
            elif any(keyword in scheme_name for keyword in ['multi cap', 'multicap']):
                return 'multi cap'
            else:
                return 'equity'
        
        elif asset_class == 'debt':
            if any(keyword in scheme_name for keyword in ['corporate bond', 'corporate']):
                return 'corporate bond'
            elif any(keyword in scheme_name for keyword in ['government', 'gilt']):
                return 'government securities'
            elif any(keyword in scheme_name for keyword in ['money market']):
                return 'money market'
            elif any(keyword in scheme_name for keyword in ['short duration']):
                return 'short duration'
            elif any(keyword in scheme_name for keyword in ['medium duration']):
                return 'medium duration'
            elif any(keyword in scheme_name for keyword in ['long duration']):
                return 'long duration'
            else:
                return 'debt'
        
        elif asset_class == 'hybrid':
            if any(keyword in scheme_name for keyword in ['balanced']):
                return 'balanced'
            elif any(keyword in scheme_name for keyword in ['aggressive']):
                return 'aggressive hybrid'
            elif any(keyword in scheme_name for keyword in ['conservative']):
                return 'conservative hybrid'
            else:
                return 'hybrid'
        
        return 'other'
    
    def _determine_scheme_type(self, scheme_name: str, text: str) -> str:
        """Determine scheme type"""
        if any(keyword in scheme_name for keyword in ['growth', 'equity']):
            return 'Growth'
        elif any(keyword in scheme_name for keyword in ['dividend', 'idcw']):
            return 'IDCW'
        elif any(keyword in scheme_name for keyword in ['regular']):
            return 'Regular'
        else:
            return 'Growth'  # Default
    
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
                # Check if we've moved to a new section
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
