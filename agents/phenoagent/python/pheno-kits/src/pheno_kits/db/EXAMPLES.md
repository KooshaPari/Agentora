# DB Kit Usage Examples

## Basic Database Operations

### Supabase Connection
```python
from pheno.kits.db import Database, SupabaseAdapter

# Initialize database
db = Database(
    adapter=SupabaseAdapter(
        url="https://your-project.supabase.co",
        key="your-anon-key"
    )
)

# Query data
users = await db.query("users").select("*").execute()
user = await db.query("users").select("*").eq("id", "123").single()

# Insert data
new_user = await db.query("users").insert({
    "name": "John Doe",
    "email": "john@example.com"
}).execute()

# Update data
updated = await db.query("users").update({
    "name": "Jane Doe"
}).eq("id", "123").execute()

# Delete data
deleted = await db.query("users").delete().eq("id", "123").execute()
```

### PostgreSQL Direct Connection
```python
from pheno.kits.db import Database, PostgreSQLAdapter

db = Database(
    adapter=PostgreSQLAdapter(
        host="localhost",
        port=5432,
        database="mydb",
        user="postgres",
        password="password"
    )
)

# Use same query interface
results = await db.query("users").select("*").execute()
```

### Neon Serverless PostgreSQL
```python
from pheno.kits.db import Database, NeonAdapter

db = Database(
    adapter=NeonAdapter(
        connection_string="postgresql://user:pass@neon.tech/dbname"
    )
)
```

## Connection Pooling

### Async Connection Pool
```python
from pheno.kits.db import AsyncConnectionPool, ConnectionPoolConfig

# Create pool
pool = AsyncConnectionPool(
    config=ConnectionPoolConfig(
        provider="postgresql",
        connection_string="postgresql://localhost/mydb",
        min_size=2,
        max_size=10,
        timeout=30,
    )
)

# Acquire connection
async with pool.acquire() as conn:
    result = await conn.execute("SELECT * FROM users")

# Pool automatically manages connections
stats = pool.get_stats()
print(f"Active: {stats.active_connections}/{stats.total_connections}")

# Cleanup
await pool.close()
```

### Pool Manager (Recommended)
```python
from pheno.kits.db import get_pool_manager, cleanup_all_pools

# Get or create pool
pool_mgr = get_pool_manager()
pool = pool_mgr.get_or_create_pool(
    provider="supabase",
    connection_string="postgresql://...",
    pool_size=10
)

# Use pool
async with pool.acquire() as conn:
    # Your queries here
    pass

# Cleanup all pools on shutdown
await cleanup_all_pools()
```

## Migrations

### Define Migration
```python
from pheno.kits.db import Migration, MigrationStatus

migration = Migration(
    version="001",
    name="create_users_table",
    up_sql="""
        CREATE TABLE users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email TEXT UNIQUE NOT NULL,
            name TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
    """,
    down_sql="DROP TABLE users;"
)
```

### Run Migrations
```python
from pheno.kits.db import MigrationEngine, Database, PostgreSQLAdapter

db = Database(adapter=PostgreSQLAdapter(...))
engine = MigrationEngine(db_adapter=db.adapter)

# Apply migration
await engine.apply(migration)

# Check status
status = await engine.get_status(migration)
print(f"Migration status: {status}")

# Rollback
await engine.rollback(migration)
```

## Realtime Subscriptions

### Supabase Realtime
```python
from pheno.kits.db import SupabaseRealtimeAdapter

realtime = SupabaseRealtimeAdapter(
    url="https://your-project.supabase.co",
    key="your-anon-key"
)

# Subscribe to changes
def on_change(payload):
    print(f"Change detected: {payload}")

subscription = realtime.subscribe(
    table="users",
    event="INSERT",
    callback=on_change
)

# Unsubscribe
realtime.unsubscribe(subscription)
```

## Storage Operations

### Supabase Storage
```python
from pheno.kits.db import SupabaseStorageAdapter

storage = SupabaseStorageAdapter(
    url="https://your-project.supabase.co",
    key="your-anon-key"
)

# Upload file
with open("avatar.png", "rb") as f:
    result = await storage.upload(
        bucket="avatars",
        path="user-123/avatar.png",
        file=f
    )

# Download file
file_data = await storage.download(
    bucket="avatars",
    path="user-123/avatar.png"
)

# Get public URL
url = storage.get_public_url(
    bucket="avatars",
    path="user-123/avatar.png"
)

# Delete file
await storage.delete(
    bucket="avatars",
    path="user-123/avatar.png"
)
```

## Multi-Tenancy

### Tenant Isolation
```python
from pheno.kits.db import TenancyAdapter, Database

db = Database(adapter=...)
tenancy = TenancyAdapter(db_adapter=db.adapter)

# Query with tenant context
users = await tenancy.query(
    table="users",
    tenant_id="tenant-123"
).select("*").execute()

# Insert with tenant context
await tenancy.insert(
    table="users",
    tenant_id="tenant-123",
    data={"name": "John Doe"}
)
```

## Vector/Embeddings

### Store and Query Embeddings
```python
from pheno.kits.db import VectorAdapter, Database

db = Database(adapter=...)
vector = VectorAdapter(db_adapter=db.adapter)

# Store embedding
await vector.store(
    collection="documents",
    id="doc-123",
    embedding=[0.1, 0.2, 0.3, ...],  # 1536-dim vector
    metadata={"title": "Document Title"}
)

# Similarity search
results = await vector.search(
    collection="documents",
    query_embedding=[0.1, 0.2, 0.3, ...],
    limit=10
)

# Results include similarity scores
for result in results:
    print(f"{result.id}: {result.similarity}")
```

## Row-Level Security (RLS)

### Enable RLS
```python
from pheno.kits.db import Database, PostgreSQLAdapter

db = Database(adapter=PostgreSQLAdapter(...))

# Enable RLS on table
await db.execute("""
    ALTER TABLE users ENABLE ROW LEVEL SECURITY;
""")

# Create policy
await db.execute("""
    CREATE POLICY user_policy ON users
    FOR SELECT
    USING (auth.uid() = id);
""")

# Queries now respect RLS
# User can only see their own data
users = await db.query("users").select("*").execute()
```

## Query Builder

### Advanced Queries
```python
from pheno.kits.db import QueryBuilder, Database

db = Database(adapter=...)
qb = QueryBuilder(db.adapter)

# Build complex query
query = (
    qb.select("users.name", "orders.total")
    .from_table("users")
    .join("orders", "users.id", "orders.user_id")
    .where("orders.status", "=", "completed")
    .where("orders.total", ">", 100)
    .order_by("orders.created_at", "DESC")
    .limit(10)
)

results = await query.execute()
```

## Error Handling

```python
from pheno.kits.db import Database, DatabaseAdapter

try:
    db = Database(adapter=...)
    result = await db.query("users").select("*").execute()
except Exception as e:
    print(f"Database error: {e}")
    # Handle error appropriately
```

## Context Manager Pattern

```python
from pheno.kits.db import Database, get_pool_manager

async def process_users():
    pool_mgr = get_pool_manager()
    pool = pool_mgr.get_or_create_pool(...)

    async with pool.acquire() as conn:
        # Connection automatically returned to pool
        users = await conn.execute("SELECT * FROM users")
        for user in users:
            # Process user
            pass
```

## Best Practices

1. **Use Connection Pooling**: Always use pools in production
2. **Handle Errors Gracefully**: Wrap DB calls in try/except
3. **Close Connections**: Use context managers or cleanup functions
4. **Use Parameterized Queries**: Prevent SQL injection
5. **Enable RLS**: For multi-tenant applications
6. **Monitor Pool Stats**: Track connection usage
7. **Set Timeouts**: Prevent hanging connections
8. **Use Migrations**: Version control your schema changes
