---
name: migrate
description: Manage Django database migrations for the MTT project
---

# Database Migration Skill

Manage Django database migrations for the MTT project.

## When to Use This Skill

Claude should invoke this skill when:
- User changes Django models
- User asks about migration status
- Database schema needs updating
- Migration errors occur

## Status Check

Show which migrations are applied:

```bash
cd backend && python manage.py showmigrations
```

For specific app:
```bash
cd backend && python manage.py showmigrations containers
```

## Create Migrations

Generate new migration files from model changes:

```bash
cd backend && python manage.py makemigrations
```

For specific app:
```bash
cd backend && python manage.py makemigrations containers
```

With custom name:
```bash
cd backend && python manage.py makemigrations containers --name add_status_field
```

## Apply Migrations

Run pending migrations:

```bash
cd backend && python manage.py migrate
```

For specific app:
```bash
cd backend && python manage.py migrate containers
```

## Rollback

Revert to a previous migration state:

```bash
cd backend && python manage.py migrate containers 0001_initial
```

To unapply all migrations for an app:
```bash
cd backend && python manage.py migrate containers zero
```

## App Names

| App | Models |
|-----|--------|
| `accounts` | CustomUser, ManagerProfile, CustomerProfile, Company |
| `containers` | Container, ContainerOwner |
| `terminal_operations` | ContainerEntry, CraneOperation, PreOrder |
| `vehicles` | VehicleEntry, Destination |
| `files` | File, FileCategory, FileAttachment |

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "No changes detected" | Check if model is registered in app's models.py |
| "Conflicting migrations" | Run `python manage.py makemigrations --merge` |
| "Table already exists" | Use `--fake-initial` for initial migration |
| "Cannot add NOT NULL" | Provide default value or make nullable |

## Database Info

- Development: SQLite (`db.sqlite3`)
- Production: PostgreSQL (via `DATABASE_URL`)
