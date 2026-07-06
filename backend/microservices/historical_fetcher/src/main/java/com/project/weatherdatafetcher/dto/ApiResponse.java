package com.project.weatherdatafetcher.dto;

import com.fasterxml.jackson.annotation.JsonFormat;
import com.project.weatherdatafetcher.model.Measurement;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDate;
import java.util.List;


@Data
@NoArgsConstructor
@AllArgsConstructor
public class ApiResponse {
    @JsonFormat(pattern = "yyyy-MM-dd")
    private LocalDate date;
    private List<Measurement> stations;

}
