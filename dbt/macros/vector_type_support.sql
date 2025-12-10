{% macro get_column_types() %}
  {#
    Custom macro to skip column type inference for VECTOR columns
    This prevents dbt from trying to parse VECTOR(FLOAT, 768) types
  #}
  {{ return({}) }}
{% endmacro %}


{% macro snowflake__create_table_as(temporary, relation, sql) -%}
  {#
    Override default create_table_as to handle VECTOR types
    Uses CREATE TABLE AS SELECT without column type inference
  #}
  {%- set sql_header = config.get('sql_header', none) -%}

  {{ sql_header if sql_header is not none }}

  create or replace {% if temporary -%}temporary{%- endif %} table {{ relation }}
  as (
    {{ sql }}
  );
{%- endmacro %}
