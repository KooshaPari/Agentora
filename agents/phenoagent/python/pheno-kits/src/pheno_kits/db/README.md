# DB-Kit 🗄️

Universal database abstraction layer with RLS support, multi-tenancy, query caching, and a clean async API.

## Features

- **🔌 Pluggable Adapters**: Supabase, pgvector, raw SQL (coming soon)
- **🔐 Row-Level Security (RLS)**: Automatic JWT context for secure queries
- **🏢 Multi-Tenancy**: Built-in tenant context manager
- **⚡ Query Caching**: Automatic caching for read queries (30s TTL)
- **📊 Advanced Filters**: Rich filtering with operators (eq, gt, like, in, etc.)
- **🎯 Type-Safe**: Full type hints with mypy support
- **🚀 Async-First**: Built on async/await for high performance

## Platform Support

- Supabase (Auth, RLS, Realtime)
- Neon (Serverless PostgreSQL, Branching)
- PlanetScale (Serverless MySQL)
- Turso (Edge SQLite replicas)

## Installation

```bash
# Basic installation
pip install db-kit

# With Supabase adapter
pip install db-kit[supabase]
```

## Quick Start

```python
from db_kit import Database

# Auto-configure from environment variables
db = Database.supabase()

# Set user token for RLS
db.set_access_token(user_jwt_token)

# Query with filters
users = await db.query(
    "users",
    filters={"active": True},
    order_by="created_at:desc",
    limit=10
)

# Insert
new_user = await db.insert("users", {
    "username": "johndoe",
    "email": "john@example.com"
})

# Update
await db.update(
    "users",
    data={"last_login": "2024-01-15"},
    filters={"id": user_id}
)
```

## Examples

### 1. Basic CRUD Operations

```python
from db_kit import Database

db = Database.supabase()
db.set_access_token(jwt_token)

# Create
user = await db.insert("users", {
    "username": "alice",
    "email": "alice@example.com",
    "role": "admin"
})

# Read - single record
user = await db.get_single("users", filters={"id": user_id})

# Read - multiple records
admins = await db.query("users", filters={"role": "admin"})

# Update
await db.update(
    "users",
    data={"role": "superadmin"},
    filters={"id": user_id}
)

# Delete
deleted_count = await db.delete("users", filters={"id": user_id})
```

### 2. Advanced Filtering

```python
from db_kit import Database

db = Database.supabase()

# Simple equality
users = await db.query("users", filters={"active": True})

# Operators
users = await db.query("users", filters={
    "age": {"gte": 18},  # age >= 18
    "role": {"in": ["admin", "moderator"]},  # role IN (...)
    "username": {"like": "%john%"},  # username LIKE '%john%'
})

# Combined filters
users = await db.query("users", filters={
    "active": True,
    "age": {"gte": 18},
    "created_at": {"gt": "2024-01-01"}
})

# Null checks
users = await db.query("users", filters={"deleted_at": None})
```

### 3. Multi-Tenancy with Tenant Context

```python
from db_kit import Database

db = Database.supabase()
db.set_access_token(jwt_token)

# Automatic tenant_id filtering
async with db.tenant_context("org_abc123") as tenant_db:
    # All queries automatically filter by tenant_id="org_abc123"
    users = await tenant_db.query("users", filters={"active": True})

    # Inserts automatically add tenant_id
    new_user = await tenant_db.insert("users", {
        "username": "bob",
        "email": "bob@example.com"
    })  # tenant_id is auto-added

    # Updates/deletes are scoped to tenant
    await tenant_db.update(
        "users",
        data={"role": "admin"},
        filters={"username": "bob"}
    )
```

### 4. Query Caching

```python
from db_kit import Database

db = Database.supabase()

# First query - hits database
users = await db.query("users", filters={"active": True})

# Second query within 30s - returns cached result
users = await db.query("users", filters={"active": True})

# Cache is automatically invalidated on writes
await db.insert("users", {"username": "new_user"})

# Next query hits database again
users = await db.query("users", filters={"active": True})
```

### 5. Pagination with Order By

```python
from db_kit import Database

db = Database.supabase()

# Get first page
page1 = await db.query(
    "posts",
    order_by="created_at:desc",
    limit=20,
    offset=0
)

# Get second page
page2 = await db.query(
    "posts",
    order_by="created_at:desc",
    limit=20,
    offset=20
)

# Ascending order
oldest_posts = await db.query(
    "posts",
    order_by="created_at",  # or "created_at:asc"
    limit=10
)
```

### 6. Counting Records

```python
from db_kit import Database

db = Database.supabase()

# Total count
total_users = await db.count("users")

# Filtered count
active_users = await db.count("users", filters={"active": True})

# Multi-tenancy count
async with db.tenant_context("org_123") as tenant_db:
    org_users = await tenant_db.count("users")
```

### 7. Bulk Operations

```python
from db_kit import Database

db = Database.supabase()

# Bulk insert
new_users = await db.insert("users", [
    {"username": "user1", "email": "user1@example.com"},
    {"username": "user2", "email": "user2@example.com"},
    {"username": "user3", "email": "user3@example.com"},
])

# Returns list of inserted records
print(f"Inserted {len(new_users)} users")
```

### 8. Custom Adapter

```python
from db_kit import DatabaseAdapter
from typing import Any, Dict, List, Optional, Union

class PostgresAdapter(DatabaseAdapter):
    def __init__(self, dsn: str):
        import asyncpg
        self.dsn = dsn
        self.pool = None

    async def query(
        self,
        table: str,
        *,
        select: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        # Build SQL query
        sql = f"SELECT {select or '*'} FROM {table}"

        # Add WHERE clause
        if filters:
            conditions = [f"{k} = ${i+1}" for i, k in enumerate(filters.keys())]
            sql += f" WHERE {' AND '.join(conditions)}"

        # Execute with asyncpg
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(sql, *filters.values())
            return [dict(row) for row in rows]

    # Implement other methods...

    def set_access_token(self, token: str):
        # Store for RLS
        self.token = token

# Use custom adapter
from db_kit import Database
adapter = PostgresAdapter("postgresql://user:pass@localhost/db")
db = Database(adapter=adapter)
```

## API Reference

### Database Class

#### Factory Methods

- `Database.supabase()` - Create Supabase database client

#### Methods

- `set_access_token(token)` - Set JWT for RLS context
- `query(table, *, select, filters, order_by, limit, offset)` - Query records
- `get_single(table, *, select, filters)` - Get single record
- `insert(table, data, *, returning)` - Insert records
- `update(table, data, filters, *, returning)` - Update records
- `delete(table, filters)` - Delete records
- `count(table, filters)` - Count records
- `tenant_context(tenant_id)` - Multi-tenancy context manager

### Filter Operators

| Operator | Description | Example |
|----------|-------------|---------|
| Direct value | Equality | `{"age": 25}` |
| `{"eq": val}` | Equals | `{"age": {"eq": 25}}` |
| `{"neq": val}` | Not equals | `{"status": {"neq": "deleted"}}` |
| `{"gt": val}` | Greater than | `{"age": {"gt": 18}}` |
| `{"gte": val}` | Greater than or equal | `{"age": {"gte": 18}}` |
| `{"lt": val}` | Less than | `{"age": {"lt": 65}}` |
| `{"lte": val}` | Less than or equal | `{"age": {"lte": 65}}` |
| `{"like": val}` | LIKE pattern | `{"name": {"like": "%john%"}}` |
| `{"ilike": val}` | Case-insensitive LIKE | `{"email": {"ilike": "%@GMAIL.COM"}}` |
| `{"in": list}` | IN list | `{"role": {"in": ["admin", "mod"]}}` |
| `{"not_in": list}` | NOT IN list | `{"status": {"not_in": ["banned"]}}` |
| `None` | IS NULL | `{"deleted_at": None}` |

## Configuration

### Environment Variables (Supabase)

```bash
export NEXT_PUBLIC_SUPABASE_URL="https://your-project.supabase.co"
export NEXT_PUBLIC_SUPABASE_ANON_KEY="your-anon-key"
```

## Performance Tips

1. **Enable caching** - Read queries are automatically cached for 30s
2. **Use tenant context** - Reduces code duplication and errors
3. **Leverage RLS** - Set access_token for automatic security
4. **Batch inserts** - Insert multiple records at once
5. **Select specific columns** - Use `select="id,name"` instead of `"*"`

## Row-Level Security (RLS)

DB-Kit integrates seamlessly with Supabase RLS policies:

```sql
-- Example RLS policy
CREATE POLICY "Users can only see their own data"
ON users
FOR SELECT
USING (auth.uid() = user_id);
```

```python
# Set user JWT - RLS automatically enforces policies
db.set_access_token(user_jwt_token)

# This query respects RLS - only returns user's own records
my_data = await db.query("users")
```

## License

MIT License - see LICENSE file for details

## Credits

Extracted from the Atoms MCP Server project and generalized for reuse.
