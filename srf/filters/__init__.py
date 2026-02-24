# ==============================================================================
# Query Parameter Mapping
# ------------------------------------------------------------------------------
# Name            Type / Example        Description
# ------------------------------------------------------------------------------
# filter          JsonLogic             Generic JsonLogic expression (nested AND/OR)
# search          SearchFilter          Global full-text search keyword
# page            int  (≥1)             Page number, default 1
# pagesize        int  (1~200)          Items per page, default 20
# filter_fields   str  (comma-split)   Exact-match field list, e.g. status,owner
# simple_filter   str  (comma-split)   Range field list, format field_min,field_max
# ==============================================================================
