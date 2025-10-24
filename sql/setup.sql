CREATE DATABASE knowledge_base_server
    WITH
    OWNER = postgres
    ENCODING = 'UTF8'
    LOCALE_PROVIDER = 'libc'
    CONNECTION LIMIT = -1
    IS_TEMPLATE = False;

-- Older version of PostgreSQL does not support the IS_TEMPLATE parameter
CREATE DATABASE knowledge_base_server
    WITH 
    OWNER = postgres
    ENCODING = 'UTF8'
    LC_COLLATE = 'C.UTF-8'
    LC_CTYPE = 'C.UTF-8'
    CONNECTION LIMIT = -1
    IS_TEMPLATE = false;