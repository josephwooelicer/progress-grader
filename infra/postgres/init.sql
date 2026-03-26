-- Create platform database (idempotent)
SELECT 'CREATE DATABASE progressgrader'
  WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'progressgrader')\gexec

-- Create Gitea database (idempotent)
SELECT 'CREATE DATABASE gitea'
  WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'gitea')\gexec
