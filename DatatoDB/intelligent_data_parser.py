"""
Intelligent Data Parser for Financial Factsheets
Uses context-aware parsing and layout understanding to extract accurate data
"""
import re
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from bson import ObjectId

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IntelligentDataParser:
    """Intelligent parser that understands factsheet layout and extracts data accurately"""
    
    def __init__(self):
        self.patterns = self._initialize_intelligent_patterns()
        self.context_rules = self._initialize_context_rules()
    
    def _initialize_intelligent_patterns(self) -> Dict[str, Dict[str, List[str]]]:
        """Initialize intelligent patterns based on factsheet layout understanding"""
        return {
            'nav_patterns': {
                'regular_growth': [
                    r'Reg-Plan-Growth.*?(\d+\.?\d*)',
                    r'Regular.*?Plan.*?Growth.*?Option.*?(\d+\.?\d*)',
                    r'Growth.*?Option.*?(\d+\.?\d*)',
                    r'NAV.*?Growth.*?(\d+\.?\d*)',
                ],
                'regular_idcw': [
                    r'Reg-Plan-IDCW.*?(\d+\.?\d*)',
                    r'Regular.*?Plan.*?IDCW.*?Option.*?(\d+\.?\d*)',
                    r'IDCW.*?Option.*?(\d+\.?\d*)',
                    r'NAV.*?IDCW.*?(\d+\.?\d*)',
                ],
                'direct_growth': [
                    r'Dir-Plan-Growth.*?(\d+\.?\d*)',
                    r'Direct.*?Plan.*?Growth.*?Option.*?(\d+\.?\d*)',
                    r'Direct.*?Growth.*?(\d+\.?\d*)',
                ],
                'direct_idcw': [
                    r'Dir-Plan-IDCW.*?(\d+\.?\d*)',
                    r'Direct.*?Plan.*?IDCW.*?Option.*?(\d+\.?\d*)',
                    r'Direct.*?IDCW.*?(\d+\.?\d*)',
                ]
            },
            'fund_details_patterns': {
                'aum': [
                    r'AUM.*?as on.*?(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}).*?₹\s*(\d+\.?\d*)\s*(?:Cr|Crore)',
                    r'Assets Under Management.*?₹\s*(\d+\.?\d*)\s*(?:Cr|Crore)',
                    r'Total AUM.*?₹\s*(\d+\.?\d*)\s*(?:Cr|Crore)',
                    r'Fund Size.*?₹\s*(\d+\.?\d*)\s*(?:Cr|Crore)',
                    r'AUM.*?₹\s*(\d+\.?\d*)\s*(?:Cr|Crore)',
                ],
                'inception_date': [
                    r'Date of Allotment[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
                    r'Inception Date[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
                    r'Launch Date[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
                ],
                'fund_manager_name': [
                    r'Fund Manager[:\s]*([^\n\r]+?)(?:\s*Since|\s*Total|\s*Experience|\n)',
                    r'Manager[:\s]*([^\n\r]+?)(?:\s*Since|\s*Total|\s*Experience|\n)',
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
                'benchmark': [
                    r'Benchmark[:\s]*([^\n\r]+)',
                    r'Index[:\s]*([^\n\r]+)',
                    r'Reference Index[:\s]*([^\n\r]+)',
                    r'First Tier Benchmark[:\s]*([^\n\r]+)',
                ],
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
                ],
                'exit_load_after_90_days': [
                    r'Exit Load.*?90.*?days?[:\s]*(\d+\.?\d*%?)',
                    r'After 90 days[:\s]*(\d+\.?\d*%?)',
                    r'90.*?days?.*?Exit Load[:\s]*(\d+\.?\d*%?)',
                ],
                'min_sip_monthly': [
                    r'Minimum.*?SIP.*?Monthly[:\s]*₹?(\d+)',
                    r'Monthly.*?SIP.*?Minimum[:\s]*₹?(\d+)',
                    r'SIP.*?Monthly[:\s]*₹?(\d+)',
                ],
                'expense_ratio': [
                    r'Total Expense Ratio[:\s]*(\d+\.?\d*%?)',
                    r'Expense Ratio[:\s]*(\d+\.?\d*%?)',
                    r'TER[:\s]*(\d+\.?\d*%?)',
                    r'Regular[:\s]*(\d+\.?\d*%?)',
                ]
            },
            'performance_patterns': {
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
                'equity_turnover': [
                    r'Equity.*?Turnover[:\s]*(\d+\.?\d*%?)',
                    r'Portfolio.*?Turnover[:\s]*(\d+\.?\d*%?)',
                    r'Equity.*?Portfolio.*?Turnover[:\s]*(\d+\.?\d*%?)',
                ],
                'total_turnover': [
                    r'Total.*?Turnover[:\s]*(\d+\.?\d*%?)',
                    r'Turnover[:\s]*(\d+\.?\d*%?)',
                ]
            },
            'risk_patterns': {
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
                'riskometer': [
                    r'Riskometer[:\s]*([^\n\r]+)',
                    r'Risk Level[:\s]*([^\n\r]+)',
                    r'Risk Profile[:\s]*([^\n\r]+)',
                    r'Very High|High|Moderate|Low',
                ]
            },
            'debt_patterns': {
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
                ]
            }
        }
    
    def _initialize_context_rules(self) -> Dict[str, Any]:
        """Initialize context rules for better data extraction"""
        return {
            'nav_table_context': {
                'indicators': [r'NAV.*?\(As On', r'Option.*?NAV.*?₹', r'Net Asset Value'],
                'extraction_method': 'table_parsing'
            },
            'fund_details_context': {
                'indicators': [r'Fund Details', r'Type of Scheme', r'Date of Allotment'],
                'extraction_method': 'section_parsing'
            },
            'performance_context': {
                'indicators': [r'Quantitative Data', r'Standard Deviation', r'Beta'],
                'extraction_method': 'section_parsing'
            },
            'portfolio_context': {
                'indicators': [r'Portfolio.*?Classification', r'Industry Allocation', r'Asset Allocation'],
                'extraction_method': 'table_parsing'
            }
        }
    
    def parse_scheme_data(self, scheme_data: Dict[str, Any], extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse individual scheme data with intelligent context awareness
        
        Args:
            scheme_data: Scheme data from intelligent detector
            extracted_data: Raw extracted data from PDF
            
        Returns:
            Structured scheme data
        """
        try:
            scheme_text = scheme_data.get('full_scheme_text', '')
            if not scheme_text:
                return None
            
            # Initialize result structure
            result = {
                '_id': ObjectId(),
                'scheme_id': scheme_data.get('scheme_id'),
                'basic_info': {
                    'scheme_name': scheme_data.get('name', ''),
                    'amc_name': self._extract_amc_name(scheme_text, extracted_data),
                    'file_name': extracted_data.get('file_name', ''),
                    'extraction_date': datetime.now().isoformat(),
                    'asset_class': self._determine_asset_class(scheme_text),
                    'sub_class': self._determine_sub_class(scheme_text),
                    'scheme_type': self._determine_scheme_type(scheme_text),
                },
                'nav_data': self._extract_nav_data_intelligent(scheme_text),
                'fund_details': self._extract_fund_details_intelligent(scheme_text),
                'performance_metrics': self._extract_performance_metrics_intelligent(scheme_text),
                'risk_metrics': self._extract_risk_metrics_intelligent(scheme_text),
                'debt_metrics': self._extract_debt_metrics_intelligent(scheme_text),
                'portfolio_data': self._extract_portfolio_data_intelligent(scheme_text),
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error parsing scheme data: {str(e)}")
            return None
    
    def _extract_nav_data_intelligent(self, text: str) -> Dict:
        """Extract NAV data with intelligent table parsing"""
        nav_data = {}
        
        # Look for NAV table context
        nav_section = self._find_section_by_context(text, 'nav_table_context')
        
        if nav_section:
            # Extract using table parsing
            nav_data.update(self._parse_nav_table(nav_section))
        else:
            # Fallback to pattern matching
            for field, patterns in self.patterns['nav_patterns'].items():
                nav_data[field] = self._extract_value_intelligent(text, patterns)
        
        return nav_data
    
    def _parse_nav_table(self, nav_section: str) -> Dict:
        """Parse NAV data from table format"""
        nav_data = {}
        
        # Look for table rows with NAV values
        table_rows = re.findall(r'([A-Za-z\s-]+)\s*\|?\s*(\d+\.?\d*)', nav_section)
        
        for row in table_rows:
            option_name = row[0].strip().lower()
            nav_value = float(row[1])
            
            if 'reg' in option_name and 'growth' in option_name:
                nav_data['regular_growth'] = nav_value
            elif 'reg' in option_name and 'idcw' in option_name:
                nav_data['regular_idcw'] = nav_value
            elif 'dir' in option_name and 'growth' in option_name:
                nav_data['direct_growth'] = nav_value
            elif 'dir' in option_name and 'idcw' in option_name:
                nav_data['direct_idcw'] = nav_value
        
        return nav_data
    
    def _extract_fund_details_intelligent(self, text: str) -> Dict:
        """Extract fund details with intelligent section parsing"""
        fund_details = {}
        
        # Look for fund details section
        fund_section = self._find_section_by_context(text, 'fund_details_context')
        
        if fund_section:
            # Extract using section parsing
            for field, patterns in self.patterns['fund_details_patterns'].items():
                fund_details[field] = self._extract_value_intelligent(fund_section, patterns)
        else:
            # Fallback to full text
            for field, patterns in self.patterns['fund_details_patterns'].items():
                fund_details[field] = self._extract_value_intelligent(text, patterns)
        
        return fund_details
    
    def _extract_performance_metrics_intelligent(self, text: str) -> Dict:
        """Extract performance metrics with intelligent parsing"""
        performance = {}
        
        # Look for performance section
        perf_section = self._find_section_by_context(text, 'performance_context')
        
        if perf_section:
            for field, patterns in self.patterns['performance_patterns'].items():
                performance[field] = self._extract_value_intelligent(perf_section, patterns)
        else:
            for field, patterns in self.patterns['performance_patterns'].items():
                performance[field] = self._extract_value_intelligent(text, patterns)
        
        return performance
    
    def _extract_risk_metrics_intelligent(self, text: str) -> Dict:
        """Extract risk metrics with intelligent parsing"""
        risk_metrics = {}
        
        # Look for performance section (risk metrics are usually there)
        perf_section = self._find_section_by_context(text, 'performance_context')
        
        if perf_section:
            for field, patterns in self.patterns['risk_patterns'].items():
                risk_metrics[field] = self._extract_value_intelligent(perf_section, patterns)
        else:
            for field, patterns in self.patterns['risk_patterns'].items():
                risk_metrics[field] = self._extract_value_intelligent(text, patterns)
        
        return risk_metrics
    
    def _extract_debt_metrics_intelligent(self, text: str) -> Dict:
        """Extract debt-specific metrics"""
        debt_metrics = {}
        
        for field, patterns in self.patterns['debt_patterns'].items():
            debt_metrics[field] = self._extract_value_intelligent(text, patterns)
        
        return debt_metrics
    
    def _extract_portfolio_data_intelligent(self, text: str) -> Dict:
        """Extract portfolio data with intelligent table parsing"""
        portfolio_data = {}
        
        # Look for portfolio section
        portfolio_section = self._find_section_by_context(text, 'portfolio_context')
        
        if portfolio_section:
            # Extract industry allocation
            industry_allocation = self._parse_industry_allocation_table(portfolio_section)
            portfolio_data['industry_allocation'] = industry_allocation
            
            # Extract asset allocation
            asset_allocation = self._parse_asset_allocation_table(portfolio_section)
            portfolio_data['asset_allocation'] = asset_allocation
            
            # Extract top holdings
            top_holdings = self._parse_top_holdings_table(portfolio_section)
            portfolio_data['top_holdings'] = top_holdings
        else:
            # Fallback to pattern matching
            portfolio_data['industry_allocation'] = {}
            portfolio_data['asset_allocation'] = {}
            portfolio_data['top_holdings'] = []
        
        return portfolio_data
    
    def _parse_industry_allocation_table(self, text: str) -> Dict[str, float]:
        """Parse industry allocation from table format"""
        industry_allocation = {}
        
        # Look for industry allocation patterns
        industry_patterns = [
            r'([A-Za-z\s&\.]+)\s+(\d+\.?\d*%?)',
            r'([A-Za-z\s&\.]+)\s*:\s*(\d+\.?\d*%?)',
        ]
        
        for pattern in industry_patterns:
            matches = re.findall(pattern, text)
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
    
    def _parse_asset_allocation_table(self, text: str) -> Dict[str, float]:
        """Parse asset allocation from table format"""
        asset_allocation = {}
        
        # Common asset types
        asset_types = ['equity', 'debt', 'cash', 'others', 'derivatives', 'large cap', 'mid cap', 'small cap']
        
        for asset_type in asset_types:
            pattern = rf'{asset_type}[:\s]*(\d+\.?\d*%?)'
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    percentage = float(re.sub(r'[^\d.]', '', match.group(1)))
                    if 0 <= percentage <= 100:
                        asset_allocation[asset_type] = percentage
                except ValueError:
                    continue
        
        return asset_allocation
    
    def _parse_top_holdings_table(self, text: str) -> List[Dict[str, str]]:
        """Parse top holdings from table format"""
        holdings = []
        
        # Look for holdings table patterns
        holding_patterns = [
            r'([A-Za-z\s&\.]+)\s+(\d+\.?\d*%?)',
            r'([A-Za-z\s&\.]+)\s*:\s*(\d+\.?\d*%?)',
        ]
        
        for pattern in holding_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                company = match[0].strip()
                percentage = match[1].strip()
                
                if company and percentage and len(company) > 2:
                    holdings.append({
                        'company': company,
                        'percentage': percentage
                    })
        
        return holdings[:10]  # Return top 10 holdings
    
    def _find_section_by_context(self, text: str, context_type: str) -> str:
        """Find section based on context rules"""
        if context_type not in self.context_rules:
            return ""
        
        context_rule = self.context_rules[context_type]
        indicators = context_rule['indicators']
        
        for indicator in indicators:
            match = re.search(indicator, text, re.IGNORECASE)
            if match:
                # Extract section from match to next section or reasonable limit
                start_pos = match.start()
                end_pos = min(len(text), start_pos + 2000)
                
                # Look for next section
                next_section_patterns = [
                    r'^[A-Z][A-Z\s&]+(?:FUND|SCHEME)',
                    r'Portfolio.*?Classification',
                    r'Quantitative Data',
                    r'Riskometer',
                    r'This product is suitable'
                ]
                
                for next_pattern in next_section_patterns:
                    next_match = re.search(next_pattern, text[start_pos + 100:end_pos], re.IGNORECASE)
                    if next_match:
                        end_pos = start_pos + 100 + next_match.start()
                        break
                
                return text[start_pos:end_pos]
        
        return ""
    
    def _extract_value_intelligent(self, text: str, patterns: List[str]) -> Optional[Any]:
        """Extract value using intelligent pattern matching"""
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
