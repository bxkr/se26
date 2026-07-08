package com.project.weatherdatafetcher;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.jdbc.autoconfigure.DataSourceAutoConfiguration;
import org.springframework.kafka.annotation.EnableKafka;


@EnableKafka
@SpringBootApplication(exclude = {DataSourceAutoConfiguration.class})
public class WeatherDataFetcherApplication {

	public static void main(String[] args) {
		SpringApplication.run(WeatherDataFetcherApplication.class, args);
	}

}
