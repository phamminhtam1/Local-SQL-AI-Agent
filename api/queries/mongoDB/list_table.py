# MongoDB: List all collections (equivalent to tables) in a database
from pymongo import MongoClient
import logging

logger = logging.getLogger(__name__)

def list_tables(connection_string, db_name):
    """
    List all collections in a MongoDB database
    
    Args:
        connection_string (str): MongoDB connection string
        db_name (str): Database name to list collections from
    
    Returns:
        list: List of dictionaries containing collection information
    """
    try:
        # Connect to MongoDB
        client = MongoClient(connection_string)
        db = client[db_name]
        
        # Get list of collections
        collections = db.list_collection_names()
        
        result = []
        for collection_name in collections:
            # Get collection stats
            stats = db.command("collStats", collection_name)
            
            collection_info = {
                'database_name': db_name,
                'table_name': collection_name,  # Using table_name for consistency
                'table_type': 'MONGO_COLLECTION',
                'estimated_rows': stats.get('count', 0),
                'size_mb': round(stats.get('size', 0) / 1024 / 1024, 2),
                'table_comment': 'MongoDB Collection',
                'created_at': None,
                'updated_at': None,
                'indexes': len(stats.get('indexSizes', {})),
                'avg_obj_size': stats.get('avgObjSize', 0)
            }
            result.append(collection_info)
        
        # Sort by collection name
        result.sort(key=lambda x: x['table_name'])
        
        client.close()
        return result
        
    except Exception as e:
        logger.error(f"Error listing MongoDB collections: {e}")
        return {"error": str(e)}
