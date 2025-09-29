"""
Configuration file for the factsheet extraction system
"""
import os
from dotenv import load_dotenv

load_dotenv()

# MongoDB Configuration
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
DATABASE_NAME = os.getenv('DATABASE_NAME', 'pluto_money_factsheets')
COLLECTION_NAME = os.getenv('COLLECTION_NAME', 'scheme_data')

# File paths
FACTSHEETS_DIR = os.path.join(os.path.dirname(__file__), 'factsheets')
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'output')

# Data extraction patterns
NAV_PATTERNS = [
    r'NAV.*?(\d+\.?\d*)',
    r'Net Asset Value.*?(\d+\.?\d*)',
    r'Regular.*?(\d+\.?\d*)',
    r'Growth.*?(\d+\.?\d*)',
    r'IDCW.*?(\d+\.?\d*)'
]

AUM_PATTERNS = [
    r'AUM.*?(\d+\.?\d*)\s*(?:Cr|Crore|Lakh|Million|Billion)',
    r'Assets Under Management.*?(\d+\.?\d*)\s*(?:Cr|Crore|Lakh|Million|Billion)',
    r'Total AUM.*?(\d+\.?\d*)\s*(?:Cr|Crore|Lakh|Million|Billion)'
]

DATE_PATTERNS = [
    r'(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
    r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4})',
    r'(\d{2,4}[\/\-]\d{1,2}[\/\-]\d{1,2})'
]

# Asset classes and sub-classes mapping
ASSET_CLASSES = {
    'equity': ['large cap', 'mid cap', 'small cap', 'flexi cap', 'multi cap', 'value', 'growth', 'sectoral', 'thematic'],
    'debt': ['corporate bond', 'government securities', 'money market', 'short duration', 'medium duration', 'long duration', 'credit risk', 'gilt'],
    'hybrid': ['balanced', 'aggressive hybrid', 'conservative hybrid', 'equity savings', 'arbitrage'],
    'solution': ['retirement', 'children', 'tax saving'],
    'other': ['index', 'etf', 'fund of funds', 'international']
}

# Risk levels
RISK_LEVELS = ['Low', 'Moderately Low', 'Moderate', 'Moderately High', 'High']

# Create output directory if it doesn't exist
os.makedirs(OUTPUT_DIR, exist_ok=True)
