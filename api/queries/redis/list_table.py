# Redis: List all keys (equivalent to tables) in a Redis database
import redis
import logging

logger = logging.getLogger(__name__)

def list_tables(connection_string, db_name=None):
    """
    List all keys in a Redis database
    
    Args:
        connection_string (str): Redis connection string
        db_name (str): Database name (Redis database number, 0-15)
    
    Returns:
        list: List of dictionaries containing key information
    """
    try:
        # Parse connection string and connect to Redis
        # Assuming connection_string format: redis://host:port/db
        r = redis.from_url(connection_string)
        
        # If db_name is provided, select that database
        if db_name is not None:
            try:
                db_num = int(db_name)
                r.select(db_num)
            except ValueError:
                logger.warning(f"Invalid database number: {db_name}, using default")
        
        # Get all keys
        keys = r.keys('*')
        
        result = []
        for key in keys:
            key_str = key.decode('utf-8') if isinstance(key, bytes) else str(key)
            
            # Get key information
            key_type = r.type(key).decode('utf-8')
            ttl = r.ttl(key)
            
            # Get memory usage if available
            try:
                memory_usage = r.memory_usage(key)
            except:
                memory_usage = 0
            
            # Get key length based on type
            key_length = 0
            try:
                if key_type == 'string':
                    key_length = 1
                elif key_type == 'list':
                    key_length = r.llen(key)
                elif key_type == 'set':
                    key_length = r.scard(key)
                elif key_type == 'zset':
                    key_length = r.zcard(key)
                elif key_type == 'hash':
                    key_length = r.hlen(key)
            except:
                key_length = 0
            
            key_info = {
                'database_name': f"db_{r.connection_pool.connection_kwargs.get('db', 0)}",
                'table_name': key_str,
                'table_type': f'REDIS_{key_type.upper()}',
                'estimated_rows': key_length,
                'size_mb': round(memory_usage / 1024 / 1024, 4) if memory_usage else 0,
                'table_comment': f'Redis {key_type} key',
                'created_at': None,
                'updated_at': None,
                'ttl_seconds': ttl if ttl > 0 else None,
                'key_type': key_type,
                'key_length': key_length
            }
            result.append(key_info)
        
        # Sort by key name
        result.sort(key=lambda x: x['table_name'])
        
        return result
        
    except Exception as e:
        logger.error(f"Error listing Redis keys: {e}")
        return {"error": str(e)}
