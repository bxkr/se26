package com.project.weatherdatafetcher.dto;
import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import com.fasterxml.jackson.databind.annotation.JsonNaming;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;


import java.util.List;

@JsonIgnoreProperties(ignoreUnknown = true)
@JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
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
) {@JsonCreator
public InputEvent(
        @JsonProperty("event_id") String event_id,
        @JsonProperty("trace_id") String trace_id,
        @JsonProperty("event_type") String event_type,
        @JsonProperty("requested_by") String requested_by,
        @JsonProperty("date_from") String date_from,
        @JsonProperty("date_to") String date_to,
        @JsonProperty("wmo_indexes") List<String> wmo_indexes,
        @JsonProperty("schema_version") Integer schema_version,
        @JsonProperty("created_at") String created_at,
        @JsonProperty("dataset_type") String dataset_type
) {
        this.event_id = event_id;
        this.trace_id = trace_id;
        this.event_type = event_type;
        this.requested_by = requested_by;
        this.date_from = date_from;
        this.date_to = date_to;
        this.wmo_indexes = wmo_indexes;
        this.schema_version = schema_version;
        this.created_at = created_at;
        this.dataset_type = dataset_type;
}
}