package com.project.weatherdatafetcher.dto;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;


import java.util.List;

@JsonIgnoreProperties(ignoreUnknown = true)
public record InputEvent(
        @NotBlank(message = "eventId не должен быть пустым")
        String event_id,
        String trace_id,
        String event_type,
        String requested_by,
        @NotNull(message = "date_from обязателен")
        String date_from,
        @NotNull(message = "date_to обязателен")
        String date_to,
        List<String> wmo_indexes,
        Integer schema_version,
        String created_at,
        String dataset_type
) {}