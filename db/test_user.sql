-- Test user for local development. The tests create a throwaway database per run, so
-- the user needs CREATEDB, but it must never reach the application database.
CREATE ROLE tester LOGIN CREATEDB PASSWORD 'tester';
CREATE DATABASE tester OWNER tester;
REVOKE CONNECT ON DATABASE postgres FROM PUBLIC;
REVOKE CONNECT ON DATABASE gridcheck FROM PUBLIC;
