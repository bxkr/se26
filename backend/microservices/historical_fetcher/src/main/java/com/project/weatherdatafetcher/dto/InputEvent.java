package com.project.weatherdatafetcher.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;


import java.time.LocalDate;
import java.util.List;

public record InputEvent(
        @JsonProperty("event_id")
        @NotBlank(message = "eventId не должен быть пустым")
        String eventId,
        @JsonProperty("date_from")
        @NotNull(message = "date_from обязателен")
        LocalDate startDate,
        @JsonProperty("date_to")
        @NotNull(message = "date_to обязателен")
        LocalDate endDate,
        @JsonProperty("trace_id")
        String traceId,
        @JsonProperty("event_type")
        String eventType,
        @JsonProperty("dataset_type")
        String datasetType,
        @JsonProperty("requested_by")
        String requestedBy,
        @JsonProperty("wmo_indexes")
        List<String> RequestedWmoIndexes,
        @JsonProperty("reason")
        String reason,
        @JsonProperty("schema_version")
        Integer schemaVersion,
        @JsonProperty("created_at")
        String createdAt

) {}
