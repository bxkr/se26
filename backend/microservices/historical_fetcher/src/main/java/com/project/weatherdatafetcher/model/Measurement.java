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


/*
"wmo_index": "20674",
      "name": "Диксон",
      "country": "Россия",
      "min_temp": -35.1,
      "avg_temp": -31.9,
      "max_temp": -25.9,
      "precipitation": 0
 */