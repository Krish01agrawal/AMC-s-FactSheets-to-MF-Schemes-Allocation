"""
Analysis Engine for Factsheet Data
Provides insights, trends, and investment recommendations
"""
import logging
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from advanced_mongodb_interface import AdvancedMongoDBInterface

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FactsheetAnalysisEngine:
    """Advanced analysis engine for factsheet data"""
    
    def __init__(self, db_interface: AdvancedMongoDBInterface = None):
        self.db_interface = db_interface or AdvancedMongoDBInterface()
    
    def get_comprehensive_analysis(self) -> Dict[str, Any]:
        """Get comprehensive analysis of all factsheet data"""
        try:
            analysis = {
                'market_overview': self._get_market_overview(),
                'performance_analysis': self._get_performance_analysis(),
                'risk_analysis': self._get_risk_analysis(),
                'amc_comparison': self._get_amc_comparison(),
                'asset_class_analysis': self._get_asset_class_analysis(),
                'investment_insights': self._get_investment_insights(),
                'trends': self._get_market_trends(),
                'recommendations': self._get_investment_recommendations()
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to get comprehensive analysis: {str(e)}")
            return {}
    
    def _get_market_overview(self) -> Dict[str, Any]:
        """Get market overview statistics"""
        try:
            stats = self.db_interface.get_database_stats()
            
            # Get additional market data
            all_schemes = self.db_interface.get_all_schemes(limit=1000)
            
            total_aum = 0
            avg_expense_ratio = 0
            scheme_count = len(all_schemes)
            
            for scheme in all_schemes:
                aum = scheme.get('fund_details', {}).get('aum', 0)
                expense_ratio = scheme.get('fund_details', {}).get('expense_ratio', 0)
                
                if aum:
                    total_aum += float(aum)
                if expense_ratio:
                    avg_expense_ratio += float(expense_ratio)
            
            if scheme_count > 0:
                avg_expense_ratio = avg_expense_ratio / scheme_count
            
            return {
                'total_schemes': stats.get('total_schemes', 0),
                'total_amcs': stats.get('total_amcs', 0),
                'estimated_total_aum': total_aum,
                'average_expense_ratio': round(avg_expense_ratio, 2),
                'asset_class_distribution': stats.get('asset_class_distribution', {}),
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get market overview: {str(e)}")
            return {}
    
    def _get_performance_analysis(self) -> Dict[str, Any]:
        """Get performance analysis across all schemes"""
        try:
            all_schemes = self.db_interface.get_all_schemes(limit=1000)
            
            performance_data = {
                'equity': {'cagr_1y': [], 'cagr_3y': [], 'cagr_5y': [], 'sharpe_ratio': []},
                'debt': {'cagr_1y': [], 'cagr_3y': [], 'cagr_5y': [], 'sharpe_ratio': []},
                'hybrid': {'cagr_1y': [], 'cagr_3y': [], 'cagr_5y': [], 'sharpe_ratio': []}
            }
            
            for scheme in all_schemes:
                asset_class = scheme.get('asset_classification', {}).get('asset_class', 'other')
                performance = scheme.get('performance_metrics', {})
                risk_metrics = scheme.get('risk_metrics', {})
                
                if asset_class in performance_data:
                    # Collect CAGR data
                    for period in ['cagr_1y', 'cagr_3y', 'cagr_5y']:
                        value = performance.get(period)
                        if value:
                            performance_data[asset_class][period].append(float(value))
                    
                    # Collect Sharpe ratio
                    sharpe = risk_metrics.get('sharpe_ratio')
                    if sharpe:
                        performance_data[asset_class]['sharpe_ratio'].append(float(sharpe))
            
            # Calculate statistics
            analysis = {}
            for asset_class, data in performance_data.items():
                analysis[asset_class] = {}
                for metric, values in data.items():
                    if values:
                        analysis[asset_class][metric] = {
                            'mean': round(np.mean(values), 2),
                            'median': round(np.median(values), 2),
                            'std': round(np.std(values), 2),
                            'min': round(np.min(values), 2),
                            'max': round(np.max(values), 2),
                            'count': len(values)
                        }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to get performance analysis: {str(e)}")
            return {}
    
    def _get_risk_analysis(self) -> Dict[str, Any]:
        """Get risk analysis across all schemes"""
        try:
            risk_analysis = self.db_interface.get_risk_analysis()
            
            # Additional risk metrics
            all_schemes = self.db_interface.get_all_schemes(limit=1000)
            
            risk_metrics = {
                'beta_distribution': [],
                'standard_deviation_distribution': [],
                'sharpe_ratio_distribution': [],
                'risk_level_distribution': {}
            }
            
            for scheme in all_schemes:
                risk_metrics_data = scheme.get('risk_metrics', {})
                riskometer = scheme.get('riskometer', 'Unknown')
                
                # Collect risk metrics
                beta = risk_metrics_data.get('beta')
                if beta:
                    risk_metrics['beta_distribution'].append(float(beta))
                
                std_dev = risk_metrics_data.get('standard_deviation')
                if std_dev:
                    risk_metrics['standard_deviation_distribution'].append(float(std_dev))
                
                sharpe = risk_metrics_data.get('sharpe_ratio')
                if sharpe:
                    risk_metrics['sharpe_ratio_distribution'].append(float(sharpe))
                
                # Count risk levels
                risk_metrics['risk_level_distribution'][riskometer] = \
                    risk_metrics['risk_level_distribution'].get(riskometer, 0) + 1
            
            # Calculate risk statistics
            risk_stats = {}
            for metric, values in risk_metrics.items():
                if values and isinstance(values, list):
                    risk_stats[metric] = {
                        'mean': round(np.mean(values), 2),
                        'median': round(np.median(values), 2),
                        'std': round(np.std(values), 2),
                        'min': round(np.min(values), 2),
                        'max': round(np.max(values), 2)
                    }
                elif isinstance(values, dict):
                    risk_stats[metric] = values
            
            return {
                'riskometer_distribution': risk_analysis,
                'risk_statistics': risk_stats
            }
            
        except Exception as e:
            logger.error(f"Failed to get risk analysis: {str(e)}")
            return {}
    
    def _get_amc_comparison(self) -> Dict[str, Any]:
        """Get AMC comparison analysis"""
        try:
            amc_comparison = self.db_interface.get_amc_comparison()
            
            # Enhance with additional metrics
            enhanced_comparison = []
            
            for amc_data in amc_comparison:
                amc_name = amc_data['_id']
                schemes = amc_data.get('schemes', [])
                
                # Calculate additional metrics
                equity_schemes = [s for s in schemes if s.get('asset_class') == 'equity']
                debt_schemes = [s for s in schemes if s.get('asset_class') == 'debt']
                hybrid_schemes = [s for s in schemes if s.get('asset_class') == 'hybrid']
                
                enhanced_amc = {
                    'amc_name': amc_name,
                    'total_schemes': amc_data['scheme_count'],
                    'equity_schemes': len(equity_schemes),
                    'debt_schemes': len(debt_schemes),
                    'hybrid_schemes': len(hybrid_schemes),
                    'avg_aum': round(amc_data.get('avg_aum', 0), 2),
                    'avg_expense_ratio': round(amc_data.get('avg_expense_ratio', 0), 2),
                    'schemes': schemes
                }
                
                enhanced_comparison.append(enhanced_amc)
            
            return enhanced_comparison
            
        except Exception as e:
            logger.error(f"Failed to get AMC comparison: {str(e)}")
            return []
    
    def _get_asset_class_analysis(self) -> Dict[str, Any]:
        """Get detailed asset class analysis"""
        try:
            asset_classes = ['equity', 'debt', 'hybrid']
            analysis = {}
            
            for asset_class in asset_classes:
                schemes = self.db_interface.get_schemes_by_asset_class(asset_class)
                
                if not schemes:
                    continue
                
                # Calculate metrics for this asset class
                aum_values = []
                expense_ratios = []
                cagr_1y_values = []
                cagr_3y_values = []
                cagr_5y_values = []
                
                for scheme in schemes:
                    fund_details = scheme.get('fund_details', {})
                    performance = scheme.get('performance_metrics', {})
                    
                    aum = fund_details.get('aum')
                    if aum:
                        aum_values.append(float(aum))
                    
                    expense_ratio = fund_details.get('expense_ratio')
                    if expense_ratio:
                        expense_ratios.append(float(expense_ratio))
                    
                    cagr_1y = performance.get('cagr_1y')
                    if cagr_1y:
                        cagr_1y_values.append(float(cagr_1y))
                    
                    cagr_3y = performance.get('cagr_3y')
                    if cagr_3y:
                        cagr_3y_values.append(float(cagr_3y))
                    
                    cagr_5y = performance.get('cagr_5y')
                    if cagr_5y:
                        cagr_5y_values.append(float(cagr_5y))
                
                analysis[asset_class] = {
                    'total_schemes': len(schemes),
                    'avg_aum': round(np.mean(aum_values), 2) if aum_values else 0,
                    'avg_expense_ratio': round(np.mean(expense_ratios), 2) if expense_ratios else 0,
                    'avg_cagr_1y': round(np.mean(cagr_1y_values), 2) if cagr_1y_values else 0,
                    'avg_cagr_3y': round(np.mean(cagr3y_values), 2) if cagr_3y_values else 0,
                    'avg_cagr_5y': round(np.mean(cagr_5y_values), 2) if cagr_5y_values else 0,
                    'top_performers': self._get_top_performers(schemes, asset_class)
                }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to get asset class analysis: {str(e)}")
            return {}
    
    def _get_investment_insights(self) -> Dict[str, Any]:
        """Generate investment insights and recommendations"""
        try:
            insights = {
                'market_trends': [],
                'performance_insights': [],
                'risk_insights': [],
                'cost_insights': [],
                'diversification_insights': []
            }
            
            # Get market data
            market_overview = self._get_market_overview()
            performance_analysis = self._get_performance_analysis()
            risk_analysis = self._get_risk_analysis()
            
            # Market trends
            asset_distribution = market_overview.get('asset_class_distribution', {})
            if asset_distribution:
                dominant_asset_class = max(asset_distribution, key=asset_distribution.get)
                insights['market_trends'].append(
                    f"{dominant_asset_class.title()} funds dominate the market with {asset_distribution[dominant_asset_class]} schemes"
                )
            
            # Performance insights
            if 'equity' in performance_analysis:
                equity_perf = performance_analysis['equity']
                if 'cagr_3y' in equity_perf:
                    avg_3y_cagr = equity_perf['cagr_3y'].get('mean', 0)
                    insights['performance_insights'].append(
                        f"Average 3-year CAGR for equity funds: {avg_3y_cagr}%"
                    )
            
            # Risk insights
            risk_stats = risk_analysis.get('risk_statistics', {})
            if 'beta_distribution' in risk_stats:
                avg_beta = risk_stats['beta_distribution'].get('mean', 0)
                if avg_beta > 1:
                    insights['risk_insights'].append(
                        f"Average beta of {avg_beta} indicates higher market sensitivity"
                    )
                elif avg_beta < 1:
                    insights['risk_insights'].append(
                        f"Average beta of {avg_beta} indicates lower market sensitivity"
                    )
            
            # Cost insights
            avg_expense_ratio = market_overview.get('average_expense_ratio', 0)
            if avg_expense_ratio > 2:
                insights['cost_insights'].append(
                    f"Average expense ratio of {avg_expense_ratio}% is relatively high"
                )
            elif avg_expense_ratio < 1:
                insights['cost_insights'].append(
                    f"Average expense ratio of {avg_expense_ratio}% is competitive"
                )
            
            return insights
            
        except Exception as e:
            logger.error(f"Failed to get investment insights: {str(e)}")
            return {}
    
    def _get_market_trends(self) -> Dict[str, Any]:
        """Identify market trends and patterns"""
        try:
            trends = {
                'emerging_patterns': [],
                'performance_trends': [],
                'risk_trends': [],
                'cost_trends': []
            }
            
            # Analyze scheme characteristics
            all_schemes = self.db_interface.get_all_schemes(limit=1000)
            
            # Performance trends
            high_performers = []
            for scheme in all_schemes:
                performance = scheme.get('performance_metrics', {})
                cagr_3y = performance.get('cagr_3y')
                if cagr_3y and float(cagr_3y) > 15:  # High performers
                    high_performers.append({
                        'scheme_name': scheme.get('basic_info', {}).get('scheme_name', ''),
                        'amc_name': scheme.get('basic_info', {}).get('amc_name', ''),
                        'cagr_3y': cagr_3y,
                        'asset_class': scheme.get('asset_classification', {}).get('asset_class', '')
                    })
            
            if high_performers:
                trends['performance_trends'].append(
                    f"Found {len(high_performers)} high-performing schemes with 3Y CAGR > 15%"
                )
            
            # Risk trends
            low_risk_schemes = []
            for scheme in all_schemes:
                risk_metrics = scheme.get('risk_metrics', {})
                beta = risk_metrics.get('beta')
                if beta and float(beta) < 0.8:  # Low beta schemes
                    low_risk_schemes.append({
                        'scheme_name': scheme.get('basic_info', {}).get('scheme_name', ''),
                        'beta': beta,
                        'asset_class': scheme.get('asset_classification', {}).get('asset_class', '')
                    })
            
            if low_risk_schemes:
                trends['risk_trends'].append(
                    f"Found {len(low_risk_schemes)} low-risk schemes with beta < 0.8"
                )
            
            return trends
            
        except Exception as e:
            logger.error(f"Failed to get market trends: {str(e)}")
            return {}
    
    def _get_investment_recommendations(self) -> Dict[str, Any]:
        """Generate investment recommendations based on analysis"""
        try:
            recommendations = {
                'conservative_investors': [],
                'moderate_investors': [],
                'aggressive_investors': [],
                'general_recommendations': []
            }
            
            # Get analysis data
            performance_analysis = self._get_performance_analysis()
            risk_analysis = self._get_risk_analysis()
            asset_class_analysis = self._get_asset_class_analysis()
            
            # Conservative investor recommendations
            if 'debt' in asset_class_analysis:
                debt_analysis = asset_class_analysis['debt']
                if debt_analysis.get('avg_cagr_3y', 0) > 8:
                    recommendations['conservative_investors'].append(
                        "Consider debt funds with consistent 3Y CAGR performance"
                    )
            
            # Moderate investor recommendations
            if 'hybrid' in asset_class_analysis:
                hybrid_analysis = asset_class_analysis['hybrid']
                if hybrid_analysis.get('avg_cagr_3y', 0) > 10:
                    recommendations['moderate_investors'].append(
                        "Hybrid funds offer balanced risk-return profile"
                    )
            
            # Aggressive investor recommendations
            if 'equity' in asset_class_analysis:
                equity_analysis = asset_class_analysis['equity']
                if equity_analysis.get('avg_cagr_3y', 0) > 12:
                    recommendations['aggressive_investors'].append(
                        "Equity funds show strong long-term growth potential"
                    )
            
            # General recommendations
            recommendations['general_recommendations'].append(
                "Diversify across asset classes based on risk tolerance"
            )
            recommendations['general_recommendations'].append(
                "Consider expense ratios when selecting funds"
            )
            recommendations['general_recommendations'].append(
                "Review fund performance regularly and rebalance portfolio"
            )
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to get investment recommendations: {str(e)}")
            return {}
    
    def _get_top_performers(self, schemes: List[Dict], asset_class: str, limit: int = 5) -> List[Dict]:
        """Get top performing schemes for an asset class"""
        try:
            performers = []
            
            for scheme in schemes:
                performance = scheme.get('performance_metrics', {})
                cagr_3y = performance.get('cagr_3y')
                
                if cagr_3y:
                    performers.append({
                        'scheme_name': scheme.get('basic_info', {}).get('scheme_name', ''),
                        'amc_name': scheme.get('basic_info', {}).get('amc_name', ''),
                        'cagr_3y': float(cagr_3y),
                        'aum': scheme.get('fund_details', {}).get('aum', 0)
                    })
            
            # Sort by 3Y CAGR and return top performers
            performers.sort(key=lambda x: x['cagr_3y'], reverse=True)
            return performers[:limit]
            
        except Exception as e:
            logger.error(f"Failed to get top performers: {str(e)}")
            return []
    
    def generate_analysis_report(self, output_file: str = None) -> str:
        """Generate comprehensive analysis report"""
        try:
            analysis = self.get_comprehensive_analysis()
            
            if not output_file:
                output_file = f"analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            import json
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(analysis, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"Analysis report saved to: {output_file}")
            return output_file
            
        except Exception as e:
            logger.error(f"Failed to generate analysis report: {str(e)}")
            return ""
    
    def close(self) -> None:
        """Close database connection"""
        try:
            if self.db_interface:
                self.db_interface.close_connection()
        except Exception as e:
            logger.error(f"Error closing analysis engine: {str(e)}")
