package com.project.weatherdatafetcher.model;

public record Measurement(
        String wmo_index,
        String name,
        String country,
        Double min_temp,
        Double avg_temp,
        Double max_temp,
        Double precipitation
) {
    public Measurement(String wmo_index, Double min_temp, Double avg_temp, Double max_temp, Double precipitation) {
        this(wmo_index, "", "", min_temp, avg_temp, max_temp, precipitation);
    }
}
