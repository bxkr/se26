package com.project.weatherdatafetcher.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;


import java.time.LocalDate;
import java.util.List;

public record InputEvent(
        @NotBlank(message = "eventId не должен быть пустым")
        String event_id,
        @NotNull(message = "date_from обязателен")
        LocalDate startDate,
        @NotNull(message = "date_to обязателен")
        LocalDate end_date,
        String trace_id,
        String event_type,
        String dataset_type,
        String requested_by,
        List<String> wmo_indexes,
        String reason,
        Integer schema_version,
        String created_at
) {}
