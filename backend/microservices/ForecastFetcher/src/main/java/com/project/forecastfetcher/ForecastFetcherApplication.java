package com.project.forecastfetcher;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.jdbc.autoconfigure.DataSourceAutoConfiguration;
import org.springframework.kafka.annotation.EnableKafka;


@EnableKafka
@SpringBootApplication(exclude = {DataSourceAutoConfiguration.class})
public class ForecastFetcherApplication {

    public static void main(String[] args) {
        SpringApplication.run(ForecastFetcherApplication.class, args);
    }

}
