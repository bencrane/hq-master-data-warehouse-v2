-- Migration: Auth DB Orgs Setup
-- Database: auth-db
-- Created: 2026-01-27
-- Purpose: Set up orgs and org_users tables in auth-db

-- Drop the simpler organizations table we created earlier
DROP TABLE IF EXISTS core.target_client_views;
DROP TABLE IF EXISTS public.organizations;

-- Create core schema if not exists
CREATE SCHEMA IF NOT EXISTS core;

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION core.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create orgs table
CREATE TABLE core.orgs (
    id UUID NOT NULL DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    slug TEXT NOT NULL,
    services_enabled JSONB NULL DEFAULT '{"intent": false, "inbound": false, "outbound": false}'::jsonb,
    status TEXT NULL DEFAULT 'active'::text,
    created_at TIMESTAMPTZ NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NULL DEFAULT NOW(),
    domain TEXT NULL,
    max_email_accounts INTEGER NULL DEFAULT 0,
    max_linkedin_accounts INTEGER NULL DEFAULT 0,
    CONSTRAINT orgs_pkey PRIMARY KEY (id),
    CONSTRAINT orgs_domain_key UNIQUE (domain),
    CONSTRAINT orgs_slug_key UNIQUE (slug),
    CONSTRAINT orgs_status_check CHECK (status = ANY (ARRAY['active'::text, 'paused'::text, 'churned'::text]))
);

CREATE TRIGGER update_orgs_updated_at
BEFORE UPDATE ON core.orgs
FOR EACH ROW EXECUTE FUNCTION core.update_updated_at_column();

-- Create org_users table
CREATE TABLE core.org_users (
    id UUID NOT NULL DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL,
    user_id UUID NOT NULL,
    role TEXT NOT NULL DEFAULT 'member'::text,
    created_at TIMESTAMPTZ NULL DEFAULT NOW(),
    CONSTRAINT org_users_pkey PRIMARY KEY (id),
    CONSTRAINT org_users_org_id_user_id_key UNIQUE (org_id, user_id),
    CONSTRAINT org_users_org_id_fkey FOREIGN KEY (org_id) REFERENCES core.orgs(id) ON DELETE CASCADE,
    CONSTRAINT org_users_role_check CHECK (role = ANY (ARRAY['owner'::text, 'admin'::text, 'member'::text, 'viewer'::text]))
);

CREATE INDEX idx_org_users_user_id ON core.org_users(user_id);
CREATE INDEX idx_org_users_org_id ON core.org_users(org_id);
