package com.project.weatherdatafetcher.dto;

import java.time.LocalDateTime;

public record OutputReceipt(
        String event_id,
        String trace_id,
        String event_type,
        String source_name,
        String bucket,
        String object_key,
        String date_from,
        String date_to,
        Integer station_count,
        Integer schema_version,
        LocalDateTime created_at
) {}
