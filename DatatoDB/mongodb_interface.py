"""
MongoDB Interface for Factsheet Data Storage and Retrieval
Handles database operations with proper schema validation
"""
import pymongo
from pymongo import MongoClient
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime
import config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MongoDBInterface:
    """MongoDB interface for factsheet data management"""
    
    def __init__(self, connection_string: str = None, database_name: str = None):
        self.connection_string = connection_string or config.MONGODB_URI
        self.database_name = database_name or config.DATABASE_NAME
        self.collection_name = config.COLLECTION_NAME
        
        try:
            self.client = MongoClient(self.connection_string)
            self.db = self.client[self.database_name]
            self.collection = self.db[self.collection_name]
            
            # Test connection
            self.client.admin.command('ping')
            logger.info(f"Connected to MongoDB: {self.database_name}")
            
            # Create indexes for better performance
            self._create_indexes()
            
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {str(e)}")
            raise
    
    def _create_indexes(self) -> None:
        """Create database indexes for better query performance"""
        try:
            # Create compound index for common queries
            self.collection.create_index([
                ("basic_info.amc_name", 1),
                ("asset_classification.asset_class", 1),
                ("asset_classification.sub_class", 1)
            ])
            
            # Create index for scheme name
            self.collection.create_index("basic_info.scheme_name")
            
            # Create index for extraction date
            self.collection.create_index("basic_info.extraction_date")
            
            # Create text index for full-text search
            self.collection.create_index([
                ("basic_info.scheme_name", "text"),
                ("basic_info.amc_name", "text")
            ])
            
            logger.info("Database indexes created successfully")
            
        except Exception as e:
            logger.warning(f"Failed to create indexes: {str(e)}")
    
    def insert_scheme_data(self, scheme_data: Dict[str, Any]) -> str:
        """
        Insert scheme data into MongoDB
        
        Args:
            scheme_data: Structured scheme data
            
        Returns:
            Inserted document ID
        """
        try:
            # Add metadata
            scheme_data['_id'] = self._generate_document_id(scheme_data)
            scheme_data['created_at'] = datetime.now()
            scheme_data['updated_at'] = datetime.now()
            
            # Insert document
            result = self.collection.insert_one(scheme_data)
            
            logger.info(f"Inserted scheme data: {result.inserted_id}")
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"Failed to insert scheme data: {str(e)}")
            raise
    
    def update_scheme_data(self, scheme_data: Dict[str, Any]) -> bool:
        """
        Update existing scheme data
        
        Args:
            scheme_data: Updated scheme data
            
        Returns:
            True if update successful
        """
        try:
            document_id = self._generate_document_id(scheme_data)
            scheme_data['updated_at'] = datetime.now()
            
            result = self.collection.update_one(
                {'_id': document_id},
                {'$set': scheme_data},
                upsert=True
            )
            
            logger.info(f"Updated scheme data: {document_id}")
            return result.acknowledged
            
        except Exception as e:
            logger.error(f"Failed to update scheme data: {str(e)}")
            raise
    
    def get_scheme_by_id(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get scheme data by document ID"""
        try:
            return self.collection.find_one({'_id': document_id})
        except Exception as e:
            logger.error(f"Failed to get scheme by ID: {str(e)}")
            return None
    
    def get_schemes_by_amc(self, amc_name: str) -> List[Dict[str, Any]]:
        """Get all schemes by AMC name"""
        try:
            cursor = self.collection.find({'basic_info.amc_name': {'$regex': amc_name, '$options': 'i'}})
            return list(cursor)
        except Exception as e:
            logger.error(f"Failed to get schemes by AMC: {str(e)}")
            return []
    
    def get_schemes_by_asset_class(self, asset_class: str) -> List[Dict[str, Any]]:
        """Get all schemes by asset class"""
        try:
            cursor = self.collection.find({'asset_classification.asset_class': asset_class})
            return list(cursor)
        except Exception as e:
            logger.error(f"Failed to get schemes by asset class: {str(e)}")
            return []
    
    def get_schemes_by_sub_class(self, sub_class: str) -> List[Dict[str, Any]]:
        """Get all schemes by sub-class"""
        try:
            cursor = self.collection.find({'asset_classification.sub_class': sub_class})
            return list(cursor)
        except Exception as e:
            logger.error(f"Failed to get schemes by sub-class: {str(e)}")
            return []
    
    def search_schemes(self, query: str) -> List[Dict[str, Any]]:
        """Search schemes using text search"""
        try:
            cursor = self.collection.find({'$text': {'$search': query}})
            return list(cursor)
        except Exception as e:
            logger.error(f"Failed to search schemes: {str(e)}")
            return []
    
    def get_all_schemes(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all schemes with limit"""
        try:
            cursor = self.collection.find().limit(limit)
            return list(cursor)
        except Exception as e:
            logger.error(f"Failed to get all schemes: {str(e)}")
            return []
    
    def get_performance_analysis(self, asset_class: str = None) -> Dict[str, Any]:
        """Get performance analysis using aggregation"""
        try:
            pipeline = []
            
            # Match stage
            if asset_class:
                pipeline.append({'$match': {'asset_classification.asset_class': asset_class}})
            
            # Group stage for performance metrics
            pipeline.append({
                '$group': {
                    '_id': '$asset_classification.asset_class',
                    'avg_cagr_1y': {'$avg': '$performance_metrics.cagr_1y'},
                    'avg_cagr_3y': {'$avg': '$performance_metrics.cagr_3y'},
                    'avg_cagr_5y': {'$avg': '$performance_metrics.cagr_5y'},
                    'avg_sharpe_ratio': {'$avg': '$risk_metrics.sharpe_ratio'},
                    'avg_beta': {'$avg': '$risk_metrics.beta'},
                    'avg_standard_deviation': {'$avg': '$risk_metrics.standard_deviation'},
                    'count': {'$sum': 1}
                }
            })
            
            result = list(self.collection.aggregate(pipeline))
            return result[0] if result else {}
            
        except Exception as e:
            logger.error(f"Failed to get performance analysis: {str(e)}")
            return {}
    
    def get_risk_analysis(self) -> Dict[str, Any]:
        """Get risk analysis across all schemes"""
        try:
            pipeline = [
                {
                    '$group': {
                        '_id': '$riskometer',
                        'count': {'$sum': 1},
                        'avg_beta': {'$avg': '$risk_metrics.beta'},
                        'avg_standard_deviation': {'$avg': '$risk_metrics.standard_deviation'},
                        'avg_sharpe_ratio': {'$avg': '$risk_metrics.sharpe_ratio'}
                    }
                },
                {'$sort': {'count': -1}}
            ]
            
            result = list(self.collection.aggregate(pipeline))
            return result
            
        except Exception as e:
            logger.error(f"Failed to get risk analysis: {str(e)}")
            return []
    
    def get_amc_comparison(self) -> Dict[str, Any]:
        """Get AMC comparison data"""
        try:
            pipeline = [
                {
                    '$group': {
                        '_id': '$basic_info.amc_name',
                        'scheme_count': {'$sum': 1},
                        'avg_aum': {'$avg': '$fund_details.aum'},
                        'avg_expense_ratio': {'$avg': '$fund_details.expense_ratio'},
                        'schemes': {
                            '$push': {
                                'name': '$basic_info.scheme_name',
                                'asset_class': '$asset_classification.asset_class',
                                'sub_class': '$asset_classification.sub_class',
                                'aum': '$fund_details.aum'
                            }
                        }
                    }
                },
                {'$sort': {'scheme_count': -1}}
            ]
            
            result = list(self.collection.aggregate(pipeline))
            return result
            
        except Exception as e:
            logger.error(f"Failed to get AMC comparison: {str(e)}")
            return []
    
    def delete_scheme(self, document_id: str) -> bool:
        """Delete scheme by document ID"""
        try:
            result = self.collection.delete_one({'_id': document_id})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Failed to delete scheme: {str(e)}")
            return False
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            stats = {
                'total_schemes': self.collection.count_documents({}),
                'total_amcs': len(self.collection.distinct('basic_info.amc_name')),
                'asset_class_distribution': {},
                'recent_updates': 0
            }
            
            # Get asset class distribution
            pipeline = [
                {
                    '$group': {
                        '_id': '$asset_classification.asset_class',
                        'count': {'$sum': 1}
                    }
                }
            ]
            
            asset_distribution = list(self.collection.aggregate(pipeline))
            for item in asset_distribution:
                stats['asset_class_distribution'][item['_id']] = item['count']
            
            # Get recent updates (last 7 days)
            week_ago = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            week_ago = week_ago.replace(day=week_ago.day - 7)
            
            stats['recent_updates'] = self.collection.count_documents({
                'updated_at': {'$gte': week_ago}
            })
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get database stats: {str(e)}")
            return {}
    
    def _generate_document_id(self, scheme_data: Dict[str, Any]) -> str:
        """Generate unique document ID based on scheme information"""
        try:
            amc_name = scheme_data.get('basic_info', {}).get('amc_name', '')
            scheme_name = scheme_data.get('basic_info', {}).get('scheme_name', '')
            file_name = scheme_data.get('basic_info', {}).get('file_name', '')
            
            # Create a unique identifier
            identifier = f"{amc_name}_{scheme_name}_{file_name}".replace(' ', '_').replace('.', '_')
            return identifier.lower()
            
        except Exception as e:
            logger.error(f"Failed to generate document ID: {str(e)}")
            return f"scheme_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    def close_connection(self) -> None:
        """Close MongoDB connection"""
        try:
            self.client.close()
            logger.info("MongoDB connection closed")
        except Exception as e:
            logger.error(f"Failed to close MongoDB connection: {str(e)}")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_connection()
