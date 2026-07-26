-- AuraFit PostgreSQL initialization
-- Enables pgvector extension for product embedding similarity search

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Create schemas for multi-service isolation (all in same DB for dev)
CREATE SCHEMA IF NOT EXISTS user_svc;
CREATE SCHEMA IF NOT EXISTS product_svc;
CREATE SCHEMA IF NOT EXISTS rec_svc;

COMMENT ON SCHEMA user_svc IS 'AuraFit user service tables';
COMMENT ON SCHEMA product_svc IS 'AuraFit product catalog tables';
COMMENT ON SCHEMA rec_svc IS 'AuraFit recommendation engine tables';
