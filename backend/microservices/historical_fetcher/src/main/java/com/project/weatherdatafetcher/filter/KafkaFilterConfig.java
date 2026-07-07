package com.project.weatherdatafetcher.filter;


import com.project.weatherdatafetcher.dto.InputEvent;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.jspecify.annotations.NonNull;
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
                if (event.datasetType() == null) {
                    return true;
                }
                return !event.datasetType().equals("weather-raw");
            }

            return true;
        };
    }
}