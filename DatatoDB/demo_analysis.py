"""
Demo Analysis Script
Demonstrates the analysis capabilities of the factsheet extraction system
"""
import json
from analysis_engine import FactsheetAnalysisEngine
from mongodb_interface import MongoDBInterface

def main():
    """Run comprehensive analysis demo"""
    print("="*60)
    print("PLUTO MONEY FACTSHEET ANALYSIS DEMO")
    print("="*60)
    
    try:
        # Initialize analysis engine
        print("\n1. Initializing Analysis Engine...")
        analysis_engine = FactsheetAnalysisEngine()
        
        # Get comprehensive analysis
        print("\n2. Generating Comprehensive Analysis...")
        analysis = analysis_engine.get_comprehensive_analysis()
        
        # Display Market Overview
        print("\n3. MARKET OVERVIEW")
        print("-" * 30)
        market_overview = analysis.get('market_overview', {})
        print(f"Total Schemes: {market_overview.get('total_schemes', 0)}")
        print(f"Total AMCs: {market_overview.get('total_amcs', 0)}")
        print(f"Estimated Total AUM: {market_overview.get('estimated_total_aum', 0)} Cr")
        print(f"Average Expense Ratio: {market_overview.get('average_expense_ratio', 0)}%")
        
        asset_distribution = market_overview.get('asset_class_distribution', {})
        if asset_distribution:
            print("\nAsset Class Distribution:")
            for asset_class, count in asset_distribution.items():
                print(f"  {asset_class.title()}: {count} schemes")
        
        # Display Performance Analysis
        print("\n4. PERFORMANCE ANALYSIS")
        print("-" * 30)
        performance_analysis = analysis.get('performance_analysis', {})
        
        for asset_class, metrics in performance_analysis.items():
            print(f"\n{asset_class.title()} Funds:")
            if 'cagr_3y' in metrics:
                cagr_3y = metrics['cagr_3y']
                print(f"  Average 3Y CAGR: {cagr_3y.get('mean', 0)}%")
                print(f"  Best 3Y CAGR: {cagr_3y.get('max', 0)}%")
                print(f"  Worst 3Y CAGR: {cagr_3y.get('min', 0)}%")
            
            if 'sharpe_ratio' in metrics:
                sharpe = metrics['sharpe_ratio']
                print(f"  Average Sharpe Ratio: {sharpe.get('mean', 0)}")
        
        # Display Risk Analysis
        print("\n5. RISK ANALYSIS")
        print("-" * 30)
        risk_analysis = analysis.get('risk_analysis', {})
        risk_stats = risk_analysis.get('risk_statistics', {})
        
        if 'beta_distribution' in risk_stats:
            beta_stats = risk_stats['beta_distribution']
            print(f"Average Beta: {beta_stats.get('mean', 0)}")
            print(f"Beta Range: {beta_stats.get('min', 0)} - {beta_stats.get('max', 0)}")
        
        if 'standard_deviation_distribution' in risk_stats:
            std_stats = risk_stats['standard_deviation_distribution']
            print(f"Average Standard Deviation: {std_stats.get('mean', 0)}%")
        
        # Display AMC Comparison
        print("\n6. AMC COMPARISON")
        print("-" * 30)
        amc_comparison = analysis.get('amc_comparison', [])
        
        if amc_comparison:
            print("Top AMCs by Scheme Count:")
            for i, amc in enumerate(amc_comparison[:5], 1):
                print(f"  {i}. {amc.get('amc_name', 'Unknown')}: {amc.get('total_schemes', 0)} schemes")
                print(f"     Avg AUM: {amc.get('avg_aum', 0)} Cr")
                print(f"     Avg Expense Ratio: {amc.get('avg_expense_ratio', 0)}%")
        
        # Display Investment Insights
        print("\n7. INVESTMENT INSIGHTS")
        print("-" * 30)
        insights = analysis.get('investment_insights', {})
        
        market_trends = insights.get('market_trends', [])
        if market_trends:
            print("Market Trends:")
            for trend in market_trends[:3]:
                print(f"  • {trend}")
        
        performance_insights = insights.get('performance_insights', [])
        if performance_insights:
            print("\nPerformance Insights:")
            for insight in performance_insights[:3]:
                print(f"  • {insight}")
        
        risk_insights = insights.get('risk_insights', [])
        if risk_insights:
            print("\nRisk Insights:")
            for insight in risk_insights[:3]:
                print(f"  • {insight}")
        
        # Display Recommendations
        print("\n8. INVESTMENT RECOMMENDATIONS")
        print("-" * 30)
        recommendations = analysis.get('recommendations', {})
        
        conservative = recommendations.get('conservative_investors', [])
        if conservative:
            print("For Conservative Investors:")
            for rec in conservative[:2]:
                print(f"  • {rec}")
        
        moderate = recommendations.get('moderate_investors', [])
        if moderate:
            print("\nFor Moderate Investors:")
            for rec in moderate[:2]:
                print(f"  • {rec}")
        
        aggressive = recommendations.get('aggressive_investors', [])
        if aggressive:
            print("\nFor Aggressive Investors:")
            for rec in aggressive[:2]:
                print(f"  • {rec}")
        
        general = recommendations.get('general_recommendations', [])
        if general:
            print("\nGeneral Recommendations:")
            for rec in general:
                print(f"  • {rec}")
        
        # Save detailed analysis report
        print("\n9. SAVING DETAILED ANALYSIS REPORT...")
        report_file = analysis_engine.generate_analysis_report()
        print(f"Detailed report saved to: {report_file}")
        
        print("\n" + "="*60)
        print("ANALYSIS COMPLETE!")
        print("="*60)
        
        # Display database statistics
        print("\n10. DATABASE STATISTICS")
        print("-" * 30)
        db_interface = MongoDBInterface()
        stats = db_interface.get_database_stats()
        
        print(f"Total Schemes in Database: {stats.get('total_schemes', 0)}")
        print(f"Total AMCs in Database: {stats.get('total_amcs', 0)}")
        print(f"Recent Updates: {stats.get('recent_updates', 0)}")
        
        db_interface.close_connection()
        
    except Exception as e:
        print(f"Error during analysis: {str(e)}")
        raise

if __name__ == "__main__":
    main()
