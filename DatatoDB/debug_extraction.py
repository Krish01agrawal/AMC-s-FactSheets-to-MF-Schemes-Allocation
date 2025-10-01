#!/usr/bin/env python3
"""
Debug script to test text extraction and LLM response
"""

import os
import json
import re
from pathlib import Path
from advanced_pdf_extractor import AdvancedPDFExtractor
from scalable_amc_extractor import ScalableAMCExtractor

def debug_sbi_extraction():
    """Debug SBI extraction specifically"""
    print("🔍 Debugging SBI extraction...")
    
    # Initialize extractor
    extractor = ScalableAMCExtractor()
    pdf_path = "factsheets/AL Scheme factsheet August_SBI.pdf"
    
    # Extract text
    extraction_result = extractor.pdf_extractor.extract_text_from_pdf(pdf_path)
    full_text = extraction_result.get('full_text', '')
    
    print(f"📊 Total text length: {len(full_text)} chars")
    
    # Test scheme detection
    schemes = extractor._extract_table_of_contents(full_text, "SBI")
    print(f"📊 Found {len(schemes)} schemes")
    
    # Test first scheme extraction
    if schemes:
        first_scheme = schemes[0]
        print(f"🎯 Testing scheme: {first_scheme['name']}")
        print(f"📄 Page: {first_scheme.get('page', 'N/A')}")
        
        # Extract text for this scheme
        scheme_text = extractor._extract_scheme_data_with_gemini(
            full_text, 
            first_scheme['name'], 
            "SBI",
            first_scheme.get('page', 'N/A')
        )
        
        # Just return the text, not the LLM response
        return scheme_text

def debug_text_content():
    """Debug what text is actually being extracted"""
    print("🔍 Debugging text content...")
    
    extractor = ScalableAMCExtractor()
    pdf_path = "factsheets/AL Scheme factsheet August_SBI.pdf"
    
    # Extract text
    extraction_result = extractor.pdf_extractor.extract_text_from_pdf(pdf_path)
    full_text = extraction_result.get('full_text', '')
    
    # Look for SBI Large Cap Fund specifically
    scheme_name = "SBI Large Cap Fund"
    scheme_pattern = re.escape(scheme_name)
    match = re.search(scheme_pattern, full_text, re.IGNORECASE)
    
    if match:
        start_pos = max(0, match.start() - 2000)
        end_pos = min(len(full_text), match.end() + 10000)
        scheme_text = full_text[start_pos:end_pos]
        
        print(f"📊 Found {scheme_name} at position {match.start()}")
        print(f"📊 Extracted {len(scheme_text)} chars")
        print("=" * 80)
        print("EXTRACTED TEXT:")
        print("=" * 80)
        print(scheme_text[:2000])  # First 2000 chars
        print("=" * 80)
        print("... (truncated)")
        
        # Look for key data points
        print("\n🔍 Looking for key data points:")
        
        # AUM
        aum_match = re.search(r'AUM.*?₹[\d,]+\.?\d*\s*[Cc]r', scheme_text, re.IGNORECASE)
        if aum_match:
            print(f"✅ Found AUM: {aum_match.group()}")
        else:
            print("❌ AUM not found")
        
        # NAV
        nav_match = re.search(r'NAV.*?₹[\d,]+\.?\d*', scheme_text, re.IGNORECASE)
        if nav_match:
            print(f"✅ Found NAV: {nav_match.group()}")
        else:
            print("❌ NAV not found")
        
        # Fund Manager
        fm_match = re.search(r'Fund Manager.*?Mr\.\s+[A-Za-z\s]+', scheme_text, re.IGNORECASE)
        if fm_match:
            print(f"✅ Found Fund Manager: {fm_match.group()}")
        else:
            print("❌ Fund Manager not found")
        
        # Benchmark
        bench_match = re.search(r'Benchmark.*?[A-Za-z\s]+\(TRI\)', scheme_text, re.IGNORECASE)
        if bench_match:
            print(f"✅ Found Benchmark: {bench_match.group()}")
        else:
            print("❌ Benchmark not found")
        
        # Expense Ratio
        exp_match = re.search(r'Expense Ratio.*?\d+\.\d+%', scheme_text, re.IGNORECASE)
        if exp_match:
            print(f"✅ Found Expense Ratio: {exp_match.group()}")
        else:
            print("❌ Expense Ratio not found")
        
        return scheme_text
    else:
        print(f"❌ {scheme_name} not found in text")
        return None

if __name__ == "__main__":
    print("🚀 Starting debug extraction...")
    
    # Debug text content
    text = debug_text_content()
    
    if text:
        print(f"\n📊 Text extraction successful: {len(text)} chars")
    else:
        print("\n❌ Text extraction failed")
