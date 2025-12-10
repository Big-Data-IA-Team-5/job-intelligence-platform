{% macro generate_schema_name(custom_schema_name, node) -%}
    {#
    Custom schema name generation macro
    Instead of: base_schema + '_' + custom_schema
    Use: base_schema + '_' + custom_schema for proper naming
    
    Example: 
    - base: processed, custom: staging -> processed_staging ✓
    - base: processed, custom: processing -> processed_processing ✓
    - base: processed, custom: marts -> processed_marts ✓
    #}
    
    {%- set default_schema = target.schema -%}
    
    {%- if custom_schema_name is none -%}
        {{ default_schema }}
    {%- else -%}
        {{ default_schema }}_{{ custom_schema_name | trim }}
    {%- endif -%}

{%- endmacro %}
