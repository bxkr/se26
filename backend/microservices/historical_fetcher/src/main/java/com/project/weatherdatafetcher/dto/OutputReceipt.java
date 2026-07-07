package com.project.weatherdatafetcher.dto;

import java.time.LocalDateTime;
import java.util.List;

public record OutputReceipt(
        String event_id,
        String trace_id,
        String event_type,
        String source_name,
        String bucket,
        List<String> object_keys,
        String date_from,
        String date_to,
        Integer schema_version,
        LocalDateTime created_at
) {}
