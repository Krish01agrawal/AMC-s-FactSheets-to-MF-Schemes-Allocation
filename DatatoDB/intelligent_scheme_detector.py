"""
Intelligent Scheme Detection Module
Uses context-aware parsing to accurately identify and extract individual schemes from factsheets
"""
import re
import logging
from typing import List, Dict, Any, Tuple
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IntelligentSchemeDetector:
    """Intelligent scheme detector that understands factsheet structure and context"""
    
    def __init__(self):
        self.scheme_patterns = self._initialize_scheme_patterns()
        self.context_patterns = self._initialize_context_patterns()
    
    def _initialize_scheme_patterns(self) -> Dict[str, List[str]]:
        """Initialize patterns for detecting actual scheme names"""
        return {
            # SBI patterns
            'sbi_schemes': [
                r'SBI\s+(?:LARGE\s+CAP\s+FUND|ESG\s+EXCLUSIONARY\s+STRATEGY\s+FUND|MULTICAP\s+FUND|DIVIDEND\s+YIELD\s+FUND|CONTRA\s+FUND|LARGE\s+&\s+MIDCAP\s+FUND|FOCUSED\s+FUND|MIDCAP\s+FUND|MNC\s+FUND|SMALL\s+CAP\s+FUND|FLEXICAP\s+FUND|BANKING\s+&\s+FINANCIAL\s+SERVICES\s+FUND|PSU\s+FUND|HEALTHCARE\s+OPPORTUNITIES\s+FUND|INFRASTRUCTURE\s+FUND|TECHNOLOGY\s+OPPORTUNITIES\s+FUND|EQUITY\s+MINIMUM\s+VARIANCE\s+FUND|CONSUMPTION\s+OPPORTUNITIES\s+FUND|ENERGY\s+OPPORTUNITIES\s+FUND|AUTOMOTIVE\s+OPPORTUNITIES\s+FUND|INNOVATIVE\s+OPPORTUNITIES\s+FUND|QUANT\s+FUND)',
                r'SBI\s+[A-Z][A-Z\s&]+(?:FUND|SCHEME)',
            ],
            # HDFC patterns
            'hdfc_schemes': [
                r'HDFC\s+(?:MULTI\s+CAP\s+FUND|LARGE\s+CAP\s+FUND|SMALL\s+CAP\s+FUND|LARGE\s+AND\s+MID\s+CAP\s+FUND|DIVIDEND\s+YIELD\s+FUND|BANKING\s+&\s+FINANCIAL\s+SERVICES\s+FUND|FLEXI\s+CAP\s+FUND|MANUFACTURING\s+FUND|INNOVATION\s+FUND)',
                r'HDFC\s+[A-Z][A-Z\s&]+(?:FUND|SCHEME)',
            ],
            # Generic patterns
            'generic_schemes': [
                r'[A-Z][A-Z\s&]+(?:FUND|SCHEME)(?:\s*[-–]\s*[A-Z][A-Z\s&]+)?',
                r'[A-Z][A-Z\s&]+(?:FUND|SCHEME)\s*\([^)]+\)',
            ]
        }
    
    def _initialize_context_patterns(self) -> Dict[str, List[str]]:
        """Initialize patterns for identifying scheme context and boundaries"""
        return {
            'scheme_start_indicators': [
                r'^[A-Z][A-Z\s&]+(?:FUND|SCHEME)',
                r'Net Asset Value.*?NAV',
                r'Investment Objective',
                r'Fund Details',
                r'Type of Scheme',
            ],
            'scheme_end_indicators': [
                r'Portfolio.*?Classification',
                r'Quantitative Data',
                r'Riskometer',
                r'This product is suitable',
                r'Page\s+\d+',
                r'^[A-Z][A-Z\s&]+(?:FUND|SCHEME)',  # Next scheme
            ],
            'nav_section': [
                r'NAV.*?\(As On|Net Asset Value',
                r'Option.*?NAV.*?₹',
                r'Regular.*?Plan.*?Growth',
            ],
            'fund_details_section': [
                r'Fund Details',
                r'Type of Scheme',
                r'Date of Allotment',
                r'Fund Manager',
                r'AUM.*?as on',
            ],
            'performance_section': [
                r'Quantitative Data',
                r'Standard Deviation',
                r'Beta',
                r'Sharpe Ratio',
                r'Portfolio Turnover',
            ],
            'portfolio_section': [
                r'Portfolio.*?Classification',
                r'Industry Allocation',
                r'Asset Allocation',
                r'Top Holdings',
            ]
        }
    
    def detect_schemes(self, text: str, amc_name: str = None) -> List[Dict[str, Any]]:
        """
        Detect individual schemes from factsheet text with context awareness
        
        Args:
            text: Full factsheet text
            amc_name: Name of the AMC for better pattern matching
            
        Returns:
            List of detected schemes with their boundaries and context
        """
        schemes = []
        
        # Determine which patterns to use based on AMC
        if amc_name and 'SBI' in amc_name.upper():
            scheme_patterns = self.scheme_patterns['sbi_schemes']
        elif amc_name and 'HDFC' in amc_name.upper():
            scheme_patterns = self.scheme_patterns['hdfc_schemes']
        else:
            scheme_patterns = self.scheme_patterns['generic_schemes']
        
        # Find all potential scheme names
        potential_schemes = []
        for pattern in scheme_patterns:
            matches = re.finditer(pattern, text, re.MULTILINE | re.IGNORECASE)
            for match in matches:
                scheme_name = match.group(0).strip()
                # Clean up the scheme name
                scheme_name = self._clean_scheme_name(scheme_name)
                
                if self._is_valid_scheme_name(scheme_name):
                    potential_schemes.append({
                        'name': scheme_name,
                        'position': match.start(),
                        'end_position': match.end(),
                        'context': self._get_context_around_match(text, match.start(), match.end())
                    })
        
        # Remove duplicates and sort by position
        unique_schemes = {}
        for scheme in potential_schemes:
            if scheme['name'] not in unique_schemes:
                unique_schemes[scheme['name']] = scheme
        
        sorted_schemes = sorted(unique_schemes.values(), key=lambda x: x['position'])
        
        # For each scheme, find its boundaries and extract relevant sections
        for i, scheme in enumerate(sorted_schemes):
            try:
                scheme_data = self._extract_scheme_data(text, scheme, i, len(sorted_schemes))
                if scheme_data:
                    schemes.append(scheme_data)
            except Exception as e:
                logger.error(f"Error extracting scheme {scheme['name']}: {str(e)}")
                continue
        
        logger.info(f"Detected {len(schemes)} valid schemes")
        return schemes
    
    def _clean_scheme_name(self, name: str) -> str:
        """Clean and normalize scheme name"""
        # Remove extra whitespace
        name = re.sub(r'\s+', ' ', name.strip())
        
        # Remove common suffixes that aren't part of the scheme name
        name = re.sub(r'\s*\([^)]*\)$', '', name)
        name = re.sub(r'\s*[-–]\s*[A-Z][A-Z\s&]*$', '', name)
        
        # Remove page numbers and other artifacts
        name = re.sub(r'\s*Page\s+\d+.*$', '', name)
        name = re.sub(r'\s*\.{3,}.*$', '', name)
        
        return name.strip()
    
    def _is_valid_scheme_name(self, name: str) -> bool:
        """Check if a name is a valid scheme name"""
        if not name or len(name) < 5:
            return False
        
        # Must contain FUND or SCHEME
        if not re.search(r'(?:FUND|SCHEME)', name, re.IGNORECASE):
            return False
        
        # Should not be too long (likely not a scheme name)
        if len(name) > 100:
            return False
        
        # Should not contain common non-scheme words
        invalid_words = ['CONTENT', 'CATEGORY', 'OVERVIEW', 'SNAPSHOT', 'INDEX', 'PAGE']
        if any(word in name.upper() for word in invalid_words):
            return False
        
        return True
    
    def _get_context_around_match(self, text: str, start: int, end: int, context_size: int = 1000) -> str:
        """Get context around a match for better understanding"""
        context_start = max(0, start - context_size)
        context_end = min(len(text), end + context_size)
        return text[context_start:context_end]
    
    def _extract_scheme_data(self, text: str, scheme: Dict[str, Any], index: int, total_schemes: int) -> Dict[str, Any]:
        """Extract comprehensive data for a single scheme"""
        scheme_name = scheme['name']
        start_pos = scheme['position']
        
        # Find the end position of this scheme
        end_pos = self._find_scheme_end_position(text, start_pos, index, total_schemes)
        
        # Extract the scheme section
        scheme_section = text[start_pos:end_pos]
        
        # Extract different data sections
        nav_section = self._extract_section(scheme_section, self.context_patterns['nav_section'])
        fund_details_section = self._extract_section(scheme_section, self.context_patterns['fund_details_section'])
        performance_section = self._extract_section(scheme_section, self.context_patterns['performance_section'])
        portfolio_section = self._extract_section(scheme_section, self.context_patterns['portfolio_section'])
        
        return {
            'scheme_id': f"scheme_{index}_{hash(scheme_name) % 10000}",
            'name': scheme_name,
            'position': start_pos,
            'end_position': end_pos,
            'sections': {
                'nav_section': nav_section,
                'fund_details_section': fund_details_section,
                'performance_section': performance_section,
                'portfolio_section': portfolio_section
            },
            'full_scheme_text': scheme_section,
            'context': scheme['context']
        }
    
    def _find_scheme_end_position(self, text: str, start_pos: int, index: int, total_schemes: int) -> int:
        """Find where the current scheme ends and the next begins"""
        # Look for scheme end indicators
        end_indicators = self.context_patterns['scheme_end_indicators']
        
        # Search for end indicators after the current scheme start
        search_start = start_pos + 100  # Skip the scheme name itself
        search_end = min(len(text), start_pos + 5000)  # Limit search to reasonable distance
        
        earliest_end = len(text)  # Default to end of text
        
        for pattern in end_indicators:
            matches = list(re.finditer(pattern, text[search_start:search_end], re.MULTILINE | re.IGNORECASE))
            for match in matches:
                match_pos = search_start + match.start()
                if match_pos > start_pos and match_pos < earliest_end:
                    # Check if this is actually the start of the next scheme
                    if 'FUND' in match.group(0).upper() or 'SCHEME' in match.group(0).upper():
                        earliest_end = match_pos
                        break
        
        return earliest_end
    
    def _extract_section(self, text: str, patterns: List[str]) -> str:
        """Extract a specific section based on patterns"""
        for pattern in patterns:
            match = re.search(pattern, text, re.MULTILINE | re.IGNORECASE)
            if match:
                # Extract text from the match to the next section or reasonable limit
                start_pos = match.start()
                end_pos = min(len(text), start_pos + 2000)  # Limit section size
                
                # Look for the next section indicator
                next_section_patterns = [
                    r'^[A-Z][A-Z\s&]+(?:FUND|SCHEME)',
                    r'Portfolio.*?Classification',
                    r'Quantitative Data',
                    r'Riskometer',
                    r'This product is suitable'
                ]
                
                for next_pattern in next_section_patterns:
                    next_match = re.search(next_pattern, text[start_pos + 100:end_pos], re.MULTILINE | re.IGNORECASE)
                    if next_match:
                        end_pos = start_pos + 100 + next_match.start()
                        break
                
                return text[start_pos:end_pos]
        
        return ""
    
    def get_scheme_boundaries(self, text: str, scheme_name: str) -> Tuple[int, int]:
        """Get the start and end boundaries of a specific scheme"""
        # Find the scheme name
        pattern = re.escape(scheme_name)
        match = re.search(pattern, text, re.IGNORECASE)
        
        if not match:
            return 0, len(text)
        
        start_pos = match.start()
        
        # Find the end position
        end_pos = self._find_scheme_end_position(text, start_pos, 0, 1)
        
        return start_pos, end_pos
