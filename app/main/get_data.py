from google.cloud import bigquery

from datetime import datetime
import google.auth

credentials, project_id = google.auth.default()

client = bigquery.Client()


def get_summary_data(start_date, end_date, desired_page, ga_toggle):
    start_date = datetime.strftime(start_date, '%Y%m%d')
    end_date = datetime.strftime(end_date, '%Y%m%d')

    summary_sql_ua = f"""
      DECLARE first_date STRING DEFAULT '{start_date}';
      DECLARE final_date STRING DEFAULT '{end_date}';
      DECLARE filtered_urls_for STRING DEFAULT '{desired_page}';

      WITH
        sessions AS (
          SELECT DISTINCT fullVisitorId, visitId
          FROM `govuk-bigquery-analytics.87773428.ga_sessions_*`, UNNEST(hits) AS hits
          WHERE _table_suffix between first_date AND final_date
          AND REGEXP_CONTAINS(hits.page.pagePath, filtered_urls_for)
        )

      SELECT
        cast(TIMESTAMP_MILLIS(CAST(hits.time+(visitStartTime*1000) AS INT64)) as STRING) AS datetime,
        hits.page.pagePath,
        hits.eventInfo.eventCategory,
        hits.eventInfo.eventAction,
        hits.eventInfo.eventLabel,
      FROM `govuk-bigquery-analytics.87773428.ga_sessions_*`, unnest(hits) AS hits
      INNER JOIN sessions USING(fullVisitorId, visitId)
      WHERE _table_suffix between first_date AND final_date
      AND hits.page.pagePath NOT LIKE '/print%'
    """

    summary_sql_ga4 = f"""
      DECLARE first_date STRING DEFAULT '{start_date}';
      DECLARE final_date STRING DEFAULT '{end_date}';
      DECLARE filtered_urls_for STRING DEFAULT '{desired_page}';


      WITH
        sessions AS (
          SELECT DISTINCT unique_session_id
          FROM `ga4-analytics-352613.flattened_dataset.flattened_daily_ga_data_*`
          WHERE _table_suffix between first_date AND final_date
          AND event_name = 'session_start'
          AND REGEXP_CONTAINS(cleaned_page_location, filtered_urls_for)
        )

      SELECT
        'DataLabs' AS tablesource,
        _table_suffix AS tabledate,
        cleaned_page_location,
        unique_session_id,
        event_name,
        type,
        FORMAT_TIMESTAMP('%Y-%m-%d %H:%M:%S', TIMESTAMP_MILLIS(CAST(event_timestamp/1000 AS INT64))) AS datetime,
        category
      FROM `ga4-analytics-352613.flattened_dataset.flattened_daily_ga_data_*`
      INNER JOIN sessions USING(unique_session_id)
      WHERE _table_suffix BETWEEN first_date AND final_date
      AND cleaned_page_location NOT LIKE '/print%'
      AND category = 'mobile'
      --AND event_name = 'page_view'

      GROUP BY ALL

    """

    if ga_toggle == 'ua':
        summary_sql = summary_sql_ua
    else:
        summary_sql = summary_sql_ga4
    job_config = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
    query_job = client.query(
        summary_sql,
        job_config=job_config,
    )
    tot_bytes_processed = query_job.total_bytes_processed
    gb_processed = tot_bytes_processed / (1024 ** 3)
    query_cost = tot_bytes_processed / (1024 ** 4) * 5
    return gb_processed, query_cost


def get_csv_data(start_date, end_date, desired_page, ga_toggle):
    start_date = datetime.strftime(start_date, '%Y%m%d')
    end_date = datetime.strftime(end_date, '%Y%m%d')

    csv_sql_ua = f"""
      DECLARE first_date STRING DEFAULT '{start_date}';
      DECLARE final_date STRING DEFAULT '{end_date}';
      DECLARE filtered_urls_for STRING DEFAULT '{desired_page}';

      WITH
        sessions AS (
          SELECT DISTINCT fullVisitorId, visitId
          FROM `govuk-bigquery-analytics.87773428.ga_sessions_*`, UNNEST(hits) AS hits
          WHERE _table_suffix between first_date AND final_date
          AND REGEXP_CONTAINS(hits.page.pagePath, filtered_urls_for)
        )

      SELECT
        'DataLabs' AS tablesource,
        _table_suffix AS tabledate,
        fullVisitorId,
        visitId,
        cast(TIMESTAMP_MILLIS(CAST(hits.time+(visitStartTime*1000) AS INT64)) as STRING) AS datetime,
        hits.hitNumber,
        hits.page.pagePath,
        hits.type,
        hits.eventInfo.eventCategory,
        hits.eventInfo.eventAction,
        hits.eventInfo.eventLabel,
        (SELECT value FROM hits.customDimensions WHERE index=4) AS content_id,
        (SELECT value FROM hits.customDimensions WHERE index=2) AS document_type,
        device.isMobile,
        CONCAT(fullVisitorId, '-', visitId) AS SessionId,
        hits.page.pagePath as page_path_copy,
        hits.eventInfo.eventCategory as event_category_copy,
        hits.eventInfo.eventAction as event_action_copy,
        hits.eventInfo.eventLabel as event_label_copy,

      FROM `govuk-bigquery-analytics.87773428.ga_sessions_*`, unnest(hits) AS hits
      INNER JOIN sessions USING(fullVisitorId, visitId)
      WHERE _table_suffix BETWEEN first_date AND final_date
      AND hits.page.pagePath NOT LIKE '/print%'
    """

    csv_sql_ga4 = f"""
      DECLARE first_date STRING DEFAULT '{start_date}';
      DECLARE final_date STRING DEFAULT '{end_date}';
      DECLARE filtered_urls_for STRING DEFAULT '{desired_page}';


      WITH
        sessions AS (
          SELECT DISTINCT unique_session_id
          FROM `ga4-analytics-352613.flattened_dataset.flattened_daily_ga_data_*`
          WHERE _table_suffix between first_date AND final_date
          AND event_name = 'session_start'
          AND REGEXP_CONTAINS(cleaned_page_location, filtered_urls_for)
        )

      SELECT
        'DataLabs' AS tablesource,
        _table_suffix AS tabledate,
        cleaned_page_location,
        unique_session_id,
        event_name,
        type,
        FORMAT_TIMESTAMP('%Y-%m-%d %H:%M:%S', TIMESTAMP_MILLIS(CAST(event_timestamp/1000 AS INT64))) AS datetime,
        category
      FROM `ga4-analytics-352613.flattened_dataset.flattened_daily_ga_data_*`
      INNER JOIN sessions USING(unique_session_id)
      WHERE _table_suffix BETWEEN first_date AND final_date
      AND cleaned_page_location NOT LIKE '/print%'
      AND category = 'mobile'
      --AND event_name = 'page_view'

      GROUP BY ALL

    """
    if ga_toggle == 'ua':
        csv_sql = csv_sql_ua
    else:
        csv_sql = csv_sql_ga4
    return client.query(csv_sql).to_dataframe()
