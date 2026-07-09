package com.project.weatherdatafetcher.filter;


import com.project.weatherdatafetcher.dto.InputEvent;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.listener.adapter.RecordFilterStrategy;

@Configuration
public class KafkaFilterConfig {

    @Bean
    public RecordFilterStrategy<Object, Object> datasetTypeFilter() {
        return consumerRecord -> {
            Object value = consumerRecord.value();


            if (value instanceof InputEvent event) {
                if (event.dataset_type() == null) {
                    return true;
                }
                // historical_fetcher only handles the actual-weather branch;
                // "forecast" is forecast_fetcher's job. Matches the actual/
                // forecast dataset_type convention used everywhere else in
                // the pipeline (dm_trigger, dm_pipeline DAG, weather.dm.ready).
                return !event.dataset_type().equals("actual");
            }

            return true;
        };
    }
}