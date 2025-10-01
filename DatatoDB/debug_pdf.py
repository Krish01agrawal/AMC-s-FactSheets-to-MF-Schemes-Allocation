from advanced_pdf_extractor import AdvancedPDFExtractor

extractor = AdvancedPDFExtractor()
text = extractor.extract_text_from_pdf('factsheets/HDFC MF Factsheet - August 2025.pdf')

# Show first 5000 characters
print("="*80)
print("HDFC FACTSHEET TEXT FORMAT:")
print("="*80)
print(text[:5000])
print("\n" + "="*80)
print("SEARCHING FOR 'Fund' patterns:")
print("="*80)

import re
# Find all instances of potential scheme names
matches = re.findall(r'.{0,50}Fund.{0,50}', text[:20000], re.IGNORECASE)
for i, match in enumerate(matches[:20]):
    print(f"{i+1}. {match.strip()}")
