package com.project.weatherdatafetcher.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

@Data
public class DailyUnits {

    private String time;

    @JsonProperty("temperature_2m_max")
    private String temperature2mMax;

    @JsonProperty("temperature_2m_min")
    private String temperature2mMin;

    @JsonProperty("precipitation_sum")
    private String precipitationSum;

    @JsonProperty("temperature_2m_mean")
    private String temperature2mMean;
}
