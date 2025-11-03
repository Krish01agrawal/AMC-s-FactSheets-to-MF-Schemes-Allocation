#!/usr/bin/env python3
"""
Comprehensive test script for Ultimate Extractor
Tests all factsheets and provides detailed analysis
"""

import json
import sys
from pathlib import Path
from typing import Dict, List
import logging

from ultimate_extractor import UltimateExtractor

logging.basicConfig(level=logging.WARNING)  # Suppress INFO logs
logger = logging.getLogger(__name__)


def analyze_schemes(schemes: List[Dict]) -> Dict:
    """Analyze extraction completeness"""
    
    if not schemes:
        return {}
    
    # Field extraction stats
    field_stats = {}
    
    # Core fields
    core_fields = [
        'Scheme_Name', 'Asset_Class', 'Sub_Class', 'Type_of_Scheme',
        'Date_of_Allotment_(Inception_Date)', 'AUM_(as_of_latest)',
        'Fund_Manager_Name', 'Benchmark', 'Options',
        'Minimum_Monthly_SIP_investment_amount', 'RisKometer_(Risk_Profile)'
    ]
    
    for field in core_fields:
        count = sum(1 for s in schemes if s.get(field) and s[field] != "")
        field_stats[field] = {"count": count, "rate": (count / len(schemes)) * 100}
    
    # Nested fields
    nested_checks = {
        'Expense_Ratio': lambda s: s.get('Expense_Ratio', {}).get('Regular') != "",
        'NAV (Growth or IDCW)': lambda s: (
            s.get('NAV_Value', {}).get('Regular_Growth') != "" or 
            s.get('NAV_Value', {}).get('Regular_IDCW') != ""
        ),
        'Risk_Metrics (any)': lambda s: any([
            s.get('Risk_Metrics', {}).get('Standard_Deviation') != "",
            s.get('Risk_Metrics', {}).get('Beta') != "",
            s.get('Risk_Metrics', {}).get('Sharpe_Ratio') != ""
        ]),
        'CAGR (any period)': lambda s: any([
            s.get('CAGR', {}).get('1Y') != "",
            s.get('CAGR', {}).get('3Y') != "",
            s.get('CAGR', {}).get('5Y') != ""
        ]),
        'Exit_Load (any)': lambda s: any([
            s.get('Exit_Load', {}).get('Under_30_days') != "",
            s.get('Exit_Load', {}).get('After_90_days') != ""
        ]),
        'Turnover': lambda s: s.get('Turnover', {}).get('Equity_Portfolio_Turnover') != "",
    }
    
    for field, check_func in nested_checks.items():
        count = sum(1 for s in schemes if check_func(s))
        field_stats[field] = {"count": count, "rate": (count / len(schemes)) * 100}
    
    # Completeness distribution
    completeness_values = [s.get('_completeness', 0) for s in schemes]
    avg_completeness = sum(completeness_values) / len(completeness_values)
    min_completeness = min(completeness_values)
    max_completeness = max(completeness_values)
    
    return {
        'total_schemes': len(schemes),
        'avg_completeness': avg_completeness,
        'min_completeness': min_completeness,
        'max_completeness': max_completeness,
        'field_stats': field_stats
    }


def print_report(pdf_name: str, result: Dict, analysis: Dict):
    """Print formatted report"""
    
    print(f"\n{'='*90}")
    print(f"📊 EXTRACTION REPORT: {pdf_name}")
    print(f"{'='*90}")
    
    print(f"\n🎯 AMC: {result['amc']}")
    print(f"📄 Total Schemes: {analysis['total_schemes']}")
    print(f"📈 Average Completeness: {analysis['avg_completeness']:.1f}%")
    print(f"   Range: {analysis['min_completeness']:.1f}% - {analysis['max_completeness']:.1f}%")
    
    print(f"\n📊 FIELD EXTRACTION RATES:")
    print(f"{'-'*90}")
    
    # Sort by rate
    field_stats = analysis['field_stats']
    sorted_fields = sorted(field_stats.items(), key=lambda x: x[1]['rate'], reverse=True)
    
    for field, stats in sorted_fields:
        rate = stats['rate']
        count = stats['count']
        total = analysis['total_schemes']
        
        if rate >= 70:
            icon = "✅"
            color = "GREEN"
        elif rate >= 40:
            icon = "⚠️"
            color = "YELLOW"
        else:
            icon = "❌"
            color = "RED"
        
        print(f"  {icon} {field:40s}: {count:3d}/{total:3d} = {rate:5.1f}%")
    
    print(f"{'-'*90}")


def main():
    """Main test function"""
    
    print("\n" + "="*90)
    print("🚀 ULTIMATE EXTRACTOR - COMPREHENSIVE TEST")
    print("="*90)
    
    # Get factsheets
    factsheets_dir = Path("factsheets")
    
    if len(sys.argv) > 1:
        pdf_files = [Path(sys.argv[1])]
    else:
        pdf_files = list(factsheets_dir.glob("*.pdf"))
    
    if not pdf_files:
        print("❌ No factsheets found!")
        sys.exit(1)
    
    print(f"\n📂 Testing {len(pdf_files)} factsheet(s)...")
    
    extractor = UltimateExtractor()
    all_results = []
    
    for pdf_path in pdf_files:
        try:
            print(f"\n⏳ Processing: {pdf_path.name}...")
            
            # Extract
            result = extractor.process_pdf(str(pdf_path))
            
            # Analyze
            analysis = analyze_schemes(result['schemes'])
            
            # Print report
            print_report(pdf_path.name, result, analysis)
            
            # Save
            output_path = Path("output") / f"{pdf_path.stem}_ultimate.json"
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            print(f"\n💾 Saved to: {output_path}")
            
            all_results.append({
                'pdf': pdf_path.name,
                'amc': result['amc'],
                'result': result,
                'analysis': analysis
            })
        
        except Exception as e:
            print(f"\n❌ ERROR processing {pdf_path.name}: {e}")
            import traceback
            traceback.print_exc()
    
    # Print overall summary
    if len(all_results) > 1:
        print(f"\n{'='*90}")
        print("📊 OVERALL SUMMARY - ALL AMCs")
        print(f"={'='*90}")
        
        total_schemes = sum(r['analysis']['total_schemes'] for r in all_results)
        overall_avg = sum(r['analysis']['avg_completeness'] for r in all_results) / len(all_results)
        
        print(f"\n✅ Successfully processed: {len(all_results)} factsheets")
        print(f"📊 Total schemes extracted: {total_schemes}")
        print(f"📈 Overall average completeness: {overall_avg:.1f}%")
        
        print(f"\n📄 Breakdown by AMC:")
        print(f"{'-'*90}")
        for r in all_results:
            amc = r['amc']
            schemes = r['analysis']['total_schemes']
            completeness = r['analysis']['avg_completeness']
            print(f"  • {amc:10s}: {schemes:3d} schemes | {completeness:5.1f}% completeness")
        
        print(f"{'-'*90}")
        
        # Success criteria
        print(f"\n🎯 SUCCESS CRITERIA:")
        if overall_avg >= 70:
            print(f"  ✅ Target achieved! ({overall_avg:.1f}% >= 70%)")
        elif overall_avg >= 60:
            print(f"  ⚠️  Close to target ({overall_avg:.1f}% >= 60%, target: 70%)")
        else:
            print(f"  ❌ Needs improvement ({overall_avg:.1f}% < 60%, target: 70%)")
    
    print(f"\n{'='*90}")
    print("✅ TESTING COMPLETE!")
    print(f"={'='*90}\n")


if __name__ == "__main__":
    main()

