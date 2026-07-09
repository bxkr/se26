package com.project.forecastfetcher.dto;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.project.forecastfetcher.model.DailyData;
import com.project.forecastfetcher.model.DailyUnits;
import lombok.Data;

// When latitude/longitude are comma-joined lists (batch request), each
// array element additionally carries "location_id" (its index in the
// request) - not needed since we already correlate by array position, but
// must not fail deserialization when it's absent (single-location) or
// present (batch).
@JsonIgnoreProperties(ignoreUnknown = true)
@Data
public class ForecastResponse {

    private Double latitude;

    private Double longitude;

    @JsonProperty("generationtime_ms")
    private Double generationTimeMs;

    @JsonProperty("utc_offset_seconds")
    private Integer utcOffsetSeconds;

    private String timezone;

    @JsonProperty("timezone_abbreviation")
    private String timezoneAbbreviation;

    private Double elevation;

    @JsonProperty("daily_units")
    private DailyUnits dailyUnits;

    private DailyData daily;
}