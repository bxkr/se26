package com.project.weatherdatafetcher.model;

public record Measurement(
        Long wmo_index,
        String name,
        String country,
        Double min_temp,
        Double avg_temp,
        Double max_temp,
        Double precipitation
) {}

