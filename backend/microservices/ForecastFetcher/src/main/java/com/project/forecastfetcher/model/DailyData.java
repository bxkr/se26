package com.project.forecastfetcher.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;
import java.time.LocalDate;
import java.util.List;

@Data
public class DailyData {

    private List<LocalDate> time;

    @JsonProperty("temperature_2m_max")
    private List<Double> temperature2mMax;

    @JsonProperty("temperature_2m_min")
    private List<Double> temperature2mMin;

    @JsonProperty("precipitation_sum")
    private List<Double> precipitationSum;

    @JsonProperty("temperature_2m_mean")
    private List<Double> temperature2mMean;
}
