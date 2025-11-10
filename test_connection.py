import asyncio
import asyncpg
import ssl
import certifi
import os

async def test_connection():
    ssl_ctx = ssl.create_default_context(cafile=certifi.where())
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE
    
    dsn = os.getenv("POSTGRES_DSN")
    
    try:
        print("Connecting with statement_cache_size=0...")
        conn = await asyncpg.connect(
            dsn,
            statement_cache_size=0,
            ssl=ssl_ctx,
        )
        print("✅ Connected successfully!")
        
        # Test a simple query
        result = await conn.fetchval("SELECT 1")
        print(f"✅ Query result: {result}")
        
        # Test another query to see if prepared statements cause issues
        result2 = await conn.fetchval("SELECT version()")
        print(f"✅ Version: {result2}")
        
        await conn.close()
        print("✅ Connection closed")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_connection())
