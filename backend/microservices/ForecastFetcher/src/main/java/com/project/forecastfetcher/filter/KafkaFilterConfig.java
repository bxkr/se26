package com.project.forecastfetcher.filter;


import com.project.forecastfetcher.dto.InputEvent;

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
                return !event.dataset_type().equals("forecast");
            }

            return true;
        };
    }
}